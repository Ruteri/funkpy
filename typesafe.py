from functools import (update_wrapper, wraps)
import typing
import logging

"""Supported types:
(most) builtins
typing.List
typing.Dict
typing.Callable
"""

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("@typesafe")

def is_list(c):
    return c == list or c == typing.List or (hasattr(c, '__origin__') and c.__origin__ == typing.List)

def check_list(obj):
    if not issubclass(list, type(obj)): return False
    return True


def is_dict(c):
    return c == dict or c == typing.Dict or (hasattr(c, '__origin__') and c.__origin__ == typing.Dict)

def check_dict(obj):
    if not issubclass(dict, type(obj)): return False
    return True


def is_callable(c):
    return c == typing.Callable or (hasattr(c, '__origin__') and c.__origin__ == typing.Callable)

def check_callable(obj):
    if not callable(obj): return False
    return True


def _get_check_list_args_fn(expected_class):
    if not hasattr(expected_class, '__args__') or not expected_class.__args__: return None
    expected_arg_type = expected_class.__args__[0]
    check = _get_check_fn(expected_arg_type)
    def check_args(obj):
        return all(check(v) for v in obj)
    return check_args


def _get_check_dict_args_fn(expected_class):
    if not hasattr(expected_class, '__args__') or not expected_class.__args__: return None
    argtypes = expected_class.__args__
    checks = [_get_check_fn(c) for c in argtypes]
    def check_args(obj):
        for items in obj.items():
            for index, item in enumerate(items):
                if not checks[index](item):
                    return False
        return True
    return check_args

def _type_matches(expected, actual):
    if expected is None: return True
    if expected == typing.Any: return True
    return expected == actual or issubclass(expected, actual)

def _get_check_callable_args_fn(expected_class):
    if not hasattr(expected_class, '__args__') or not expected_class.__args__: return None
    expected_args = expected_class.__args__[:-1]
    expected_rt = expected_class.__args__[-1]

    def check(obj):
        args = obj.__code__.co_varnames
        annotations = obj.__annotations__
        argtypes = [annotations.get(arg, None) for arg in args]
        for index, expected_arg in enumerate(expected_args):
            if expected_arg == Ellipsis:
                break # ignore the rest of the arguments
            if not _type_matches(expected_arg, argtypes[index]):
                return False
        return _type_matches(expected_rt, annotations.get('return'))
    return check

# TODO: flatten checks
def _get_check_fn(expected_class):
    if expected_class is None or expected_class == typing.Any:
        return None
    elif is_list(expected_class):
        argscheck_fn = _get_check_list_args_fn(expected_class)
        if argscheck_fn:
            return lambda o: check_list(o) and argscheck_fn(o)
        return check_list
    elif is_dict(expected_class):
        argscheck_fn = _get_check_dict_args_fn(expected_class)
        if argscheck_fn:
            return lambda o: check_dict(o) and argscheck_fn(o)
        return check_dict
    elif is_callable(expected_class):
        argscheck_fn = _get_check_callable_args_fn(expected_class)
        if argscheck_fn:
            return lambda o: check_callable(o) and argscheck_fn(o)
        return check_callable
    else:
        return lambda o, expected_class=expected_class: _type_matches(expected_class, type(o))

class Typesafe(object):
    def __init__(self, f):
        self.f = f

        args = self.f.__code__.co_varnames
        annotations = self.f.__annotations__

        self.retcheck = _get_check_fn(annotations.get('return', None))

        self.checks = [_get_check_fn(annotations.get(arg, None)) for arg in args]
        self.kw_map = {arg: index for index, arg in enumerate(args)}

        update_wrapper(self, f)

    def __call__(self, *args, **kwargs):
        log.debug('calling with {} {}'.format(args, kwargs))
        for index, arg in enumerate(args):
            check = self.checks[index]
            if check and not check(arg):
                raise TypeError('unexpected argument {} passed to function at position {}'.format(arg, index))

        for key, arg in kwargs.items():
            index = self.kw_map[key]
            check = self.checks[index]
            if check and not check(arg):
                raise TypeError('unexpected argument {} passed to function as key {}'.format(arg, key))

        ret = self.f(*args, **kwargs)
        if self.retcheck and not self.retcheck(ret):
            raise TypeError('unexpected return value {} from function'.format(ret))

        return ret

def Typesafe_mf(f):
    ts = Typesafe(f)
    @wraps(f)
    def wrapper(self, *args, **kwargs):
        return ts.__call__(self, *args, **kwargs)
    return wrapper
