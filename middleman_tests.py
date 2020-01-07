import unittest
import unittest.mock

from middleman import Middleman, Middleman_mf, Middleman_cl

class MiddlemanTests(unittest.TestCase):
    def test_no_hooks(self):
        @Middleman()
        def some_fn():
            return 5
        self.assertEqual(some_fn(), 5)

    def test_no_hooks_mf(self):
        class MTest(object):
            @Middleman_mf()
            def some_fn(self):
                return 5
        self.assertEqual(MTest().some_fn(), 5)

    def test_args(self):
        @Middleman()
        def some_fn(arg1, arg2=2):
            return arg1+arg2
        self.assertEqual(some_fn(3), 5)
        self.assertEqual(some_fn(2, 3), 5)
        self.assertEqual(some_fn(2, arg2=3), 5)
        self.assertEqual(some_fn(arg1=2, arg2=3), 5)
        self.assertEqual(some_fn(arg2=2, arg1=3), 5)

    def test_hooks(self):
        pre_mock = unittest.mock.MagicMock()
        post_mock = unittest.mock.MagicMock()

        @Middleman(pre_hook=pre_mock, post_hook=post_mock)
        def some_fn(arg1, arg2):
            return 5

        self.assertEqual(some_fn('a', arg2=3), 5)

        pre_mock.assert_called_once_with('a', arg2=3)
        post_mock.assert_called_once_with(5, 'a', arg2=3)

    def test_hooks_mf(self):
        pre_mock = unittest.mock.MagicMock()
        post_mock = unittest.mock.MagicMock()

        class MTest(object):
            @Middleman_mf(pre_hook=pre_mock, post_hook=post_mock)
            def some_fn(self, arg1, arg2):
                return 5

        tobj = MTest()

        self.assertEqual(tobj.some_fn('a', arg2=3), 5)

        pre_mock.assert_called_once_with(tobj, 'a', arg2=3)
        post_mock.assert_called_once_with(tobj, 5, 'a', arg2=3)

    def test_hooks_cl(self):
        pre_mock = unittest.mock.MagicMock()
        post_mock = unittest.mock.MagicMock()

        @Middleman_cl(pre_hook=pre_mock, post_hook=post_mock)
        class CTest(object):
            def some_fn(self, arg1, arg2):
                return 5

        tobj = CTest()

        self.assertEqual(tobj.some_fn('a', arg2=3), 5)

        pre_mock.assert_called_once_with(tobj._obj, 'some_fn', ('a',), arg2=3)
        post_mock.assert_called_once_with(tobj._obj, 'some_fn', 5, ('a',), arg2=3)
        
    def test_attributes_standalone(self):
        @Middleman()
        def some_fn(arg1, arg2):
            """somedocstring"""
            return 5

        self.assertEqual(some_fn.__name__, 'some_fn')
        self.assertEqual(some_fn.__doc__, 'somedocstring')

    def test_attributes_mf(self):
        class MTest(object):
            @Middleman_mf()
            def some_fn(self, arg1, arg2):
                """someotherdocstring_mf"""
                return 5

        mt = MTest()
        self.assertIn('MTest', str(mt.__class__()))
        self.assertEqual(mt.some_fn.__name__, 'some_fn')
        self.assertEqual(mt.some_fn.__doc__, 'someotherdocstring_mf')

    def test_attributes_cl(self):
        @Middleman_cl()
        class CTest(object):
            def some_fn(self, arg1, arg2):
                """someotherdocstring_ct"""
                return 5

        ct = CTest()
        self.assertIn('CTest', str(ct.__class__()))
        self.assertEqual(ct.some_fn.__name__, 'some_fn')
        self.assertEqual(ct.some_fn.__doc__, 'someotherdocstring_ct')

if __name__ == '__main__':
    unittest.main()
