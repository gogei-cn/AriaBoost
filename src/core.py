import time
import logging
from collections import deque
import config
from rpc_utils import get_active_task, get_task_info_fallback, pause_task, resume_task, RPCHealthChecker
from predictor import SpeedDecayPredictor
from bayesian_optimizer import BayesianOptimizer
from cluster import SpeedPatternCluster
from state_manager import StateManager
from utils import get_robust_peak
from anomaly_detector import AnomalyDetector
from circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, config.LOG_LEVEL.upper(), logging.INFO))


class OptimizerCore:
    def __init__(self, ui_callback=None):
        self.ui_callback = ui_callback or (lambda *args: None)
        self.running = False
        self.param_space = {
            'threshold': config.OPT_THRESHOLD_RANGE,
            'warmup': config.OPT_WARMUP_RANGE,
            'trigger_count': config.TRIGGER_COUNT_RANGE,
            'predict_margin': config.PREDICT_MARGIN_RANGE,
            'drop_filter': config.DROP_FILTER_RANGE,
        }
        self.mode_optimizers = {}
        self.cluster = None
        self.current_mode_id = 0
        self.state_manager = StateManager(config.PERSIST_FILE) if config.ENABLE_PERSISTENCE else None
        self.load_state()
        if 0 not in self.mode_optimizers:
            self.mode_optimizers[0] = BayesianOptimizer(self.param_space)
        self.current_opt = self.mode_optimizers[0]
        self.dynamic_warmup = config.WARMUP_SEC
        self.dynamic_base_threshold = 0.7
        self.dynamic_trigger_count = config.LOW_SPEED_TRIGGER_COUNT
        self.dynamic_predict_margin = config.PREDICTIVE_SPEED_MARGIN
        self.dynamic_drop_filter = config.SPEED_DROP_FILTER
        suggested = self.current_opt.suggest_params()
        self._apply_suggested_params(suggested)
        self.task_gid = None
        self.global_start_time = None
        self.global_start_bytes = None
        self.peak_history = deque(maxlen=config.PEAK_HISTORY_SIZE)
        self.warmup_end_time = 0
        self.last_speed = 0
        self.low_speed_streak = 0
        self.predictor = SpeedDecayPredictor()
        self.window_speed_samples = []
        self.window_time_samples = []
        self.window_peak_speed = 0
        self.window_trigger_speed = 0
        self.cycle_count = 0
        self.persist_counter = 0
        self.task_start_time = None
        self.task_restart_count = 0
        self.last_health_check = time.time()
        self.window_start_time = None
        self.window_start_bytes = None
        self.rpc_health = RPCHealthChecker()
        self.speed_buffer = deque(maxlen=20)
        self.restart_intervals = deque(maxlen=20)
        self.last_restart_time = time.time()
        self.anomaly_detector = AnomalyDetector(contamination=0.1) if config.ANOMALY_DETECTION_ENABLED else None
        self.circuit_breaker = CircuitBreaker() if config.CIRCUIT_BREAKER_ENABLED else None
        self.chart_data = {'time': [], 'speed': [], 'threshold': []}
        self.last_chart_update = 0
        self._status_text = "等待中"
        self._speed_mb = 0.0
        self._base_peak = 0.0
        self._progress = 0.0
        self._global_avg_mb = 0.0
        self._no_task_logged = False

    def _apply_suggested_params(self, suggested):
        self.dynamic_base_threshold = suggested.get('threshold', 0.7)
        self.dynamic_warmup = suggested.get('warmup', config.WARMUP_SEC)
        self.dynamic_trigger_count = suggested.get('trigger_count', config.LOW_SPEED_TRIGGER_COUNT)
        self.dynamic_predict_margin = suggested.get('predict_margin', config.PREDICTIVE_SPEED_MARGIN)
        self.dynamic_drop_filter = suggested.get('drop_filter', config.SPEED_DROP_FILTER)

    def load_state(self):
        loaded = self.state_manager.load() if self.state_manager else None
        # 修复：只要配置开启就强制创建聚类实例，不再显示未启用
        if config.USE_PATTERN_CLUSTER:
            self.cluster = SpeedPatternCluster()
        else:
            self.cluster = None

        if loaded:
            if config.USE_PATTERN_CLUSTER and "cluster" in loaded and loaded["cluster"]:
                self.cluster.load_state_dict(loaded["cluster"])
            for mode_str, opt_state in loaded.get("mode_optimizers", {}).items():
                mid = int(mode_str)
                opt = BayesianOptimizer(self.param_space)
                opt.load_state_dict(opt_state)
                self.mode_optimizers[mid] = opt
            if 0 not in self.mode_optimizers:
                self.mode_optimizers[0] = BayesianOptimizer(self.param_space)
        else:
            self.mode_optimizers[0] = BayesianOptimizer(self.param_space)
            if config.USE_PATTERN_CLUSTER:
                self.cluster = SpeedPatternCluster()

    def initial_restart(self):
        # 修复RPC解包崩溃：先接收结果再判断
        result = self._safe_rpc_call(get_active_task)
        if result is None:
            self._notify_log("RPC连接异常，无法获取任务")
            self._no_task_logged = True
            return False
        gid, info = result

        if gid:
            self._notify_log(f"检测到活跃任务 {gid[:8]}...，正在重启")
            pause_task(gid)
            time.sleep(config.PAUSE_WAIT_SEC)
            resume_task(gid)
            self.task_gid = gid
            self.task_start_time = time.time()
            now = time.time()
            self.global_start_time = now
            self.global_start_bytes = info.get("completedLength", 0)
            self.warmup_end_time = now + self.dynamic_warmup
            self.window_start_time = now
            self.window_start_bytes = self.global_start_bytes
            self._notify_log(f"任务 {gid[:8]}... 已重启，开始监控 (热身 {self.dynamic_warmup:.1f}s)")
            self._no_task_logged = False
            return True
        else:
            self._notify_log("当前无活跃任务，等待中...")
            self._no_task_logged = True
            return False

    def _safe_rpc_call(self, func, *args):
        # 统一捕获所有RPC异常，固定返回格式，杜绝None解包
        try:
            if self.circuit_breaker is not None:
                return self.circuit_breaker.call(func, *args)
            else:
                return func(*args)
        except Exception as e:
            self._notify_log(f"RPC调用失败：{str(e)}")
            return None

    def _update_dynamic_trigger_count(self):
        if len(self.restart_intervals) >= 10:
            avg_interval = sum(self.restart_intervals) / len(self.restart_intervals)
            if avg_interval < 8:
                self.dynamic_trigger_count = 1
            elif avg_interval < 20:
                self.dynamic_trigger_count = 2
            else:
                self.dynamic_trigger_count = 3
        else:
            self.dynamic_trigger_count = config.LOW_SPEED_TRIGGER_COUNT

    def _check_anomaly(self, features):
        if self.anomaly_detector is not None:
            self.anomaly_detector.add_sample(features)
            if self.anomaly_detector.fitted:
                if self.anomaly_detector.detect(features):
                    self._notify_log("检测到异常速度模式")
                    return True
        return False

    def step(self):
        if not self.running:
            return self._get_ui_state()
        try:
            now = time.time()
            if now - self.last_health_check > config.RPC_HEALTH_CHECK_INTERVAL:
                if not self.rpc_health.check():
                    self._notify_log("RPC 连接异常")
                    if not self.rpc_health.is_healthy():
                        self._notify_log("RPC 正在恢复...")
                        self.rpc_health.recover()
                        self.task_gid = None
                self.last_health_check = now

            # 修复解包逻辑
            result = self._safe_rpc_call(get_active_task)
            if result is None:
                gid, info = None, {}
            else:
                gid, info = result

            if self.task_gid is not None and (gid is None or gid != self.task_gid):
                self._notify_log("任务结束，生成报告...")
                try:
                    stat, spd, comp, total = get_task_info_fallback(self.task_gid)
                    elapsed = now - self.task_start_time if self.task_start_time else 0
                    avg_mb = (comp / elapsed / 1048576) if elapsed > 0 else 0
                    pct = (comp / total * 100) if total else 0
                    self._notify_log(f"任务完成 | 耗时 {elapsed:.1f}s 平均 {avg_mb:.2f}MB/s 进度 {pct:.1f}% 重启 {self.task_restart_count} 次")
                except Exception as e:
                    self._notify_log(f"获取任务信息失败: {e}")
                self.task_gid = self.task_start_time = None
                self.task_restart_count = 0
                self.global_start_time = None
                self.predictor.reset()
                self.window_speed_samples.clear()
                self.window_time_samples.clear()
                self.window_peak_speed = 0
                self.speed_buffer.clear()
                self.low_speed_streak = 0
                self.restart_intervals.clear()
                self._notify_status("等待任务")
                return self._get_ui_state()

            if not gid:
                if not self._no_task_logged:
                    self._notify_status("无活跃任务")
                    self._notify_speed(0, 0)
                    self._no_task_logged = True
                return self._get_ui_state()
            self._no_task_logged = False

            if self.task_gid is None:
                self.task_gid = gid
                self.task_start_time = now
                self.task_restart_count = 0
                self._notify_log(f"检测到新任务 {gid[:8]}...")
                spd = info["downloadSpeed"]
                comp = info["completedLength"]
                total = info["totalLength"]
                self.global_start_time = now
                self.global_start_bytes = comp
                suggested = self.current_opt.suggest_params()
                self._apply_suggested_params(suggested)
                self.cycle_count = 0
                self.window_peak_speed = 0
                self.speed_buffer.clear()
                self.low_speed_streak = 0
                self.warmup_end_time = now + self.dynamic_warmup
                self.window_start_time = now
                self.window_start_bytes = comp
                self.last_speed = 0
                self.predictor.reset()
                self.window_speed_samples.clear()
                self.window_time_samples.clear()
                self.restart_intervals.clear()
                self.last_restart_time = now
                self._notify_log(f"开始监控 | 阈值={self.dynamic_base_threshold:.3f} 热身={self.dynamic_warmup:.1f}s")
            else:
                spd = info["downloadSpeed"]
                comp = info["completedLength"]
                total = info["totalLength"]

            speed_mb = spd / 1048576
            progress = (comp / total * 100) if total else 0
            remaining_mb = (total - comp) / 1048576 if total else 0
            global_elapsed = now - self.global_start_time if self.global_start_time else 0
            global_delta = comp - self.global_start_bytes if self.global_start_bytes else 0
            global_avg_mb = (global_delta / global_elapsed / 1048576) if global_elapsed > 0 else 0

            if spd > 0:
                self.speed_buffer.append(spd)
                if spd > self.window_peak_speed:
                    self.window_peak_speed = spd
                if now >= self.warmup_end_time:
                    self.window_speed_samples.append(spd)
                    self.window_time_samples.append(now)
                    self.predictor.add_sample(spd, now)

            # 使用修复后的鲁棒峰值函数
            base_peak = get_robust_peak(self.speed_buffer, self.window_peak_speed)
            dynamic_threshold = self.predictor.get_adjusted_threshold(self.dynamic_base_threshold)
            window_elapsed = now - self.window_start_time if self.window_start_time else 0
            phase_ratio = min(1.0, window_elapsed / (self.dynamic_warmup + 20))
            phase_factor = config.PHASE_FACTOR_MIN + (config.PHASE_FACTOR_MAX - config.PHASE_FACTOR_MIN) * phase_ratio
            final_threshold = max(0.3, min(0.95, dynamic_threshold * phase_factor))
            in_warmup = now < self.warmup_end_time
            status_tag = "热身中" if in_warmup else ""
            should_restart = False

            if not in_warmup and base_peak > 0:
                features = [speed_mb, base_peak/1048576, spd/base_peak if base_peak else 0, progress]
                if self._check_anomaly(features):
                    should_restart = True
                    status_tag = "异常触发"

            if progress >= config.DISABLE_AFTER_PROGRESS and remaining_mb < config.DISABLE_REMAINING_MB:
                status_tag = "末期禁用"
                self._update_ui(speed_mb, base_peak, progress, global_avg_mb, status_tag)
                return self._get_ui_state()

            if not in_warmup and not should_restart:
                if spd > self.window_peak_speed:
                    self.window_peak_speed = spd
                    status_tag = "峰值刷新"
                thresh_speed = base_peak * final_threshold
                # 新增：阈值上限保护，避免虚高峰值导致频繁重启
                thresh_speed = min(thresh_speed, self.window_peak_speed * 0.7)
                if thresh_speed < config.MIN_TRIGGER_SPEED:
                    thresh_speed = config.MIN_TRIGGER_SPEED

                self._update_dynamic_trigger_count()
                predictive_trigger = False
                if config.PREDICTIVE_TRIGGER_ENABLED and spd < thresh_speed and base_peak > config.MIN_TRIGGER_SPEED:
                    pred_spd, ci = self.predictor.predict_with_confidence(config.PREDICTIVE_GAP_SEC, spd)
                    if pred_spd < thresh_speed * (1 + self.dynamic_predict_margin):
                        predictive_trigger = True
                        status_tag = "预测触发"
                        self._notify_log(f"预测触发: {speed_mb:.2f}MB/s -> {pred_spd/1048576:.2f}MB/s")
                        should_restart = True
                if not predictive_trigger:
                    is_low = (spd < thresh_speed and spd > config.MIN_TRIGGER_SPEED and base_peak > config.MIN_TRIGGER_SPEED)
                    if is_low:
                        drop = 1 - (spd / self.last_speed) if self.last_speed > 0 else 0
                        if drop > self.dynamic_drop_filter:
                            status_tag = "暴跌过滤"
                            self.low_speed_streak = 0
                        else:
                            if self.predictor.is_network_jitter():
                                status_tag = "抖动过滤"
                            self.low_speed_streak += 1
                            status_tag = f"低速({self.low_speed_streak}/{self.dynamic_trigger_count})"
                    else:
                        self.low_speed_streak = 0
                        if base_peak > config.MIN_TRIGGER_SPEED:
                            status_tag = "高速"
                    if self.low_speed_streak >= self.dynamic_trigger_count and base_peak > config.MIN_TRIGGER_SPEED:
                        should_restart = True
                        self._notify_log(f"动态触发 ({self.low_speed_streak}/{self.dynamic_trigger_count})")
                if not should_restart and spd < thresh_speed * 0.7 and spd > config.MIN_TRIGGER_SPEED and base_peak > config.MIN_TRIGGER_SPEED:
                    should_restart = True
                    status_tag = "严重降速"
                    self._notify_log(f"严重降速触发: {speed_mb:.2f}MB/s")

            if should_restart:
                self.cycle_count += 1
                self.task_restart_count += 1
                interval = now - self.last_restart_time
                self.restart_intervals.append(interval)
                self.last_restart_time = now
                window_elapsed_full = now - self.window_start_time if self.window_start_time else 0
                window_delta = comp - self.window_start_bytes if self.window_start_bytes else 0
                window_total = window_elapsed_full + config.PAUSE_WAIT_SEC
                real_avg_mb = (window_delta / 1048576) / window_total if window_total > 1e-6 else 0
                self.peak_history.append(self.window_peak_speed)
                self.window_trigger_speed = spd
                self._notify_log(f"第 {self.cycle_count} 次重启 | 平均 {real_avg_mb:.2f}MB/s")

                if config.USE_PATTERN_CLUSTER and self.cluster and self.window_speed_samples:
                    try:
                        feat = self.cluster.extract_features(
                            self.window_speed_samples, self.window_time_samples,
                            self.window_peak_speed, window_elapsed_full, self.window_trigger_speed
                        )
                        new_mode = self.cluster.add_window(feat)
                        if new_mode != self.current_mode_id:
                            self._notify_log(f"聚类切换 {self.current_mode_id} -> {new_mode}")
                            self.current_mode_id = new_mode
                            if new_mode not in self.mode_optimizers:
                                self.mode_optimizers[new_mode] = BayesianOptimizer(self.param_space)
                            self.current_opt = self.mode_optimizers[new_mode]
                    except Exception as e:
                        self._notify_log(f"聚类失败: {e}")

                self.current_opt.update({
                    "threshold": self.dynamic_base_threshold,
                    "warmup": self.dynamic_warmup,
                    "trigger_count": self.dynamic_trigger_count,
                    "predict_margin": self.dynamic_predict_margin,
                    "drop_filter": self.dynamic_drop_filter,
                }, real_avg_mb)
                suggested = self.current_opt.suggest_params()
                old = (self.dynamic_base_threshold, self.dynamic_warmup)
                self._apply_suggested_params(suggested)
                self._notify_log(f"贝叶斯优化: 阈值 {old[0]:.3f}->{self.dynamic_base_threshold:.3f} 热身 {old[1]:.1f}->{self.dynamic_warmup:.1f}s")
                pause_task(gid)
                time.sleep(config.PAUSE_WAIT_SEC)
                resume_task(gid)
                self.window_peak_speed = 0
                self.speed_buffer.clear()
                self.window_speed_samples.clear()
                self.window_time_samples.clear()
                self.warmup_end_time = now + self.dynamic_warmup
                self.window_start_time = now
                self.window_start_bytes = comp
                self.last_speed = 0
                self.low_speed_streak = 0
                self.predictor.reset()
                self.persist_counter += 1
                if self.state_manager and self.persist_counter >= config.PERSIST_SAVE_INTERVAL:
                    self.state_manager.save(self.mode_optimizers, self.cluster)
                    self.persist_counter = 0
                self._notify_log(f"重启完成")

            self.last_speed = spd
            self._update_ui(speed_mb, base_peak, progress, global_avg_mb, status_tag)
            return self._get_ui_state()
        except Exception as e:
            logger.error(f"核心步骤异常: {e}", exc_info=True)
            self._notify_log(f"核心异常: {e}")
            return self._get_ui_state()

    def _get_ui_state(self):
        # 修复聚类显示逻辑，启用后不会显示未启用
        if self.cluster is None:
            mode_display = "未启用"
        elif len(self.cluster.features) < 2:
            mode_display = "收集中"
        else:
            mode_names = {
                0: "高速模式",
                1: "稳定模式",
                2: "波动模式",
            }
            mode_display = mode_names.get(self.current_mode_id, "均衡模式")
        if self._base_peak <= 0:
            peak_display = "测算中"
        else:
            peak_display = f"{self._base_peak/1048576:.2f} MB/s"
        return {
            "status": self._status_text,
            "speed": f"{self._speed_mb:.2f} MB/s",
            "peak": peak_display,
            "threshold": f"{self.dynamic_base_threshold:.3f}",
            "warmup": f"{self.dynamic_warmup:.1f} s",
            "global_avg": f"{self._global_avg_mb:.2f} MB/s",
            "progress": f"{self._progress:.1f}%",
            "cycle": self._status_text,
            "restart": str(self.task_restart_count),
            "mode": mode_display,
        }

    def _update_ui(self, speed_mb, base_peak, progress, global_avg_mb, status_tag):
        self._speed_mb = speed_mb
        self._base_peak = base_peak
        self._progress = progress
        self._global_avg_mb = global_avg_mb
        self._status_text = status_tag

    def get_statistics(self):
        return {
            'total_restarts': self.task_restart_count,
            'avg_speed_mb': self._global_avg_mb,
            'peak_speed_mb': self._base_peak / 1048576 if self._base_peak else 0,
            'efficiency': (self._speed_mb / (self._base_peak / 1048576)) if self._base_peak else 0,
        }

    def _notify_log(self, msg):
        if self.ui_callback:
            self.ui_callback("log", msg)

    def _notify_status(self, status):
        if self.ui_callback:
            self.ui_callback("status", status)

    def _notify_speed(self, speed_mb, base_peak):
        if self.ui_callback:
            self.ui_callback("speed", {"speed": speed_mb, "peak": base_peak})
