import json
import os
import datetime

class StateManager:
    def __init__(self, filepath):
        self.filepath = filepath
        self.tmp_path = filepath + ".tmp"

    def save(self, mode_optimizers, cluster):
        state = {
            "timestamp": datetime.datetime.now().isoformat(),
            "mode_optimizers": {str(k): v.get_state_dict() for k, v in mode_optimizers.items()},
            "cluster": cluster.get_state_dict() if cluster else None
        }
        try:
            with open(self.tmp_path, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2, default=str)
            os.replace(self.tmp_path, self.filepath)
        except Exception as e:
            print(f"状态保存失败: {e}")
            if os.path.exists(self.tmp_path):
                os.unlink(self.tmp_path)

    def load(self):
        if not os.path.exists(self.filepath):
            return None
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, PermissionError, OSError):
            if os.path.exists(self.tmp_path):
                try:
                    with open(self.tmp_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except:
                    pass
            return None