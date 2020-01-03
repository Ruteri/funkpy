from functools import (update_wrapper, wraps)
try:
    from typesafe import Typesafe, Typesafe_mf
except ImportError:
    Typesafe = lambda f: f

import functools
import typing
from copy import deepcopy

def _namedtuple(name, *fields):
    class Object(object):
        _fields = []
        def __init__(self, **kwargs):
            assert(sorted(kwargs.keys()) == sorted(self._fields))
            for k, v in kwargs.items():
                setattr(self, k, v)

        def __eq__(self, other):
            return self._name == other._name and all(getattr(self, field) == getattr(other, field) for field in self._fields)

        def __instancecheck__(cls, obj):
            return cls._fields == obj._fields and cls._name == obj._name

        def __subclasscheck__(cls, subclass):
            return cls._fields == subclass._fields and cls._name == subclass._name

        def __repr__(self):
            return '<Namedtuple {}>'.format(self._name)

        def __str__(self):
            ffields = ['{}={}'.format(field, getattr(self, field)) for field in self._fields]
            return '<Namedtuple {} {}>'.format(self._name, ', '.join(ffields))


    Object._name = name
    Object._fields = fields

    for f in fields:
        setattr(Object, f, None)

    return Object

_suite_result = _namedtuple('suite_result', 'passed', 'total', 'fails')
_test_case_data = _namedtuple('test_case_data', 'case_name', 'case_details', 'case_fn')
_test_case_fail_result = _namedtuple('test_case_fail_result', 'case_name', 'fail_reason')

TestResult = _namedtuple('TestResult', 'passed', 'fail_reason')
Fail = lambda reason: TestResult(passed=False, fail_reason=reason)
Success = lambda: TestResult(passed=True, fail_reason=None)

@Typesafe
def _print_suite_result(result: _suite_result):
    print('')
    for fail_msg in result.fails:
        print(fail_msg)
    print('\n{}/{} tests passed'.format(result.passed, result.total))


class TestSuite(object):
    def __init__(self, suite_name):
        self.suite_name = suite_name
        self.test_cases = []

    def _register(self, fn):
        self.test_cases.append(fn)

    def run_tests(self):
        tc_passed = 0
        tc_total = len(self.test_cases)

        fails = []

        print('\nRunning test suite {}'.format(self.suite_name))
        for tc in self.test_cases:
            print('  running {}...'.format(tc.case_name), end='')
            try:
                result = tc.case_fn()
                if result is None or result.passed:
                    tc_passed += 1
                    print(' ok')
                else:
                    fails.append(_test_case_fail_result(case_name = tc.case_name, fail_reason = result.fail_reason))
                    print(' fail')
            except Exception as e:
                fails.append(_test_case_fail_result(case_name = tc.case_name, fail_reason = 'exception thrown: {}'.format(e)))
                print(' fail')

        result = _suite_result(
           passed = tc_passed,
           total = tc_total,
           fails = ['{}.{} failed: {}'.format(self.suite_name, fail.case_name, fail.fail_reason) for fail in fails])
        _print_suite_result(result)
        return result


class TestCase(object):
    def __init__(self, suite: TestSuite, case_details: str):
        self.suite = suite
        self.case_details = case_details
        self.case_name = ''

    def __call__(self, fn: typing.Callable[[], TestResult]) -> typing.Callable[[], TestResult]:
        self.case_name = fn.__name__
        self.suite._register(_test_case_data(case_name = self.case_name, case_details = self.case_details, case_fn = fn))
        return fn


def assert_equal(lhs, rhs):
    if lhs != rhs:
        raise AssertionError('"{}" is not equal to "{}"'.format(lhs, rhs))
    return True

def assert_throws(fn, expected_exception):
    try:
        fn()
        raise AssertionError('function did not raise an exception')
    except Exception as e:
        if not isinstance(e, type(expected_exception)):
            raise AssertionError('exception "{}" is not an instance of "{}"'.format(e, type(expected_exception)))
        if str(expected_exception) and not str(e) == str(expected_exception):
            raise AssertionError('exception message "{}" does not match expected "{}"'.format(str(e), str(expected_exception)))
    return True
