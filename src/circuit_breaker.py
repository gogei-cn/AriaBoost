import time
import config

class CircuitBreaker:
    def __init__(self, failure_threshold=None, timeout=None):
        self.failure_threshold = failure_threshold or config.RPC_MAX_FAILURES
        self.timeout = timeout or config.RPC_RECOVER_WAIT
        self.failure_count = 0
        self.state = 'CLOSED'
        self.last_failure_time = 0

    def call(self, func, *args, **kwargs):
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'HALF_OPEN'
            else:
                raise Exception("Circuit breaker open")

        try:
            result = func(*args, **kwargs)
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'
            raise e

    def reset(self):
        self.state = 'CLOSED'
        self.failure_count = 0