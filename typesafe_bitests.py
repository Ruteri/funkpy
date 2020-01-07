import unittest
import typing

from typesafe import (Typesafe, Typesafe_mf)

class TypesafeUnittests(unittest.TestCase):
    def test_single_argument_function(self):
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

        self.assertEqual(test_int(2), 2)
        self.assertEqual(test_str('a'), 'a')
        self.assertEqual(test_list([5, 'a']), [5, 'a'])
        self.assertEqual(test_dict({'a': 5, 'b': 'd'}), {'a': 5, 'b': 'd'})

        l = lambda: 0
        self.assertEqual(test_callable(l), l)

        with self.assertRaises(TypeError):
            test_int('a')

        with self.assertRaises(TypeError):
            test_str(55)

        with self.assertRaises(TypeError):
            test_list({})

        with self.assertRaises(TypeError):
            test_dict(lambda: 0)

        with self.assertRaises(TypeError):
            test_callable(5)

    def test_templated(self):
        @Typesafe
        def test_list_wargs(a: typing.List[int]): return a
        @Typesafe
        def test_dict_wargs(a: typing.Dict[str, int]): return a
        @Typesafe
        def test_callable_wargs(a: typing.Callable[[int], bool]): return a

        self.assertEqual(test_list_wargs([5, 6]), [5, 6])
        with self.assertRaises(TypeError):
            test_list_wargs([5, '6'])

        self.assertEqual(test_dict_wargs({'a': 5, 'b': 6}), {'a': 5, 'b': 6})

        with self.assertRaises(TypeError):
            test_dict_wargs({'a': 5, 'b': '6'})

        def callable_stub(arg: int) -> bool: pass
        self.assertEqual(test_callable_wargs(callable_stub), callable_stub)
        def callable_stub2(arg: str): pass
        with self.assertRaises(TypeError):
            test_callable_wargs(callable_stub2)

    def test_incorrect(self):
        @Typesafe
        def test_int(a: int): return a

        with self.assertRaises(TypeError):
            test_int([])
        with self.assertRaises(TypeError):
            test_int({})
        with self.assertRaises(TypeError):
            test_int(str(5))
        with self.assertRaises(TypeError):
            test_int(RuntimeError())

    def test_members(self):
        class C(object):
            @Typesafe_mf
            def mf(self, a: int) -> int: return a

        c = C()
        self.assertEqual(c.mf(5), 5)
        with self.assertRaises(TypeError):
            c.mf('a')

    def test_returns(self):
        @Typesafe
        def f(a) -> int: return a

        self.assertEqual(f(5), 5)
        with self.assertRaises(TypeError):
            f('a')

if __name__ == '__main__':
    unittest.main()
