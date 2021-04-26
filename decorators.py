class hashabledict(dict):
    def __hash__(self):
        return hash(tuple(sorted(self.items())))


class memoize(dict):
    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        key = hash(tuple(args)) + hash(hashabledict(kwargs))
        if key not in self:
            self[key] = self.func(*args, **kwargs)
        return self[key]