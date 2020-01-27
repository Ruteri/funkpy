import functools
import time

# TODO: add call graph of monitored functions

from collections import namedtuple

class CallTrace(object):
    """Helper structure keeping track of callers and call times
    Attributes:
        self_time: elapsed time not counting subcalls
        total_time: total elapsed time (including subcalls and excluded)
        caller: placeholder for call site
    """
    def __init__(self, caller):
        self.self_time = -time.time()
        self.total_time = self.self_time
        self.caller = caller

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
        ct = CallTrace(caller=None)
        self.call_stack.append(ct)

    def on_done(self):
        call = self.call_stack.pop()
        call.self_time += time.time()
        call.total_time += time.time()
        self.calls.append(call)

    def _pause(self):
        self.call_stack[-1].self_time += time.time()

    def _unpause(self):
        self.call_stack[-1].self_time -= time.time()

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


_WRAPPER_EXCLUDED_METHODS = [
    '__class__', '__dir__', '__doc__', '__init__', '__new__',
    '__weakref__', '__getattr__', '__getattribute__', '__setattr__',
    '__delattr__', '__dict__', '__str__', '__repr__', '__subclasshook__',
    '__sizeof__', '__reduce__', '__reduce_ex__', '__hash__', '__format__',
]


def wrapClassProfile(cl):
    class ClassProfile(cl):
        # Not mt-safe

        _n_objects = 0
        _member_profiles = {}

        def __init__(self, *args, **kwargs):
            ClassProfile._n_objects += 1
            return cl.__init__(self, *args, **kwargs)
    
    functools.update_wrapper(ClassProfile.__init__, cl.__init__)

    for attr in dir(cl):
        if attr in _WRAPPER_EXCLUDED_METHODS: continue

        fn = getattr(cl, attr)
        if not callable(fn): continue

        ClassProfile._member_profiles[attr] = CallProfile(fn)

        try:
            fn.profile = ClassProfile._member_profiles[attr]
        except:
            # wrappers
            pass

        def wrapper(*args, fn=fn, profile=ClassProfile._member_profiles[attr], **kwargs):
            profile.on_start()
            rv = fn(*args, **kwargs)
            profile.on_done()
            return rv

        wrapper.profile = ClassProfile._member_profiles[attr]

        functools.update_wrapper(wrapper, fn)
        setattr(ClassProfile, attr, wrapper)

    return ClassProfile
        


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
        profile = wrapClassProfile(cl)
        functools.update_wrapper(profile, cl, assigned=('__module__', '__name__', '__qualname__', '__doc__', '__annotations__'), updated=())
        _monitored_classes.append(profile)
        return profile

    @staticmethod
    def report():
        """Produce report for monitored calls.

        Usage:
            Profiler.report()
        """
        for call in _monitored_calls:
            # called ... times from ...
            # total ... avg ...
            self_time = sum([ct.self_time for ct in call.calls])
            total_time = sum([ct.total_time for ct in call.calls])
            print('function {}'.format(call.fn))
            print('  called {} time(s)'.format(len(call.calls)))
            print('  avg. total time {} second(s)'.format(total_time/len(call.calls)))
            print('  avg. self time {} second(s)'.format(self_time/len(call.calls)))
            for subcall_fn, subcall_calls in call.subcalls.items():
                print('  subcall {} ran {} time(s), took avg {}'.format(subcall_fn, len(subcall_calls), sum(subcall_calls)/len(subcall_calls)))

        for cl in _monitored_classes:
            total_time = 0
            print('class {} created {} time(s)'.format(cl, cl._n_objects))
            for mf_name, mf_profile in cl._member_profiles.items():
                if not mf_profile.calls: continue # ignore if not called
                mf_self_time = sum([call.self_time for call in mf_profile.calls])
                mf_total_time = sum([call.total_time for call in mf_profile.calls])
                total_time += mf_total_time
                print('  member {}'.format(mf_name))
                print('     called {} time(s)'.format(len(mf_profile.calls)))
                print('     avg. self time {} second(s)'.format(mf_self_time/len(mf_profile.calls)))
                print('     avg. total time {} second(s)'.format(mf_total_time/len(mf_profile.calls)))
            print('  spent a total of {} second(s) inside the class'.format(total_time))


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

@Profiler.profile_class
class D:
    def __init__(self, somearg):
        self.somearg = somearg

    def get_member_fn(self):
        """docstr"""
        return self.somearg

    def other_mf(self):
        pass

d = D(10)
d.get_member_fn()
d.other_mf()


Profiler.report()
