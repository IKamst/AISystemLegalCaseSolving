class Logger(object):
    def info(self, message: str):
        raise NotImplementedError()

    def warn(self, message: str):
        raise NotImplementedError()

    def error(self, message: str):
        raise NotImplementedError()


class Console(Logger):
    def info(self, message: str):
        print("[INFO] {}".format(message))

    def warn(self, message: str):
        print("[WARNING] {}".format(message))

    def error(self, message: str):
        print("[ERROR] {}".format(message))


class Boolean(object):
    def __init__(self, value, reason = None):
        self.value = bool(value)
        self.reason = reason

    def __bool__(self):
        return self.value

    def __str__(self):
        return '{} because {}'.format('Yes' if self.value else 'No', self.reason)

    def __repr__(self):
        return "<{!r}: {!s}>".format(self.value, self.reason)


def print_comparator(func):
    def wrapper(*args, **kwargs):
        print("{}\n\t{!r}\n\t{!r}:".format(func.__name__, args[0], args[1]))
        result = func(*args, **kwargs)
        print("\t> {}\n".format(result))
        return result
    return wrapper