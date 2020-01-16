import re

class OfType(object):
    """Type argument matcher."""
    def __init__(self, expected):
        self.expected = expected

    def __eq__(self, other):
        return type(other) == self.expected


class Like(object):
    """Regex argument matcher."""
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
    Basic usage:
        m = Mock()
        mf = m.expects('memberfnname', lambda arg1, arg2: None)
        mf.on(5).returns(10)
        mf.on('a', 5).raises(RuntimeError('exception message'))
        mf.once()
        m.verify()

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

    def _on_call_checks(self):
        self.n_calls += 1
        if self.expects_never:
            raise AssertionError('{} was called but expected never'.format(self.method_name))

        if self.expects_once and self.n_calls > 1:
            raise AssertionError('{} was called more than once but expected once'.format(self.method_name))

    def _merge_kwargs(self, *args, **kwargs):
        if self.fn is None or self.arg_map is None:
            if kwargs:
                raise AssertionError('cannot merge kwargs without function definition')
            return args

        all_args_kw = kwargs
        for index, arg in enumerate(args):
            varname = self.arg_map[index]
            all_args_kw[varname] = arg
        return all_args_kw

    def _args_match(self, expected, actual):
        # Strict matches (None != absent)
        if expected == actual:
            return True

        if type(expected) != type(actual):
            # Mismatch due to lack of function definition
            return False

        if isinstance(expected, dict):
            if sorted(expected.keys()) != sorted(actual.keys()): return False
            for k, v in expected.items():
                av = actual[k]
                if v == av: continue
                return False
            return True

        if isinstance(expected, list):
            if len(expected) != len(actual): return False
            for i, v in enumerate(expected):
                av = actual[i]
                if v == av: continue
                return False
            return True
        return False

    def _on_call_dispatch(self, *args, **kwargs):
        merged_args = self._merge_kwargs(*args, **kwargs)
        for expected_call in self.call_expectations:
            if self._args_match(merged_args, expected_call[0]):
                return expected_call[-1](*args, **kwargs)
        
        if self.to_raise is not None:
            raise self.to_raise

        return self.rv

    def __call__(self, *args, **kwargs):
        self._on_call_checks()
        return self._on_call_dispatch(*args, **kwargs)

    def restore(self):
        """Reset all expectations."""
        self.__init__(self, self.fn, self.method_name)

    def on(self, *args, **kwargs):
        """Specify action when arguments match.

        Only possible to specify for a known function signature (passed in constructor).
        Matches arguments in order of calls (first .on will have the highest priority).
        
        Arguments:
            positional and keyword arguments that rule should match
            equality check will be used to match the argument (__eq__)

        Usage:
            mf.on(5) # will match 
            mf.on(somekwarg='string')
            mf.on(7, mixedargs=10)
            mf.on(somearg=Like('a[0-9]'))
            mf.on(otherarg=OfType(str))

        Returns expectation.
        """
        call_matcher = self._merge_kwargs(*args, **kwargs)
        self.call_expectations.append((call_matcher, Expectation(fn=self.fn, method_name=self.method_name)))
        return self.call_expectations[-1][-1]

    def once(self):
        """Throws assertion error if called more than once."""
        self.expects_once = True
        return self

    def never(self):
        """Verification fails with assertion error if never called."""
        self.expects_never = True
        return self

    def returns(self, rv):
        """Makes given expectation return rv."""
        self.rv = rv
        return self

    def raises(self, ex):
        """Makes given expectation raise ex.

        Arguments:
            ex: error object

        Usage:
            mf.raises(ValueError(5))
        """
        self.to_raise = ex
        return self

    def verify(self):
        """Verifies expectation.

        Checks whether expectation was called correct number of times.
        """
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
        mf = m.expects('memberfnname', lambda arg1, arg2: None)
        m.expects('othermember').never()
        m.verify()

    Args:
        fn: function to be mocked, for arguments deduction
        method_name: self-explanatory, used for debug prints
    """

    def __init__(self, fn=None, method_name=''):
        Expectation.__init__(self, fn=fn, method_name=method_name)
        self.member_mocks = []

    def restore(self):
        """Resets all member expectations."""
        for method_name in self.member_mocks:
            delattr(self, method_name)
        Expectation.restore(self)

    def expects(self, method_name='', fn=None):
        """Creates new member mock and returns it."""
        self.member_mocks.append(method_name)
        setattr(self, method_name, Mock(fn=fn, method_name=method_name))
        return getattr(self, method_name)
        
    def verify(self):
        """Verifies all member mocks."""
        for mf in self.member_mocks:
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
        self.assertEqual(m._args_match(matcher, m._merge_kwargs(5)), True)
        self.assertEqual(m._args_match(matcher, m._merge_kwargs(targ1=5)), True)
        self.assertEqual(m._args_match(matcher, m._merge_kwargs(6)), False)
        self.assertEqual(m._args_match(matcher, m._merge_kwargs(targ1=6)), False)
        self.assertEqual(m._args_match(matcher, m._merge_kwargs(5, None)), False)
        self.assertEqual(m._args_match(matcher, m._merge_kwargs(5, targ2=None)), False)
        self.assertEqual(m._args_match(matcher, m._merge_kwargs(targ1=5, targ2=None)), False)

class MockTests(unittest.TestCase):
    def test_no_fn(self):
        m = Mock()
        m.returns(5)
        self.assertEqual(m(5), 5)
        self.assertEqual(m('a'), 5)

        with self.assertRaises(AssertionError):
            m.on(a=5)

        with self.assertRaises(AssertionError):
            m(a=5)

        self.assertEqual(m.verify(), True)

    def test_no_fn_on_positional(self):
        m = Mock()
        m.on(5, 6).returns(5)
        m.on('a', 6).returns(6)
        self.assertEqual(m(5), None)
        self.assertEqual(m(6), None)
        self.assertEqual(m(5, 6), 5)
        self.assertEqual(m('a', 6), 6)

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
        sql_exec_fn = db_mock.expects('exec_sql')
        sql_exec_fn.on(Like('select \* from table where id=5')).returns('some columns')
        sql_exec_fn.on(Like('select \* from table where id=6')).raises(ValueError('some message'))
        sql_exec_fn.on(Like('select \* from table where id=[0-9]')).returns('some more columns')

        self.assertEqual(db_mock.exec_sql('select * from table where id=5'), 'some columns')
        self.assertEqual(db_mock.exec_sql('select * from table where id=1'), 'some more columns')
        self.assertEqual(db_mock.exec_sql('select * from table where id=7'), 'some more columns')

        with self.assertRaises(ValueError):
            db_mock.exec_sql('select * from table where id=6')

if __name__ == '__main__':
    unittest.main()
