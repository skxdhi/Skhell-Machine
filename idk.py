import inspect

def pipe(val, *funcs):
    output = val
    for func in funcs:
        output = func(output)
    return output

def compose(*funcs):
    def wrapper(val):
        output = val
        return pipe(val, *funcs)
    return wrapper

def memoize(func):
    cache = {}
    def wrapper(*args):
        if args not in cache.keys():
            cache[args] = func(*args)
        return cache[args]
    return wrapper

def flatten(l):
    r = []
    for item in l:
        if type(item) is list:
            r.extend(flatten(item))
        else:
            r.append(item)
    return r

def unique(l):
    seen = set()
    r = []
    for item in l:
        if item not in seen:
            r.append(item)
            seen.add(item)
    return r

#------------------------------

def chunk(l, size):
    r = []
    for item in l:
        if not r or len(r[-1]) >= size:
            r.append([])
        r[-1].append(item)
    return r

def freq_sort(l: list) -> list:
    return sorted(l, key=lambda x: (-l.count(x), x))

def is_prime(x: int) -> bool:
    if x < 2:
        return False
    for i in range(2, int(x ** 0.5) + 1):
        if x % i == 0:
            return False
    return True

def flatten_and_find_primes(l: list) -> list:
    l = flatten(l)
    l = filter(is_prime, l)
    l = list(sorted(l, reverse=True))
    l = unique(l)
    return l

def primes():
    n = 2
    while True:
        if is_prime(n):
            yield n
        n += 1

def squared_sevens_primes():
    prime_stream = primes()
    sevens_stream = (x for x in prime_stream if x%10 == 7)
    squared_stream = (y ** 2 for y in sevens_stream)
    return squared_stream

def join_generators(*generators):
    for gen in generators:
        yield from gen

def interleave(*generators):
    genl = list(generators)
    while len(genl) > 0:
        for gen in list(genl):
            try:
                yield next(gen)
            except StopIteration:
                genl.remove(gen)

def match_case(sub):
    z = yield
    while True:
        z = yield (sub in z)