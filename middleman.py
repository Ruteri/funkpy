from typing import Callable, Optional
import functools

class Middleman(object):
    """Function middleman

    Handles pre/post hooks for functions

    Args:
        pre_hook: hook called with arguments before calling wrapped function
        post_hook: hook called with return value and arguments after calling wrapped function

    Basic usage:
    @Middleman(pre_hook=lambda *args, **kwargs: None
               post_hook=lambda rv, *args, **kwargs: None)
    def some_function(some_args):
        return None
    """

    def __init__(self, *, pre_hook: Optional[Callable] = None, post_hook: Optional[Callable] = None):
        self.pre_hook = pre_hook
        self.post_hook = post_hook

    def __call__(self, fn):
        pre_hook = self.pre_hook
        post_hook = self.post_hook
        def wrapper(*args, **kwargs):
            if pre_hook: pre_hook(*args, **kwargs)
            rv = fn(*args, **kwargs)
            if post_hook: post_hook(rv, *args, **kwargs)
            return rv
        functools.update_wrapper(wrapper, fn)
        return wrapper

class Middleman_mf(Middleman):
    """Member function middleman

    Handles pre/post hooks for members

    Args:
        pre_hook: hook called with self and arguments before calling wrapped function
        post_hook: hook called with self, return value and arguments after calling wrapped function

    Basic usage:
    class SomeClass(object):
        @Middleman_mf(pre_hook=lambda obj, *args, **kwargs: None,
                      post_hook: lambda obj, rv, *args, **kwargs: None)
        def some_member_function(self, some_args):
            return None
    """

    def __call__(self, fn):
        pre_hook = self.pre_hook
        post_hook = self.post_hook
        def wrapper(self, *args, **kwargs):
            if pre_hook: pre_hook(self, *args, **kwargs)
            rv = fn(self, *args, **kwargs)
            if post_hook: post_hook(self, rv, *args, **kwargs)
            return rv
        functools.update_wrapper(wrapper, fn)
        return wrapper


class Middleman_cl(object):
    """Class-wide middleman

    Handles pre/post hooks for all members of a class

    Args:
        pre_hook: hook called with self, function name and arguments before calling member function
        post_hook: hook called with self, returned value and arguments after calling member function

    Basic usage:
    @Middleman_cl(pre_hook=lambda obj, mf, *args, **kwargs: None,
                  post_hook: lambda obj, mf, rv, *args, **kwargs: None)
    class SomeClass(object):
        def some_fn(self, arg1, arg2): pass
    """

    def __init__(self, pre_hook: Optional[Callable] = None, post_hook: Optional[Callable] = None):
        self.pre_hook = pre_hook
        self.post_hook = post_hook

    def __call__(self, cl):
        pre_hook = self.pre_hook
        post_hook = self.post_hook
        class C(object):
            def __init__(self, *args, **kwargs):
                self._obj = cl(*args, **kwargs)
                for mf in dir(self._obj):
                    if not callable(getattr(self._obj, mf)) or mf.startswith("__"): continue
                    setattr(self, mf, lambda *args, **kwargs: self._call_wrapped(mf, args, **kwargs))
                    functools.update_wrapper(getattr(self, mf), getattr(self._obj, mf))

            def _call_wrapped(self, mf, *args, **kwargs):
                if pre_hook: pre_hook(self._obj, mf, *args, **kwargs)
                rv = getattr(self._obj, mf)(*args, **kwargs)
                if post_hook: post_hook(self._obj, mf, rv, *args, **kwargs)
                return rv

        functools.update_wrapper(C, cl, assigned=('__module__', '__name__', '__qualname__', '__doc__'), updated=())
        return C
