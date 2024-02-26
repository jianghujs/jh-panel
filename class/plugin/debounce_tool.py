import threading
from functools import wraps

def debounce(delay):
    """防抖装饰器，以非阻塞方式延迟执行被装饰的函数"""
    def decorator(func):
        # 使用字典存储定时器，以支持实例方法
        timers = {}
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 使用函数ID和实例ID（如果有）作为键
            key = (id(func), id(args[0]) if args else None)
            timer = timers.get(key)
            
            # 定义实际执行函数的内部函数
            def performCall():
                timers.pop(key, None)  # 执行后从字典中移除定时器
                # 使用线程执行被装饰的函数
                thread = threading.Thread(target=func, args=args, kwargs=kwargs)
                thread.start()
            
            # 如果已经有定时器在运行，则取消它
            if timer is not None:
                timer.cancel()
            
            # 创建并存储一个新的定时器
            timer = threading.Timer(delay, performCall)
            timers[key] = timer
            
            # 启动定时器
            timer.start()
        
        return wrapper
    return decorator
