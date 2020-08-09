#!/usr/bin/env python

"""Created by Raymond Hettinger on Sun, 5 Nov 2006 (PSF)
downloaded from:
    http://code.activestate.com/recipes/498245-lru-and-lfu-cache-decorators/

Updated to conform to the python-3.2 implementation of the lru_cache
which I've aslo backported for use in python 2.7 and 3.1
Copyright Brian Dolbec <brian.dolbec@gmail.com>
"""

from collections import (
    deque,
    OrderedDict,
    namedtuple,
)
from functools import wraps
from itertools import filterfalse
from heapq import nsmallest
from operator import itemgetter
from _thread import allocate_lock as Lock

class Counter(dict):
    'Mapping where default values are zero'
    def __missing__(self, key):
        return 0

_CacheInfo = namedtuple("CacheInfo", "hits misses maxsize currsize")

def lru_cache(maxsize=100):
    '''Least-recently-used cache decorator.

    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.
    Clear the cache with f.clear().
    http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used

    '''
    maxqueue = maxsize * 10
    def decorating_function(user_function,
            len=len, iter=iter, tuple=tuple, sorted=sorted, KeyError=KeyError):
        cache = {}                  # mapping of args to results
        queue = deque()             # order that keys have been used
        refcount = Counter()        # times each key is in the queue
        sentinel = object()         # marker for looping around the queue
        kwd_mark = object()         # separates positional and keyword args
        lock = Lock()

        # lookup optimizations (ugly but fast)
        queue_append, queue_popleft = queue.append, queue.popleft
        queue_appendleft, queue_pop = queue.appendleft, queue.pop

        @wraps(user_function)
        def wrapper(*args, **kwds):
            # cache key records both positional and keyword args
            key = args
            if kwds:
                key += (kwd_mark,) + tuple(sorted(kwds.items()))

            # record recent use of this key
            queue_append(key)
            refcount[key] += 1

            # get cache entry or compute if not found
            try:
                with lock:
                    result = cache[key]
                    wrapper.hits += 1
            except KeyError:
                result = user_function(*args, **kwds)
                with lock:
                    cache[key] = result
                    wrapper.misses += 1

                    # purge least recently used cache entry
                    if len(cache) > maxsize:
                        key = queue_popleft()
                        refcount[key] -= 1
                        while refcount[key]:
                            key = queue_popleft()
                            refcount[key] -= 1
                        del cache[key], refcount[key]

            # periodically compact the queue by eliminating duplicate keys
            # while preserving order of most recent access
            if len(queue) > maxqueue:
                with lock:
                    refcount.clear()
                    queue_appendleft(sentinel)
                    for key in filterfalse(refcount.__contains__,
                                            iter(queue_pop, sentinel)):
                        queue_appendleft(key)
                        refcount[key] = 1
            return result

        def cache_info():
            """Report cache statistics"""
            with lock:
                return _CacheInfo(wrapper.hits, wrapper.misses,
                    maxsize, len(cache))

        def cache_clear():
            with lock:
                cache.clear()
                queue.clear()
                refcount.clear()
                wrapper.hits = wrapper.misses = 0

        wrapper.hits = wrapper.misses = 0
        wrapper.cache_info = cache_info
        wrapper.cache_clear = cache_clear
        return wrapper
    return decorating_function


