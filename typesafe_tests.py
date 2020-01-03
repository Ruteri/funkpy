from testing import *
from typesafe import (Typesafe, Typesafe_mf)

ts = TestSuite('typesafe_unittests')

@TestCase(ts, 'sanity check with single argument functions')
def test_single_argument_functions():
    @Typesafe
    def test_int(a: int): return a
    @Typesafe
    def test_str(a: str): return a
    @Typesafe
    def test_list(a: typing.List): return a
    @Typesafe
    def test_dict(a: typing.Dict): return a
    @Typesafe
    def test_callable(a: typing.Callable): return a

    assert_equal(test_int(2), 2)
    assert_equal(test_str('a'), 'a')
    assert_equal(test_list([5, 'a']), [5, 'a'])
    assert_equal(test_dict({'a': 5, 'b': 'd'}), {'a': 5, 'b': 'd'})

    l = lambda: 0
    assert_equal(test_callable(l), l)

    assert_throws(lambda: test_int('a'), TypeError())
    assert_throws(lambda: test_str(55), TypeError())
    assert_throws(lambda: test_list({}), TypeError())
    assert_throws(lambda: test_dict(lambda: 0), TypeError())
    assert_throws(lambda: test_callable(5), TypeError())

@TestCase(ts, 'check if templated types handled properly')
def test_templated():
    @Typesafe
    def test_list_wargs(a: typing.List[int]): return a
    @Typesafe
    def test_dict_wargs(a: typing.Dict[str, int]): return a
    @Typesafe
    def test_callable_wargs(a: typing.Callable[[int], bool]): return a

    assert_equal(test_list_wargs([5, 6]), [5, 6])
    assert_throws(lambda: test_list_wargs([5, '6']), TypeError())
    assert_equal(test_dict_wargs({'a': 5, 'b': 6}), {'a': 5, 'b': 6})
    assert_throws(lambda: test_dict_wargs({'a': 5, 'b': '6'}), TypeError())

    def callable_stub(arg: int) -> bool: pass
    assert_equal(test_callable_wargs(callable_stub), callable_stub)
    def callable_stub2(arg: str): pass
    assert_throws(lambda: test_callable_wargs(callable_stub2), TypeError())

@TestCase(ts, 'check passing incorrect types raises exception')
def test_incorrect():
    @Typesafe
    def test_int(a: int): return a

    assert_throws(lambda: test_int([]), TypeError())
    assert_throws(lambda: test_int({}), TypeError())
    assert_throws(lambda: test_int(str(5)), TypeError())
    assert_throws(lambda: test_int(RuntimeError()), TypeError())

@TestCase(ts, 'check typesafe member functions')
def test_members():
    class C(object):
        @Typesafe_mf
        def mf(self, a: int) -> int: return a

    c = C()
    assert_equal(c.mf(5), 5)
    assert_throws(lambda: c.mf('a'), TypeError())

@TestCase(ts, 'check return type safety')
def test_returns():
    @Typesafe
    def f(a) -> int: return a

    assert_equal(f(5), 5)
    assert_throws(lambda: f('a'), TypeError())

ts.run_tests()
