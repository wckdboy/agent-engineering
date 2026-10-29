import unittest

from calc import clamp


class ClampTest(unittest.TestCase):
    def test_inside(self):
        self.assertEqual(clamp(2, 0, 3), 2)

    def test_below(self):
        self.assertEqual(clamp(-1, 0, 3), 0)

    def test_above(self):
        self.assertEqual(clamp(5, 0, 3), 3)
