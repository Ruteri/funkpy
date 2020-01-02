from functools import (update_wrapper, wraps)
from typesafe import typesafe, typesafe_mf

import functools
import typing
from copy import deepcopy

g_test_cases = []

def _namedtuple(name, *fields):
    class Object(object):
        _fields = []
        def __init__(self, **kwargs):
            assert(sorted(kwargs.keys()) == sorted(self._fields))
            for k, v in kwargs.items():
                setattr(self, k, v)

        def __eq__(self, other):
            return all(getattr(self, field) == getattr(other, field) for field in self._fields)

        def __instancecheck__(cls, obj):
            return cls._fields == obj._fields and cls._name == obj._name

        def __subclasscheck__(cls, subclass):
            return cls._fields == subclass._fields and cls._name == subclass._name

    Object._name = name
    Object._fields = fields

    for f in fields:
        setattr(Object, f, None)

    return Object
        
_suite_result = _namedtuple('suite_result', 'passed', 'total', 'fails')
_test_case_data = _namedtuple('test_case_data', 'case_name', 'case_fn')
_test_case_fail_result = _namedtuple('test_case_fail_result', 'case_name', 'fail_reason')

test_result = _namedtuple('test_result', 'passed', 'fail_reason')
Fail = lambda reason: test_result(passed=False, fail_reason=reason)
Success = lambda: test_result(passed=True, fail_reason=None)


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
            print('  running test case {}...'.format(tc.case_name), end='')
            try:
                result = tc.case_fn()
                if result.passed:
                    tc_passed += 1
                    print(' ok')
                else:
                    fails.append(_test_case_fail_result(case_name = tc.case_name, fail_reason = result.fail_reason))
                    print(' fail')
            except Exception as e:
                fails.append(_test_case_fail_result(case_name = tc.case_name, fail_reason = 'exception thrown: {}'.format(e)))
                print(' fail')

        return _suite_result(
           passed = tc_passed,
           total = tc_total,
           fails = ('{}.{} failed: {}'.format(self.suite_name, fail.case_name, fail.fail_reason) for fail in fails))


####*- wrapped function must return Fail(reason) or Success() *-####
class test_case(object):
    @typesafe_mf
    def __init__(self, suite: TestSuite, case_name: str):
        self.suite = suite
        self.case_name = case_name

    @typesafe_mf
    def __call__(self, fn: typing.Callable[[], test_result]) -> typing.Callable[[], test_result]:
        self.suite._register(_test_case_data(case_name = self.case_name, case_fn = fn))
        return fn


def run_suites(suites):
    results = [suite.run_tests() for suite in suites]
    grand_passed = sum(result.passed for result in results)
    grand_total = sum(result.total for result in results)

    print('')
    for result in results:
        for fail in result.fails:
            print(fail)

    print('\n{}/{} tests passed'.format(grand_passed, grand_total))


""" In-place sanity check and example usage """

testTests = TestSuite('test suite')

@typesafe
@test_case(testTests, 't1')
def tc1() -> test_result:
    return Success()

@typesafe
@test_case(testTests, 't2')
def tc2() -> test_result:
    return Fail('some reason')

@typesafe
@test_case(testTests, 't3')
def tc3() -> test_result:
    raise RuntimeError('some other reason')

run_suites([testTests])
