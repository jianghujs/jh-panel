
import time
from functools import wraps
def retry(max_retry=3, delay=1):
    """装饰器，用于在函数失败时重试"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max_retry):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if i < max_retry - 1:  # i is zero indexed
                        time.sleep(delay)
                        continue
                    else:
                        print(f"Still failed after {max_retry} attempts.")
                        raise
        return wrapper
    return decorator