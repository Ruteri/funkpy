import re

class OfType(object):
    """Type argument matcher"""
    def __init__(self, expected):
        self.expected = expected

    def __eq__(self, other):
        return type(other) == self.expected

class Like(object):
    """Regex argument matcher"""
    def __init__(self, expected):
        self.expected = re.compile(expected)

    def __eq__(self, other):
        return self.expected.match(other) is not None

class Expectation(object):
    """Class Expectation. Holds logic and data on how given function should behave.

    * Keeps track of the number of calls and checks it against expectation (once, never)
    * Wraps functions to allow returning different mocked values for different arguments (on)
    * Allows exception injection on function call with certain arguments

    Should always be used within Mock.

    Args:
        fn: function to be mocked, for arguments deduction
        method_name: self-explanatory, used for debug prints
    """
    def __init__(self, fn=None, method_name=''):
        self.fn = fn
        self.arg_map = None
        if self.fn is not None:
            self.arg_map = list(self.fn.__code__.co_varnames)

        self.expects_once = False
        self.expects_never = False
        self.n_calls = 0
        self.to_raise = None
        self.rv = None
        self.method_name = method_name
        self.call_expectations = []

    def restore(self):
        self.__init__(self, self.fn, self.method_name)

    def _on_call_checks(self):
        self.n_calls += 1
        if self.expects_never:
            raise AssertionError('{} was called but expected never'.format(self.method_name))

        if self.expects_once and self.n_calls > 1:
            raise AssertionError('{} was called more than once but expected once'.format(self.method_name))

    def _merge_kwargs(self, *args, **kwargs):
        if self.fn is None or self.arg_map is None:
            raise AssertionError('cannot merge kwargs without function definition')

        all_args_kw = kwargs
        for index, arg in enumerate(args):
            varname = self.arg_map[index]
            all_args_kw[varname] = arg
        return all_args_kw

    def _kwargs_match(self, expected, actual):
        # Strict matches (None != absent)
        if sorted(expected.keys()) != sorted(actual.keys()):
            return False

        if expected == actual:
            return True

        for k, v in expected.items():
            av = actual[k]
            if v == av: continue
            return False
            
        return True

    def _on_call_dispatch(self, *args, **kwargs):
        if self.fn is not None:
            merged_args = self._merge_kwargs(*args, **kwargs)
            for expected_call in self.call_expectations:
                # TODO: If call matches expected
                if self._kwargs_match(merged_args, expected_call[0]):
                    return expected_call[-1](*args, **kwargs)
        
        if self.to_raise is not None:
            raise self.to_raise

        return self.rv

    def __call__(self, *args, **kwargs):
        self._on_call_checks()
        return self._on_call_dispatch(*args, **kwargs)

    def on(self, *args, **kwargs):
        call_matcher = self._merge_kwargs(*args, **kwargs)
        self.call_expectations.append((call_matcher, Expectation(fn=self.fn, method_name=self.method_name)))
        return self.call_expectations[-1][-1]

    def once(self):
        self.expects_once = True
        return self

    def never(self):
        self.expects_never = True
        return self

    def returns(self, rv):
        self.rv = rv
        return self

    def raises(self, ex):
        self.to_raise = ex
        return self

    def verify(self):
        if self.expects_never and self.n_calls > 0:
            raise AssertionError('method {} was called but expected never'.format(self.method_name))
        if self.expects_once and self.n_calls < 1:
            raise AssertionError('method {} not called but expected once'.format(self.method_name))
        if self.expects_once and self.n_calls > 1:
            raise AssertionError('method {} called {} times but expected once'.format(self.method_name, self.n_calls))
        return True

    
class Mock(Expectation):
    """Mock class. Manages Expectations as member functions.

    Basic usage:
    m = Mock()
    m.never()
    mf = m.expects('memberfnname', lambda arg1, arg2: None)
    mf.on(5).returns(10)
    mf.on('a', 5).raises(RuntimeError('exception message'))
    mf.once()
    m.expects('othermember').never()
    m.verify()


    Args:
        fn: function to be mocked, for arguments deduction
        method_name: self-explanatory, used for debug prints
    """

    def __init__(self, fn=None, method_name=''):
        Expectation.__init__(self, fn=fn, method_name=method_name)
        self.expected_members = []

    def restore(self):
        for method_name in self.expected_members:
            delattr(self, method_name)
        Expectation.restore(self)

    def expects(self, method_name='', fn=None):
        self.expected_members.append(method_name)
        setattr(self, method_name, Expectation(fn=fn, method_name=method_name))
        return getattr(self, method_name)
        
    def verify(self):
        for mf in self.expected_members:
            getattr(self, mf).verify()
        return Expectation.verify(self)

import unittest

