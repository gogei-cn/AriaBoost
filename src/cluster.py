import math
import random
import config

class SpeedPatternCluster:
    def __init__(self, k=None, feature_window=None, update_freq=None):
        self.k = k if k is not None else config.CLUSTER_K
        self.feature_window = feature_window if feature_window is not None else config.CLUSTER_FEATURE_WINDOW
        self.update_freq = update_freq if update_freq is not None else config.CLUSTER_UPDATE_FREQ
        self.features = []
        self.labels = []
        self.centroids = None
        self.next_update = self.feature_window
        self._scaler_mean = None
        self._scaler_std = None
        try:
            from sklearn.cluster import KMeans
            self._sklearn_cluster = KMeans
        except ImportError:
            self._sklearn_cluster = None

    def extract_features(self, window_speeds, window_times, peak_speed, window_duration, trigger_speed):
        n = len(window_speeds)
        avg_speed = sum(window_speeds) / n if n > 0 else 0
        slope = 0.0
        if n >= 2:
            x_mean = sum(window_times) / n
            y_mean = avg_speed
            num = sum((window_times[i] - x_mean) * (window_speeds[i] - y_mean) for i in range(n))
            den = sum((t - x_mean) ** 2 for t in window_times)
            if den != 0:
                slope = num / den
        feat = [peak_speed, avg_speed, slope, window_duration, trigger_speed]
        return [0.0 if not math.isfinite(v) else v for v in feat]

    def _normalize(self, data):
        n = len(data)
        if n == 0:
            return [], [], []
        dim = len(data[0])
        mean = [0.0] * dim
        for row in data:
            for d in range(dim):
                mean[d] += row[d]
        mean = [m / n for m in mean]
        std = [0.0] * dim
        for row in data:
            for d in range(dim):
                diff = row[d] - mean[d]
                std[d] += diff * diff
        std = [math.sqrt(s / n) if s > 1e-12 else 1.0 for s in std]
        norm = []
        for row in data:
            row_norm = [(row[d] - mean[d]) / std[d] for d in range(dim)]
            norm.append(row_norm)
        return norm, mean, std

    def _kmeans_pure(self, data, k, max_iter=100):
        n = len(data)
        dim = len(data[0]) if n > 0 else 0
        if n == 0 or k <= 0:
            return [], []
        indices = list(range(n))
        random.shuffle(indices)
        centroids = [data[i][:] for i in indices[:k]]
        for _ in range(max_iter):
            labels = []
            for point in data:
                min_dist_sq = float('inf')
                best_c = 0
                for c_idx, cent in enumerate(centroids):
                    dist_sq = sum((point[d] - cent[d]) ** 2 for d in range(dim))
                    if dist_sq < min_dist_sq:
                        min_dist_sq = dist_sq
                        best_c = c_idx
                labels.append(best_c)
            new_centroids = [[0.0] * dim for _ in range(k)]
            counts = [0] * k
            for i, point in enumerate(data):
                c = labels[i]
                for d in range(dim):
                    new_centroids[c][d] += point[d]
                counts[c] += 1
            for c in range(k):
                if counts[c] > 0:
                    new_centroids[c] = [v / counts[c] for v in new_centroids[c]]
                else:
                    new_centroids[random.randint(0, n-1)] = data[random.randint(0, n-1)]
            shift_sq = 0.0
            for c in range(k):
                shift_sq += sum((new_centroids[c][d] - centroids[c]) ** 2 for d in range(dim))
            if shift_sq < 1e-8:
                break
            centroids = new_centroids
        return labels, centroids

    def _kmeans_sklearn(self, data, k):
        import numpy as np
        try:
            model = self._sklearn_cluster(n_clusters=k, random_state=42, n_init=10)
            labels = model.fit_predict(np.array(data))
            centroids = model.cluster_centers_.tolist()
            return labels.tolist(), centroids
        except Exception:
            return self._kmeans_pure(data, k)

    def add_window(self, features):
        self.features.append(features)
        if len(self.features) < self.feature_window:
            self.labels.append(0)
            return 0
        if len(self.features) == self.feature_window or (self.update_freq > 0 and len(self.features) >= self.next_update):
            self.recluster()
            self.next_update = len(self.features) + self.update_freq
        if self.centroids is not None and self._scaler_mean is not None:
            norm_features = [(features[d] - self._scaler_mean[d]) / self._scaler_std[d] for d in range(len(features))]
            label = self._predict_one(norm_features)
        else:
            label = 0
        self.labels.append(label)
        return label

    def recluster(self):
        if len(self.features) < self.k:
            return
        try:
            norm_data, mean, std = self._normalize(self.features)
            self._scaler_mean = mean
            self._scaler_std = std
            if self._sklearn_cluster is not None:
                labels, centroids = self._kmeans_sklearn(norm_data, self.k)
            else:
                labels, centroids = self._kmeans_pure(norm_data, self.k)
            self.centroids = centroids
            self.labels = labels
        except Exception as e:
            print(f"聚类失败: {e}")

    def _predict_one(self, norm_features):
        if self.centroids is None:
            return 0
        min_dist_sq = float('inf')
        best_c = 0
        for c_idx, cent in enumerate(self.centroids):
            dist_sq = sum((norm_features[d] - cent[d]) ** 2 for d in range(len(norm_features)))
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                best_c = c_idx
        return best_c

    def get_state_dict(self):
        return {
            "features": self.features,
            "labels": self.labels,
            "centroids": self.centroids,
            "scaler_mean": self._scaler_mean,
            "scaler_std": self._scaler_std,
            "next_update": self.next_update
        }

    def load_state_dict(self, state):
        self.features = state.get("features", [])
        self.labels = state.get("labels", [])
        self.centroids = state.get("centroids", None)
        self._scaler_mean = state.get("scaler_mean", None)
        self._scaler_std = state.get("scaler_std", None)
        self.next_update = state.get("next_update", self.feature_window)