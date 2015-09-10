__author__ = 'erickaltman'

import sqlite3
import os

db_file_name = 'cte_local.db'
db_test_file_name = 'test_cte_local.db'



class DatabaseManager:
    db = None
    cur = None
    current_db_file = None

    EXTRACTED_TABLE = 'extracted_info'
    headers = {
        EXTRACTED_TABLE: ('id', 'title', 'source_uri', 'extracted_datetime', 'source_file_hash', 'metadata')
    }
    fields = {
        EXTRACTED_TABLE: [
            ('id',                  'integer primary key'),
            ('title',               'text'),
            ('source_uri',          'text'),
            ('extracted_datetime',  'text'),
            ('source_file_hash',    'text'),
            ('metadata',            'text')
            ]
    }

    @classmethod
    def connect_to_db(cls, test=False):
        if test:
            DatabaseManager.db = sqlite3.connect(db_test_file_name)
            DatabaseManager.current_db_file = db_test_file_name
        else:
            DatabaseManager.db = sqlite3.connect(db_file_name)
            DatabaseManager.current_db_file = db_file_name
        DatabaseManager.cur = DatabaseManager.db.cursor()

    #TODO: change this to use absolute path to specific db directory
    @classmethod
    def delete_db(cls):
        DatabaseManager.db.close()
        try:
            f = open(DatabaseManager.current_db_file)
        except IOError:
            return False
        os.remove(DatabaseManager.current_db_file)

    # Create tables 'fields' are 2-tuples of form (col_name, col_attributes)
    # like ('name', 'text') or ('id', 'integer primary key')
    @classmethod
    def create_table(cls, table_name, fields):
        query = 'create table {} ({})'.format(table_name, "".join(["{} {},".format(f, t) for f, t in fields])[:-2])
        return cls.run_query(query)

    @classmethod
    def create_extracted_data_table(cls):
        return cls.create_table(DatabaseManager.EXTRACTED_TABLE,
                                DatabaseManager.fields[DatabaseManager.EXTRACTED_TABLE])

    @classmethod
    def insert_into_table(cls, table_name, values):
        query = 'insert into {} values ({})'.format(table_name, "".join(['?,' for _ in values])[:-1])
        return cls.run_query(query, values)

    @classmethod
    def run_query(cls, query, parameters=(), many=False):
        exec_func = cls.db.executemany if many else cls.db.execute
        try:
            result = exec_func(query, parameters)
        except sqlite3.Error as e:
            print e.message
            return None
        # .commit() method is needed for changes to be saved, can create false positives in tests
        # if left out since current connection will return its changes, but other connections will not see them
        cls.db.commit()
        return result

    @classmethod
    def is_attr_in_db(cls, attr, value, table_name):
        return cls.run_query(r'select exists(select * from {} where {}=?)'.format(table_name, attr), (value,)).fetchall() != [(0,)]

    @classmethod
    def retrieve_attr_from_db(cls, attr, value, table_name):
        return cls.run_query(r'select * from {} where {}=?'.format(table_name, attr), (value,)).fetchall()

    @classmethod
    def check_for_table(cls, table_name):
        query = 'select count(*) from sqlite_master where type=? and name=?'    # wondering if this is always safe?
        return cls.run_query(query, parameters=('table', table_name)).fetchone()[0] == 1