class MockHelpersTests(unittest.TestCase):
    def test_kwargs_merger(self):
        def f(targ1='', targ2=''): pass
        m = Mock(fn=f)
        self.assertEqual(m._merge_kwargs(targ1=1, targ2=2), {'targ1': 1, 'targ2': 2})
        self.assertEqual(m._merge_kwargs(1, targ2=2), {'targ1': 1, 'targ2': 2})
        self.assertEqual(m._merge_kwargs(1, 2), {'targ1': 1, 'targ2': 2})
        self.assertEqual(m._merge_kwargs(targ1=1), {'targ1': 1})
        self.assertEqual(m._merge_kwargs(targ2=2), {'targ2': 2})
        self.assertEqual(m._merge_kwargs(1), {'targ1': 1})

    def test_args_matcher(self):
        def f(targ1, targ2): pass
        m = Mock(fn=f)

        on_arg1 = m.on(5)
        matcher = m.call_expectations[-1][0]
        self.assertEqual(m._kwargs_match(matcher, m._merge_kwargs(5)), True)
        self.assertEqual(m._kwargs_match(matcher, m._merge_kwargs(targ1=5)), True)
        self.assertEqual(m._kwargs_match(matcher, m._merge_kwargs(6)), False)
        self.assertEqual(m._kwargs_match(matcher, m._merge_kwargs(targ1=6)), False)
        self.assertEqual(m._kwargs_match(matcher, m._merge_kwargs(5, None)), False)
        self.assertEqual(m._kwargs_match(matcher, m._merge_kwargs(5, targ2=None)), False)
        self.assertEqual(m._kwargs_match(matcher, m._merge_kwargs(targ1=5, targ2=None)), False)

class MockTests(unittest.TestCase):
    def test_no_fn(self):
        m = Mock()
        m.returns(5)
        self.assertEqual(m(5), 5)
        self.assertEqual(m('a'), 5)

        with self.assertRaises(AssertionError):
            m.on(5)
        self.assertEqual(m.verify(), True)

    def test_on_call_mixargs(self):
        def f(targ1='', targ2=''): pass
        m = Mock(fn=f)
        m.on(5).returns(9)
        m.on(targ1=5).returns(10)
        m.on(6).returns(11)
        m.on(6, targ2=7).returns(12)
        m.on(targ2=7).returns(13)

        self.assertEqual(m(5), 9)
        self.assertEqual(m(targ1=5), 9)
        self.assertEqual(m(6), 11)
        self.assertEqual(m(targ1=6), 11)
        self.assertEqual(m(6, 7), 12)
        self.assertEqual(m(6, targ2=7), 12)
        self.assertEqual(m(targ2=7), 13)
        self.assertEqual(m(None, 7), None)
        self.assertEqual(m.verify(), True)

    def test_matchers(self):
        def f(arg): pass
        m = Mock(fn=f)

        m.on(arg=Like('a')).returns(1)
        m.on(arg=OfType(str)).returns(2)

        self.assertEqual(m('a'), 1)
        self.assertEqual(m('b'), 2)
        self.assertEqual(m.verify(), True)

    def test_on_call_kwargs(self):
        def f(targ): pass
        m = Mock(fn=f)
        m.on(targ=5).returns(10)
        m.on(targ=6).returns(11)

        self.assertEqual(m(targ=5), 10)
        self.assertEqual(m(targ=6), 11)
        self.assertEqual(m.verify(), True)

    def test_expects(self):
        def f(targ1='', targ2=''): pass
        m = Mock(fn=f)
        tfn = m.expects('testfn', f)
        tfn.on(5).returns(9)
        self.assertEqual(m.testfn(5), 9)
        self.assertEqual(m.verify(), True)

    def test_once(self):
        def f(): pass
        m = Mock(f)
        m.once()
        with self.assertRaises(AssertionError):
            m.verify()

        m()

        self.assertEqual(m.verify(), True)

        with self.assertRaises(AssertionError):
            m()

        with self.assertRaises(AssertionError):
            m.verify()

    def test_never(self):
        def f(): pass
        m = Mock(f)
        m.never()

        self.assertEqual(m.verify(), True)

        with self.assertRaises(AssertionError):
            m()

        with self.assertRaises(AssertionError):
            m.verify()

    def test_verify(self):
        m = Mock()
        mf = m.expects('memfn')
        mf.never()

        self.assertEqual(m.verify(), True)
        self.assertEqual(mf.verify(), True)

        with self.assertRaises(AssertionError):
            m.memfn()

        with self.assertRaises(AssertionError):
            mf.verify()

        with self.assertRaises(AssertionError):
            m.verify()

class MockBasicUsageTests(unittest.TestCase):
    def test_basic_usage(self):
        db_mock = Mock()
        sql_exec_fn = db_mock.expects('exec_sql', lambda s: None)
        sql_exec_fn.on(Like('select \* from table where id=5')).returns('some columns')
        sql_exec_fn.on(Like('select \* from table where id=6')).raises(ValueError('some message'))
        sql_exec_fn.on(Like('select \* from table where id=[0-9]')).returns('some more columns')

        self.assertEquals(db_mock.exec_sql('select * from table where id=5'), 'some columns')
        self.assertEquals(db_mock.exec_sql('select * from table where id=1'), 'some more columns')
        self.assertEquals(db_mock.exec_sql('select * from table where id=7'), 'some more columns')

        with self.assertRaises(ValueError):
            db_mock.exec_sql('select * from table where id=6')

if __name__ == '__main__':
    unittest.main()
