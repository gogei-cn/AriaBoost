import time
import requests
import config
from circuit_breaker import CircuitBreaker

class RPCTaskCache:
    def __init__(self, cache_ms=300):
        self.cache_ms = cache_ms
        self.last_gid = None
        self.last_info = {}
        self.last_ts = 0

    def get(self):
        now = time.time() * 1000
        if now - self.last_ts < self.cache_ms and self.last_gid is not None:
            return self.last_gid, self.last_info
        return None, None

    def set(self, gid, info):
        self.last_gid = gid
        self.last_info = info
        self.last_ts = time.time() * 1000

_task_cache = RPCTaskCache()
_rpc_breaker = CircuitBreaker()

def rpc_retry(max_retries=3, base_delay=1.0):
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (requests.ConnectionError, requests.Timeout, requests.JSONDecodeError) as e:
                    last_exception = e
                    time.sleep(base_delay * (2 ** attempt))
            raise last_exception
        return wrapper
    return decorator

@rpc_retry()
def rpc_call(method, params=None):
    payload = {
        "jsonrpc": "1.0",
        "method": method,
        "id": "motrix-ai-optimizer",
        "params": params if params is not None else []
    }
    resp = requests.post(config.RPC_URL, json=payload, timeout=5)
    return resp.json()

def get_active_task():
    cached_gid, cached_info = _task_cache.get()
    if cached_gid is not None:
        return cached_gid, cached_info
    ret = rpc_call("aria2.tellActive", [f"token:{config.RPC_TOKEN}"])
    if not ret or "error" in ret:
        return None, {}
    task_list = ret["result"]
    if task_list:
        task = task_list[0]
        gid = task["gid"]
        info = {
            "status": task.get("status", "active"),
            "downloadSpeed": int(task.get("downloadSpeed", 0)),
            "completedLength": int(task.get("completedLength", 0)),
            "totalLength": int(task.get("totalLength", 0)),
        }
        _task_cache.set(gid, info)
        return gid, info
    return None, {}

def get_task_info_fallback(gid):
    try:
        ret = rpc_call("aria2.tellStatus", [f"token:{config.RPC_TOKEN}", gid])
        if "error" in ret:
            return None, 0, 0, 0
        data = ret["result"]
        return data["status"], int(data["downloadSpeed"]), int(data["completedLength"]), int(data["totalLength"])
    except Exception:
        return None, 0, 0, 0

def pause_task(gid):
    rpc_call("aria2.pause", [f"token:{config.RPC_TOKEN}", gid])

def resume_task(gid):
    rpc_call("aria2.unpause", [f"token:{config.RPC_TOKEN}", gid])

class RPCHealthChecker:
    def __init__(self):
        self.url = config.RPC_URL
        self.token = config.RPC_TOKEN
        self.failure_count = 0
        self.last_success = time.time()

    def check(self):
        try:
            resp = requests.post(self.url, json={
                "jsonrpc": "1.0", "method": "aria2.getVersion",
                "id": "health", "params": [f"token:{self.token}"]
            }, timeout=5)
            if resp.status_code == 200 and "result" in resp.json():
                self.failure_count = 0
                self.last_success = time.time()
                return True
        except Exception:
            pass
        self.failure_count += 1
        return False

    def is_healthy(self):
        return self.failure_count < config.RPC_MAX_FAILURES

    def recover(self):
        time.sleep(config.RPC_RECOVER_WAIT)
        self.failure_count = 0