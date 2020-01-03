from testing import *
from typesafe import Typesafe

testTests = TestSuite('test_suite_test')

@Typesafe
@TestCase(testTests, 't1')
def tc1() -> TestResult:
    return Success()

@Typesafe
@TestCase(testTests, 't2')
def tc2() -> TestResult:
    return Fail('some reason')

@Typesafe
@TestCase(testTests, 't3')
def tc3() -> TestResult:
    raise RuntimeError('some other reason')

suite_result = testTests.run_tests()

assert(suite_result.passed == 1)
assert(suite_result.total == 3)

assert(suite_result.fails[0] == 'test_suite_test.tc2 failed: some reason')
assert(suite_result.fails[1] == 'test_suite_test.tc3 failed: exception thrown: some other reason')

assertion_ts = TestSuite('assertions_tests')

@TestCase(assertion_ts, 'check assert_equal')
def test_assert_equal():
    assert(all([
        assert_equal(4, 4),
        assert_equal('a', 'a'),
        assert_equal([], []),
        assert_equal(['a'], ['a']),
        assert_equal({}, {}),
        assert_equal({'a'}, {'a'}),
    ]))

    for a, r in ((4, '4'), (1, 2), ([], {}), (['a'], []), (['a'], ['b']), ({'a': 3}, {'a': 4})):
        try:
            assert_equal(a, r)
            assert(False)
        except Exception as e:
            pass

@TestCase(assertion_ts, 'check assert_throws')
def test_assert_throws():
    def raise_exception(e):
        raise e

    assert_throws(lambda: raise_exception(RuntimeError('some message')), RuntimeError('some message'))
    assert_throws(lambda: raise_exception(RuntimeError('some message')), RuntimeError())

    try:
        assert_throws(lambda: 0, RuntimeError)
        assert(False)
    except Exception as e:
        pass

assertion_ts.run_tests()