def lfu_cache(maxsize=100):
    '''Least-frequenty-used cache decorator.

    Arguments to the cached function must be hashable.
    Cache performance statistics stored in f.hits and f.misses.
    Clear the cache with f.clear().
    http://en.wikipedia.org/wiki/Least_Frequently_Used

    '''
    def decorating_function(user_function):
        cache = {}                      # mapping of args to results
        use_count = Counter()           # times each key has been accessed
        kwd_mark = object()             # separate positional and keyword args
        lock = Lock()

        @wraps(user_function)
        def wrapper(*args, **kwds):
            key = args
            if kwds:
                key += (kwd_mark,) + tuple(sorted(kwds.items()))
            use_count[key] += 1

            # get cache entry or compute if not found
            try:
                with lock:
                    result = cache[key]
                    wrapper.hits += 1
            except KeyError:
                result = user_function(*args, **kwds)
                with lock:
                    cache[key] = result
                    wrapper.misses += 1

                    # purge least frequently used cache entry
                    if len(cache) > maxsize:
                        for key, _ in nsmallest(maxsize // 10,
                                            iter(use_count.items()),
                                            key=itemgetter(1)):
                            del cache[key], use_count[key]

            return result

        def cache_info():
            """Report cache statistics"""
            with lock:
                return _CacheInfo(wrapper.hits, wrapper.misses,
                    maxsize, len(cache))

        def cache_clear():
            with lock:
                cache.clear()
                use_count.clear()
                wrapper.hits = wrapper.misses = 0

        wrapper.hits = wrapper.misses = 0
        wrapper.cache_clear = cache_clear
        return wrapper
    return decorating_function


def lru_cache2(maxsize=100): # py-2.7 or 3.1, builtin in py-3.2
    """Least-recently-used cache decorator.

    If *maxsize* is set to None, the LRU features are disabled and the cache
    can grow without bound.

    Arguments to the cached function must be hashable.

    View the cache statistics named tuple (hits, misses, maxsize, currsize) with
    f.cache_info().  Clear the cache and statistics with f.cache_clear().
    Access the underlying function with f.__wrapped__.

    See:  http://en.wikipedia.org/wiki/Cache_algorithms#Least_Recently_Used

    """
    # Users should only access the lru_cache through its public API:
    #       cache_info, cache_clear, and f.__wrapped__
    # The internals of the lru_cache are encapsulated for thread safety and
    # to allow the implementation to change (including a possible C version).

    def decorating_function(user_function,
                tuple=tuple, sorted=sorted, len=len, KeyError=KeyError):

        kwd_mark = object()             # separates positional and keyword args
        lock = Lock()
        hits = 0
        misses = 0

        if maxsize is None:
            cache = dict()              # simple cache without ordering or size limit

            @wraps(user_function)
            def wrapper(*args, **kwds):
                key = args
                if kwds:
                    key += (kwd_mark,) + tuple(sorted(kwds.items()))
                try:
                    result = cache[key]
                    wrapper.hits += 1
                except KeyError:
                    result = user_function(*args, **kwds)
                    cache[key] = result
                    wrapper.misses += 1
                return result
        else:
            cache = OrderedDict()       # ordered least recent to most recent
            cache_popitem = cache.popitem
            cache_renew = cache.move_to_end

            @wraps(user_function)
            def wrapper(*args, **kwds):
                key = args
                if kwds:
                    key += (kwd_mark,) + tuple(sorted(kwds.items()))
                try:
                    with lock:
                        result = cache[key]
                        cache_renew(key)        # record recent use of this key
                        wrapper.hits += 1
                except KeyError:
                    result = user_function(*args, **kwds)
                    with lock:
                        cache[key] = result     # record recent use of this key
                        wrapper.misses += 1
                        if len(cache) > maxsize:
                            cache_popitem(0)    # purge least recently used cache entry
                return result

        def cache_info():
            """Report cache statistics"""
            with lock:
                return _CacheInfo(hits, misses, maxsize, len(cache))

        def cache_clear():
            """Clear the cache and cache statistics"""
            with lock:
                cache.clear()
                wrapper.hits = wrapper.misses = 0

        wrapper.hits = wrapper.misses = 0
        wrapper.cache_info = cache_info
        wrapper.cache_clear = cache_clear
        return wrapper

    return decorating_function


if __name__ == '__main__':

    @lru_cache(maxsize=20)
    def f(x, y):
        return 3*x+y

    domain = list(range(5))
    from random import choice
    for i in range(1000):
        r = f(choice(domain), choice(domain))

    print((f.hits, f.misses))

    @lfu_cache(maxsize=20)
    def f(x, y):
        return 3*x+y

    domain = list(range(5))
    from random import choice
    for i in range(1000):
        r = f(choice(domain), choice(domain))

    print((f.hits, f.misses))


