import threading

class Timer(threading.Timer):
    @staticmethod
    def createTimeout(duration, callback, args = [], kwargs = {}, old_timer = None, max_count = 0 ):
        if old_timer != None:
            old_timer.cancel()
            max_count = old_timer.max_count

        max_count = max_count - 1
        if max_count == 0:
            callback(*args, **kwargs)
            return None

        timer = Timer(duration, callback, args, kwargs )
        timer.start()
        timer.max_count = max_count
        return timer
