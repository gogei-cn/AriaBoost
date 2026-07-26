import random
import sys
import warnings
from collections import deque
import numpy as np
from scipy.stats import norm
import config

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", message=".*ConvergenceWarning.*")
warnings.filterwarnings("ignore", message=".*length_scale.*lower bound.*")


class BayesianOptimizer:
    _global_printed = False

    def __init__(self, param_space, init_samples=None, acq_func=None, n_candidates=None):
        self.param_space = param_space
        self.init_samples = init_samples if init_samples is not None else config.BAYES_OPT_INIT_SAMPLES
        self.acq_func = acq_func if acq_func is not None else config.BAYES_OPT_ACQ_FUNC
        self.n_candidates = n_candidates if n_candidates is not None else config.BAYES_OPT_CANDIDATES
        self.X = deque(maxlen=config.MAX_OBS_HISTORY)
        self.y = deque(maxlen=config.MAX_OBS_HISTORY)
        self.best_params = None
        self.best_reward = -1.0
        self._gp = None
        self._gp_dirty = True
        self._sample_count = 0
        self._param_keys = list(param_space.keys())
        self._param_dims = len(self._param_keys)
        self._cached_candidates = None
        self._cached_mu = None
        self._cached_sigma = None
        try:
            from sklearn.gaussian_process import GaussianProcessRegressor
            from sklearn.gaussian_process.kernels import Matern
            self.GaussianProcessRegressor = GaussianProcessRegressor
            self.Matern = Matern
            self._sklearn_ok = True
            if not BayesianOptimizer._global_printed:
                print("贝叶斯优化器已启用")
                BayesianOptimizer._global_printed = True
        except ImportError:
            print("错误: scikit-learn 未安装！")
            sys.exit(1)

    def _random_sample_params(self):
        params = {}
        for key in self._param_keys:
            lo, hi = self.param_space[key]
            params[key] = lo + random.random() * (hi - lo)
        return params

    def suggest_params(self):
        if self._sample_count < self.init_samples:
            params = self._random_sample_params()
            self._sample_count += 1
            return params
        if self._gp_dirty or self._gp is None:
            try:
                X_arr = np.array(self.X)
                y_arr = np.array(self.y)
                mask = np.isfinite(y_arr)
                X_arr = X_arr[mask]
                y_arr = y_arr[mask]
                if len(X_arr) < 2:
                    return self._random_sample_params()
                # 确保 X_arr 的列数等于 _param_dims
                if X_arr.shape[1] != self._param_dims:
                    # 维度不匹配，清空数据重新开始
                    self.X.clear()
                    self.y.clear()
                    self._sample_count = 0
                    self._gp_dirty = True
                    self._gp = None
                    self._cached_candidates = None
                    return self._random_sample_params()
                kernel = 1.0 * self.Matern(length_scale=1.0, length_scale_bounds=(1e-2, 1e2), nu=2.5)
                gp = self.GaussianProcessRegressor(kernel=kernel, alpha=1e-6, normalize_y=True, random_state=42)
                gp.fit(X_arr, y_arr)
                self._gp = gp
                self._gp_dirty = False
                self._cached_candidates = None
            except (np.linalg.LinAlgError, ValueError, OverflowError):
                return self._random_sample_params()
        if self._cached_candidates is None:
            lows = []
            highs = []
            for key in self._param_keys:
                lo, hi = self.param_space[key]
                lows.append(lo)
                highs.append(hi)
            self._cached_candidates = np.random.uniform(
                low=lows,
                high=highs,
                size=(self.n_candidates, self._param_dims)
            )
            self._cached_mu, self._cached_sigma = self._gp.predict(self._cached_candidates, return_std=True)
        mu = self._cached_mu
        sigma = self._cached_sigma
        if self.acq_func == 'ucb':
            acq = mu + config.EXPLORE_KAPPA_START * sigma
        elif self.acq_func == 'ei':
            best_y = np.max(np.array(self.y))
            imp = mu - best_y
            Z = imp / (sigma + 1e-12)
            acq = imp * norm.cdf(Z) + sigma * norm.pdf(Z)
        elif self.acq_func == 'ei_decay':
            best_y = np.max(np.array(self.y))
            imp = mu - best_y
            Z = imp / (sigma + 1e-12)
            ei = imp * norm.cdf(Z) + sigma * norm.pdf(Z)
            decay_factor = max(config.EXPLORE_KAPPA_MIN / config.EXPLORE_KAPPA_START,
                               (len(self.y) / (len(self.y) + 10)) ** 0.5)
            kappa = config.EXPLORE_KAPPA_START * decay_factor
            acq = mu + kappa * sigma
        else:
            acq = mu
        best_idx = np.argmax(acq)
        params_arr = self._cached_candidates[best_idx]
        params = {}
        for i, key in enumerate(self._param_keys):
            params[key] = float(params_arr[i])
        return params

    def update(self, params, reward):
        if not np.isfinite(reward):
            return
        self.X.append([params[k] for k in self._param_keys])
        self.y.append(reward)
        self._sample_count += 1
        self._gp_dirty = True
        self._cached_candidates = None
        if reward > self.best_reward:
            self.best_reward = reward
            self.best_params = params.copy()

    def get_state_dict(self):
        return {
            "X": list(self.X),
            "y": list(self.y),
            "best_params": self.best_params,
            "best_reward": self.best_reward,
            "sample_count": self._sample_count
        }

    def load_state_dict(self, state):
        # 检查 X 的维度是否与当前参数空间匹配
        X = state.get("X", [])
        y = state.get("y", [])
        if X and len(X[0]) != self._param_dims:
            # 维度不匹配，丢弃旧数据，重新开始
            X = []
            y = []
            self._sample_count = 0
            self.best_params = None
            self.best_reward = -1.0
        else:
            self._sample_count = state.get("sample_count", 0)
            self.best_params = state.get("best_params", None)
            self.best_reward = state.get("best_reward", -1.0)
        self.X = deque(X, maxlen=config.MAX_OBS_HISTORY)
        self.y = deque(y, maxlen=config.MAX_OBS_HISTORY)
        self._gp_dirty = True
        self._cached_candidates = None