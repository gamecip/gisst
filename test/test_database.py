__author__ = 'erickaltman'

import unittest

from database import DatabaseManager


class TestDatabaseMethods(unittest.TestCase):

    def setUp(self):
        self.dbm = DatabaseManager
        self.fields = [('id', 'integer primary key'),
                  ('name', 'text'),
                  ('date', 'text'),
                  ('other_value', 'real')]
        self.table_name = 'test_table'
        self.insert_tuple = (None, u'bob', u'2005-10-10', 4.5)
        self.dbm.connect_to_db(test=True)
        self.assertTrue(self.dbm.create_table(self.table_name, self.fields))

    def test_db_loop(self):
        self.assertTrue(self.dbm.insert_into_table(self.table_name, self.insert_tuple))
        self.assertEquals(self.dbm.retrieve_attr_from_db('name', 'bob', 'test_table'),
                          [(1, u'bob', u'2005-10-10', 4.5)])

    def test_is_attr_in_db(self):
        self.assertTrue(self.dbm.insert_into_table(self.table_name, self.insert_tuple))
        self.assertTrue(self.dbm.is_attr_in_db('name', 'bob', self.table_name))
        self.assertFalse(self.dbm.is_attr_in_db('name', 'ted', self.table_name))

    def test_run_query(self):
        other_data = [(1, u'fred', u'2006-1-1', 5.6),
                      (2, u'jill', u'2013-4-5', 5.6)]
        self.assertTrue(self.dbm.run_query(r'insert into {} (id, name, date, other_value) values (?,?,?,?)'.format(self.table_name),
                                           other_data,
                                           many=True))
        self.assertEqual(other_data, self.dbm.retrieve_attr_from_db('other_value', 5.6, self.table_name))

    def test_check_for_table(self):
        self.assertTrue(self.dbm.check_for_table(self.table_name))
        self.assertFalse(self.dbm.check_for_table('not_a_table'))

    def tearDown(self):
        self.dbm.db.close()
        self.dbm.delete_db()
