__author__ = 'erickaltman'

import unittest

from database import DatabaseManager, field_constraint, foreign_key


class TestDatabaseMethods(unittest.TestCase):

    def setUp(self):
        self.dbm = DatabaseManager
        self.fields = [('id', 'integer primary key', field_constraint),
                  ('name', 'text', field_constraint),
                  ('date', 'text', field_constraint),
                  ('other_value', 'real', field_constraint)]
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

    def test_foreign_key(self):
        foreign_fields = [('id', 'integer primary key', field_constraint),
                          ('name', 'text', field_constraint),
                          ('test_field', 'integer', foreign_key(self.table_name, 'id'))]
        foreign_table = 'f_table'
        self.assertTrue(self.dbm.create_table(foreign_table, foreign_fields))
        self.assertTrue(self.dbm.insert_into_table(self.table_name, self.insert_tuple))
        self.assertTrue(self.dbm.insert_into_table(foreign_table, (None, u'other_bob', 1)))
        self.assertFalse(self.dbm.insert_into_table(foreign_table, (None, u'third_bob', 5)))
        self.assertFalse(self.dbm.is_attr_in_db('name', u'third_bob', foreign_table))
        self.assertTrue(self.dbm.is_attr_in_db('name', u'other_bob', foreign_table))

    def tearDown(self):
        self.dbm.db.close()
        self.dbm.delete_db()
