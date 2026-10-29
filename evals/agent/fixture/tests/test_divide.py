import unittest

from calc import divide


class DivideTest(unittest.TestCase):
    def test_normal(self):
        self.assertEqual(divide(6, 3), 2)

    def test_zero_divisor_is_an_error(self):
        with self.assertRaises(ZeroDivisionError):
            divide(1, 0)
