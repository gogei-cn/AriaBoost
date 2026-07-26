import numpy as np
from sklearn.ensemble import IsolationForest

class AnomalyDetector:
    def __init__(self, contamination=0.1):
        self.model = IsolationForest(contamination=contamination, random_state=42)
        self.fitted = False
        self.buffer = []

    def add_sample(self, features):
        self.buffer.append(features)
        if len(self.buffer) >= 20 and not self.fitted:
            try:
                self.model.fit(np.array(self.buffer))
                self.fitted = True
            except:
                pass

    def detect(self, features):
        if not self.fitted:
            return False
        try:
            pred = self.model.predict([features])
            return pred[0] == -1
        except:
            return False