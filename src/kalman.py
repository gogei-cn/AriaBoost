import numpy as np

class KalmanSpeedFilter:
    """
    一维卡尔曼滤波器，用于平滑速度并估计加速度
    状态向量: [speed, acceleration]
    """
    def __init__(self, dt=1.0):
        self.dt = dt
        self.x = np.array([0.0, 0.0])          # 初始状态
        self.P = np.eye(2) * 1000.0            # 初始协方差
        self.F = np.array([[1, dt], [0, 1]])   # 状态转移矩阵
        self.H = np.array([[1, 0]])            # 观测矩阵
        self.Q = np.eye(2) * 0.01              # 过程噪声协方差
        self.R = np.array([[10.0]])            # 观测噪声协方差
        self.initialized = False

    def update(self, z):
        """输入观测速度 z，更新状态"""
        if not self.initialized:
            self.x[0] = z
            self.initialized = True
            return
        # 预测
        x_pred = self.F @ self.x
        P_pred = self.F @ self.P @ self.F.T + self.Q
        # 更新
        K = P_pred @ self.H.T @ np.linalg.inv(self.H @ P_pred @ self.H.T + self.R)
        self.x = x_pred + K @ (z - self.H @ x_pred)
        self.P = (np.eye(2) - K @ self.H) @ P_pred

    def predict(self, dt_future):
        """预测未来 dt_future 秒后的速度"""
        if not self.initialized:
            return None
        F_future = np.array([[1, dt_future], [0, 1]])
        pred_state = F_future @ self.x
        return pred_state[0]

    def get_speed(self):
        return self.x[0] if self.initialized else None

    def get_accel(self):
        return self.x[1] if self.initialized else None