import time
import math
import numpy as np
from collections import deque
import config
from kalman import KalmanSpeedFilter


class WeightedLinearPredictor:
    def __init__(self, max_points=10, alpha=0.9):
        self.times = deque(maxlen=max_points)
        self.speeds = deque(maxlen=max_points)
        self.alpha = alpha

    def add_point(self, t, speed):
        self.times.append(t)
        self.speeds.append(speed)

    def predict(self, future_time):
        n = len(self.times)
        if n < 3:
            return None
        t_ref = self.times[-1]
        rel_t = [t - t_ref for t in self.times]
        weights = [self.alpha ** (n - 1 - i) for i in range(n)]
        sum_w = sum(weights)
        sum_t = sum(w * t for w, t in zip(weights, rel_t))
        sum_y = sum(w * s for w, s in zip(weights, self.speeds))
        sum_tt = sum(w * t * t for w, t in zip(weights, rel_t))
        sum_ty = sum(w * t * s for w, t, s in zip(weights, rel_t, self.speeds))
        denom = sum_w * sum_tt - sum_t * sum_t
        if abs(denom) < 1e-9:
            return sum_y / sum_w
        b = (sum_w * sum_ty - sum_t * sum_t) / denom
        a = (sum_y - b * sum_t) / sum_w
        return a + b * (future_time - t_ref)


class SpeedDecayPredictor:
    def __init__(self, window_size=None):
        if window_size is None:
            window_size = config.FIT_WINDOW_SIZE
        self.speed_window = deque(maxlen=window_size)
        self.time_window = deque(maxlen=window_size)
        self.slope_history = deque(maxlen=window_size)
        self.slope_time_history = deque(maxlen=window_size)
        self.first_order_slope = 0.0
        self.second_order_slope = 0.0
        self._volatility_cache = 0.0
        self._vol_dirty = True
        self._slope2_dirty = True
        self.wlp = WeightedLinearPredictor(max_points=12, alpha=0.85)
        self.kalman = KalmanSpeedFilter(dt=1.0)

    def add_sample(self, speed, timestamp):
        self.speed_window.append(speed)
        self.time_window.append(timestamp)
        self.wlp.add_point(timestamp, speed)
        self.kalman.update(speed)
        slope = self._fit_single_slope()
        if slope != 0:
            self.slope_history.append(slope)
            self.slope_time_history.append(timestamp)
        self._vol_dirty = True
        self._slope2_dirty = True

    def _fit_single_slope(self):
        n = len(self.speed_window)
        if n < 4:
            self.first_order_slope = 0.0
            return 0.0
        x = list(self.time_window)
        y = list(self.speed_window)
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((t - x_mean) ** 2 for t in x)
        if abs(denominator) < 1e-12:
            self.first_order_slope = 0.0
            return 0.0
        self.first_order_slope = numerator / denominator
        return self.first_order_slope

    def _calc_second_order(self):
        if not self._slope2_dirty:
            return self.second_order_slope
        n = len(self.slope_history)
        if n < 4:
            self.second_order_slope = 0.0
            self._slope2_dirty = False
            return 0.0
        x = list(self.slope_time_history)
        y = list(self.slope_history)
        x_mean = sum(x) / n
        y_mean = sum(y) / n
        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((t - x_mean) ** 2 for t in x)
        if abs(denominator) < 1e-12:
            self.second_order_slope = 0.0
            self._slope2_dirty = False
            return 0.0
        self.second_order_slope = numerator / denominator
        self._slope2_dirty = False
        return self.second_order_slope

    def _calc_volatility(self):
        if not self._vol_dirty:
            return self._volatility_cache
        n = len(self.speed_window)
        if n < 4:
            self._volatility_cache = 0.0
            self._vol_dirty = False
            return 0.0
        speeds = list(self.speed_window)
        mean = sum(speeds) / n
        if abs(mean) < 1e-12:
            self._volatility_cache = 0.0
            self._vol_dirty = False
            return 0.0
        variance = sum((s - mean) ** 2 for s in speeds) / n
        self._volatility_cache = math.sqrt(variance) / mean
        self._vol_dirty = False
        return self._volatility_cache

    def get_adjusted_threshold(self, base_threshold):
        self._calc_second_order()
        max_slope_ref = -0.01 * 1024 * 1024
        first_order_factor = min(1.0, max(-1.0, self.first_order_slope / max_slope_ref))
        second_order_ref = -0.001 * 1024
        second_order_factor = min(1.0, max(-1.0, self.second_order_slope / second_order_ref)) * config.SECOND_ORDER_SENSITIVITY
        total_adjust = (first_order_factor + second_order_factor) * config.MAX_ADJUST_RATIO
        adjusted = base_threshold * (1 + total_adjust)
        return max(0.3, min(0.95, adjusted))

    def is_network_jitter(self):
        vol = self._calc_volatility()
        return vol > config.VOLATILITY_THRESHOLD

    def predict_speed_in(self, seconds, current_speed):
        kalman_pred = self.kalman.predict(seconds)
        if kalman_pred is not None:
            return max(0.0, kalman_pred)
        future_time = time.time() + seconds
        wl_pred = self.wlp.predict(future_time)
        if wl_pred is not None and len(self.wlp.times) >= 4:
            return max(0.0, wl_pred)
        self._calc_second_order()
        pred = current_speed + self.first_order_slope * seconds + 0.5 * self.second_order_slope * (seconds ** 2)
        return max(0.0, pred)

    def predict_with_confidence(self, seconds, current_speed):
        pred = self.predict_speed_in(seconds, current_speed)
        if len(self.speed_window) > 3:
            speeds = list(self.speed_window)
            std = np.std(speeds)
            ci = 1.96 * std / np.sqrt(len(speeds))
        else:
            ci = current_speed * 0.2
        return pred, ci

    def reset(self):
        self.speed_window.clear()
        self.time_window.clear()
        self.slope_history.clear()
        self.slope_time_history.clear()
        self.first_order_slope = 0.0
        self.second_order_slope = 0.0
        self._volatility_cache = 0.0
        self._vol_dirty = True
        self._slope2_dirty = True
        self.wlp = WeightedLinearPredictor(max_points=12, alpha=0.85)
        self.kalman = KalmanSpeedFilter(dt=1.0)