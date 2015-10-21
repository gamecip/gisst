__author__ = 'erickaltman'

import unittest
from utils import clean_for_sqlite_query

class TestUtilMethods(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_clean_for_sqlite(self):
        t = ":,::,,:"
        self.assertEqual("", clean_for_sqlite_query(t))