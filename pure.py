"""Pure function enforcement utility.

Mark functions @pure to enforce immutability of arguments.
Attepmts to modify the arguments will result in AttributeError,
similar to behaviour of @property.

This is meant to be used in development and testing environments as a safeguard.

Usage:
    @pure
    def pure_function(immutable, arguments):
        # modifying arguments will result in an exception (AttributeError)
        pass

    class ClassWithPureMember(object):
        @pure_mf
        def pure_member(self, arguments):
            # modifying self or arguments will result in AttributeError
            pass
"""


def _raise(ex):
    raise ex


_CONST_WRAPPER_EXCLUDED_METHODS = [
    '__class__', '__dir__', '__doc__', '__init__', '__new__',
    '__weakref__', '__getattr__', '__getattribute__', '__setattr__',
    '__delattr__', '__dict__', '__str__', '__repr__',
]


class _const_wrapper(object):
    """Const object wrapper.

    This class wraps objects and overwrites __setattr__ to disalow modification.
    Attributes from dir(obj) are attached to the wrapper from the wrapped object.
    """

    def __init__(self, obj):
        object.__setattr__(self, '_obj', obj)
        object.__setattr__(self, '__init__', lambda: _raise('cannot reinitialize immutable object'))

        for field_name in dir(obj):
            if field_name in _CONST_WRAPPER_EXCLUDED_METHODS: continue
            wrapped_field = getattr(obj, field_name)
            if callable(wrapped_field):
                member_wrapper = lambda _self, *args, **kwargs: wrapped_field(obj, *args, **kwargs)
                object.__setattr__(self, field_name, member_wrapper)
            else:
                object.__setattr__(self, field_name, wrapped_field)

    def __getattribute__(self, key):
        if key == '_obj':
            return object.__getattribute__(self, '_obj')

        robj = getattr(object.__getattribute__(self, '_obj'), key)
        try:
            # If it fails, robj is immutable, and we check assignment in parent,
            # so we can just return unwrapped robj
            robj.__setattr__('_is_const_wrapped', True)
            return _const_wrapper(robj)
        except AttributeError:
            return robj

    def __setattr__(self, key, value):
        raise AttributeError('cannot set "{}.{}": object is immutable'.format(self, key))

    def __repr__(self):
        return '<const {}>'.format(repr(object.__getattribute__(self, '_obj')))

    def __str__(self):
        return '<const {}>'.format(str(object.__getattribute__(self, '_obj')))


def pure(fn):
    def wrapper(*args, **kwargs):
        return fn(*[_const_wrapper(arg) for arg in args], **{k: _const_wrapper(v) for k, v in kwargs.items()})
    return wrapper


def pure_mf(fn):
    def wrapper(self, *args, **kwargs):
        return fn(_const_wrapper(self), *[_const_wrapper(arg) for arg in args], **{k: _const_wrapper(v) for k, v in kwargs.items()})
    return wrapper
