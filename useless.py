from typing import Callable, Any

class EList(list):
    @classmethod
    def empty(cls):
        return cls()

    def chunk(self, n):
        l = EList.empty()
        if n <= 0:
            raise ValueError("chunk size must be greater than 0")
        for i in range(0, len(self), n):
            l.append(self[i:i + n])
        return l

    def unique(self):
        l = EList.empty()
        for item in self:
            if item not in l:
                l.append(item)
        return l

    def round_robin(self, amount):
        l = EList.empty()
        if isinstance(amount, float):
            raise ValueError("rotation amount cannot be a float")
        for i in range(0, len(self)):
            l.append(self[(i - amount) % len(self)])
        return l

    def split_at(self, idx):
        if idx < 0 or idx > len(self): raise ValueError("split position is not in list")
        return [self[:idx], self[idx:]]

    def flatten(self):
        l = EList.empty()
        for item in self:
            if isinstance(item, list):
                l.extend(EList(item).flatten())
            else:
                l.append(item)
        return l

    def count_where(self, func: Callable[[Any], bool]):
        return len(list(filter(func, self)))

    def find_first(self, func: Callable[[Any], bool]):
        for item in self:
            if func(item):
                return item
        return None

    def remove_where(self, func: Callable[[Any], bool]):
        return EList([x for x in self if not func(x)])

    def replace_where(self, func: Callable[[Any], bool], x):
        l = EList(self.copy())
        for i in range(0, len(l)):
            item = l[i]
            if func(item):
                l[i] = x
        return l

    def all_same(self):
        return len(self.unique()) <= 1

    def indexes_of(self, x):
        l = EList.empty()
        for i in range(0, len(self)):
            item = self[i]
            if item == x:
                l.append(i)
        return l

def number_range(s, e, step):
    if step == 0:
        raise ValueError("step cannot be 0")

    return range(s, e + step, step)

def compose(*functions):
    def new_function(value):
        result = value
        for func in reversed(functions):
            result = func(result)
        return result
    return new_function

def pipe(value, *functions):
    result = value
    for func in functions:
        result = func(result)
    return result

def once(func):
    ran = False

    def wrapper(*args, **kwargs):
        nonlocal ran

        if not ran:
            ran = True
            return func(*args, **kwargs)

        return None

    return wrapper