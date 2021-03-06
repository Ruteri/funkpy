import functools

def Once(fn):
    """Only allow one call to a function.

    Additional calls will result in RuntimeError.

    Usage:
        @Once
        def f(): pass

        f()
        f() # will raise RuntimeError
    """

    fn._called = False
    def wrapper(*args):
        if fn._called: raise RuntimeError('function {} called more than once'.format(fn))
        fn._called = True
        return fn(*args)

    functools.update_wrapper(wrapper, fn)
    return wrapper

# For a lack of a better place for now
def Cached(fn):
    """Cache function calls.

    Calls will return cached value (only calculated once).

    Usage:
        @Cached
        def f():
            # some long calculation
            return 5

        f()
        f() # will return 5 without calculations
    """

    fn._cached_out = None
    def wrapper(*args):
        if fn._cached_out is not None: return fn._cached_out
        fn._cached_out = fn(*args)
        return fn._cached_out

    functools.update_wrapper(wrapper, fn)
    return wrapper


import unittest

class OnceTests(unittest.TestCase):
    def test_once(self):
        @Once
        def f(arg): return arg
        self.assertEqual(f(5), 5)
        with self.assertRaises(RuntimeError):
            f(10)

class CachedTests(unittest.TestCase):
    def test_cached(self):
        self.n_calls = 0

        @Cached
        def f():
            self.n_calls += 1
            return self.n_calls

        self.assertEqual(f(), 1)
        self.assertEqual(self.n_calls, 1)
        self.assertEqual(f(), 1)
        self.assertEqual(self.n_calls, 1)

if __name__ == '__main__':
    unittest.main()
