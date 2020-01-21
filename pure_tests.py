import unittest

from pure import pure, pure_mf

class PureTests(unittest.TestCase):
    def test_builtin_accesses(self):
        class TO(object):
            i = 5
            f = 0.4
            st = 'xxx'
            l = ['x', 4, 0.6]
            s = set('x')

        @pure
        def access_fn(tobj):
            self.assertEqual(tobj.i, 5)
            self.assertEqual(tobj.f, 0.4)
            self.assertEqual(tobj.st, 'xxx')
            self.assertEqual(tobj.l, ['x', 4, 0.6])
            self.assertEqual(tobj.s, set('x'))

            self.assertEqual(tobj.i + 10, 15)
            self.assertEqual(tobj.f + 10 - 15.4 < 10e-5, True)

            ind = 0
            for c in tobj.st:
                ind += 1
                self.assertEqual(c, 'x')
            self.assertEqual(ind, 3)
            self.assertEqual(len(tobj.l), 3)
            self.assertEqual(tobj.st.count('x'), 3)
            self.assertEqual('x' in tobj.st, True)

            self.assertEqual('x' in tobj.l, True)
            self.assertEqual(4 in tobj.l, True)
            self.assertEqual(5 not in tobj.l, True)

            self.assertEqual('x' in tobj.s, True)
            self.assertEqual('x' not in tobj.s, False)

        access_fn(TO())


    def test_builtin_perm(self):

        class TO(object):
            i = 5
            l = []

        @pure
        def perm(obj):
            with self.assertRaises(AttributeError):
                obj.i = 10

            with self.assertRaises(AttributeError):
                obj.i += 10

            with self.assertRaises(AttributeError):
                obj.i -= 10

            with self.assertRaises(AttributeError):
                obj.append(0)

            with self.assertRaises(AttributeError):
                obj.l += [0]

        perm(TO())

    def test_nested_objects(self):
        class T1(object):
            d = 5

        class T2(object):
            t1 = T1()

        @pure
        def access_nested(obj):
            self.assertEqual(obj.t1.d, 5)

        @pure
        def perm_nested(obj):
            with self.assertRaises(AttributeError):
                obj.t1 = T1()

            with self.assertRaises(AttributeError):
                obj.t1.d = 5

        access_nested(T2())
        perm_nested(T2())

    def test_member_function(self):
        testobj = self

        class TO:
            d = 5

        to = TO()

        class ConstMembers(object):
            @pure_mf
            def perm_self(self):
                with testobj.assertRaises(AttributeError):
                    self.x = 10

            @pure_mf
            def access_fn(self, obj):
                testobj.assertEqual(obj.d, 5)

            @pure_mf
            def perm_fn(self, obj):
                with testobj.assertRaises(AttributeError):
                    obj.d = 10

        cm = ConstMembers()
        cm.access_fn(to)
        cm.perm_fn(to)
        cm.perm_self()


if __name__ == '__main__':
    unittest.main()
