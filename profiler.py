import functools
import time

# TODO: add call graph of monitored functions

class CallProfile(object):
    """Function profile.

    Profile is injected into function dict as `profile`.
    """
    # TODO: also keep track of total time in function
    # TODO: (maybe) monitor stack
    # TODO: (maybe) monitor exceptions
    def __init__(self, fn):
        self.fn = fn
        self.call_stack = [] # time deltas
        self.calls = []
        self.subcalls = {}

    def exclude(self, fn):
        """Exclude subcall from function metrics.

        Useful for calls that are present in test env (prints, logs, waits).

        Usage:
            func.profile.exclude(print)('something that will take a long time to do')
        """
        def wrapper(*args, **kwargs):
            self._pause()
            rv = fn(*args, **kwargs)
            self._unpause()
            return rv
        functools.update_wrapper(wrapper, fn)
        return wrapper

    def subcall(self, fn):
        """Measure call within a function.

        Useful for keeping track of function self-time and external calls.

        Usage:
            func.profile.subcall(other_internal_fn)()
        """
        def wrapper(*args, **kwargs):
            return self._subcall(fn, *args, **kwargs)
        functools.update_wrapper(wrapper, fn)
        return wrapper

    def on_start(self):
        self.call_stack.append(-time.time())

    def on_done(self):
        self.calls.append(time.time() + self.call_stack.pop())

    def _pause(self):
        self.call_stack[-1] += time.time()

    def _unpause(self):
        self.call_stack[-1] -= time.time()

    def _subcall(self, fn, *args, **kwargs):
        self._pause()
        fn_key = fn.__qualname__
        ts = time.time()
        rv = fn(*args, **kwargs)
        te = time.time()
        if fn_key not in self.subcalls:
            self.subcalls[fn_key] = []
        self.subcalls[fn_key].append(te - ts)
        self._unpause()
        return rv

    def report(self):
        print('function {} called {} time(s)'.format(self.fn, len(self.calls)))
        print('  avg. self time {}'.format(sum(self.calls)/len(self.calls)))
        for subcall_fn, subcall_calls in self.subcalls.items():
            print('  subcall {} ran {} time(s), took avg {}'.format(subcall_fn, len(subcall_calls), sum(subcall_calls)/len(subcall_calls)))


class ClassProfile(object):
    def __init__(self, cl):
        functools.update_wrapper(self, cl)


_monitored_calls = []
_monitored_classes = []

class Profiler(object):
    """Profiler facade class.

    Object of this class is assigned to function dict.
    Usage:
        @Profiler.profile
        def profiled_function():
            pass
        Profiler.report()
    """

    @staticmethod
    def profile(fn):
        """Profiler function decorator.

        Profiler then keeps track of various stats about the wrapped function.
        """
        profile = CallProfile(fn)
        _monitored_calls.append(profile)
        def wrapper(*args, **kwargs):
            profile.on_start()
            rv = fn(*args, **kwargs)
            profile.on_done()
            return rv
        functools.update_wrapper(wrapper, fn)
        wrapper.profile = profile
        return wrapper

    @staticmethod
    def profile_class(cl):
        profile = ClassProfile(cl)
        _monitored_classes.append(profile)
        return profile

    @staticmethod
    def report():
        """Produce report for monitored calls.

        Usage:
            Profiler.report()
        """
        for call in _monitored_calls:
            call.report()


@Profiler.profile
def run_f():
    run_f.profile.exclude(time.sleep)(0.01)
    run_f.profile.subcall(time.sleep)(0.1)
    time.sleep(0.1)
    return 5

@Profiler.profile
def sort_items(items):
    sort_items.profile.subcall(items.sort)()

class C:
    @Profiler.profile
    def mf(self):
        time.sleep(0.1)
        run_f()

c = C()

import random
for _ in range(2):
    run_f()
    c.mf()
    sort_items([random.randint(0, 1000) for _ in range(10000)])


Profiler.report()
