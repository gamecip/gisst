__author__ = 'erickaltman'

from pysqlite2 import dbapi2 as sqlite3
import os
import json
import pytz
import click
from datetime import datetime
from functools import partial
from schema import (
    GAME_CITE_REF,
    PERF_CITE_REF,
    generate_cite_ref
)
from utils import bound_array

db_file_name = 'cte_local.db'
db_test_file_name = 'test_cte_local.db'

local_data_store = 'data'


#   Database utility functions, might move somewhere else if there are too many
def foreign_key(foreign_table_name, key_name):
    def foreign_key_partial(field, constraints, ftn, key):
        DatabaseManager._constraints.append('foreign key({}) references {}({})'.format(field, ftn, key))
        return "{} {}".format(field, constraints)
    return partial(foreign_key_partial, ftn=foreign_table_name, key=key_name)


def field_constraint(field, constraint):
    return "{} {}".format(field, constraint)

def no_constraint(field, constraint):
    return "{}".format(field)

class DatabaseManager:
    db = None
    cur = None
    current_db_file = None

    EXTRACTED_TABLE = 'extracted_info'
    GAME_CITATION_TABLE = 'game_citation'
    PERFORMANCE_CITATION_TABLE = 'performance_citation'
    FTS_INDEX_TABLE = 'fts_index_table'
    FTS_EXT_PATH = './fts5.dylib'

    #   Relations
    AND = ' and '
    OR = ' or '

    _constraints = []

    fields = {
        FTS_INDEX_TABLE: [
            ('uuid',                '',                 no_constraint),
            ('source_hash',         '',                 no_constraint),
            ('source_type',         '',                 no_constraint),
            ('content',             '',                 no_constraint)
        ],
        EXTRACTED_TABLE: [
            ('id',                  'integer primary key',  field_constraint),
            ('title',               'text',                 field_constraint),
            ('source_uri',          'text',                 field_constraint),
            ('extracted_datetime',  'text',                 field_constraint),
            ('source_file_hash',    'text',                 field_constraint),
            ('metadata',            'text',                 field_constraint)
            ],
        GAME_CITATION_TABLE: [
            ('id',                  'integer primary key',  field_constraint),
            ('title',               'text',                 field_constraint),
            ('uuid',                'text',                 field_constraint),
            ('platform',            'text',                 field_constraint),
            ('developer',           'text',                 field_constraint),
            ('publisher',           'text',                 field_constraint),
            ('distributor',         'text',                 field_constraint),
            ('copyright_year',      'datetime',             field_constraint),
            ('date_published',      'datetime',             field_constraint),
            ('localization_region', 'text',                 field_constraint),
            ('version',             'text',                 field_constraint),
            ('data_image_checksum', 'text',                 field_constraint),
            ('data_image_source',   'text',                 field_constraint),
            ('notes',               'text',                 field_constraint),
            ('source_url',          'text',                 field_constraint),
            ('source_data',         'text',                 field_constraint),
            ('schema_version',      'text',                 field_constraint),
            ('created',             'datetime',             field_constraint),
            ('cite_object',         'text',                 field_constraint)
        ],
        PERFORMANCE_CITATION_TABLE: [
            ('id',                                  'integer primary key',  field_constraint),
            ('title',                               'text',                 field_constraint),
            ('description',                         'text',                 field_constraint),
            ('uuid',                                'text',                 field_constraint),
            ('game_uuid',                           'text',                 field_constraint),
            ('inputs',                              'text',                 field_constraint),
            ('input_events',                        'text',                 field_constraint),
            ('data_events',                         'text',                 field_constraint),
            ('replay_source_purl',                  'text',                 field_constraint),
            ('replay_source_file_ref',              'text',                 field_constraint),
            ('replay_source_file_name',             'text',                 field_constraint),
            ('recording_agent',                     'text',                 field_constraint),
            ('save_state_source_purl',              'text',                 field_constraint),
            ('save_state_source_file_ref',          'text',                 field_constraint),
            ('save_state_terminal_purl',            'text',                 field_constraint),
            ('save_state_terminal_file_ref',        'text',                 field_constraint),
            ('emulator_name',                       'text',                 field_constraint),
            ('emulator_version',                    'text',                 field_constraint),
            ('emulator_operating_system',           'text',                 field_constraint),
            ('emulator_system_dependent_images',    'text',                 field_constraint),
            ('emulator_system_configuration',       'text',                 field_constraint),
            ('performer',                           'text',                 field_constraint),
            ('previous_performance_uuid',           'text',                 field_constraint),
            ('start_datetime',                      'datetime',             field_constraint),
            ('location',                            'text',                 field_constraint),
            ('notes',                               'text',                 field_constraint),
            ('additional_info',                     'text',                 field_constraint),
            ('schema_version',                      'text',                 field_constraint),
            ('created',                             'datetime',             field_constraint),
            ('cite_object',                         'text',                 field_constraint)
        ]
    }

    headers = {
        EXTRACTED_TABLE: ('id', 'title', 'source_uri', 'extracted_datetime', 'source_file_hash', 'metadata'),
        FTS_INDEX_TABLE: ('uuid', 'source_hash', 'source_type', 'content'),
        GAME_CITATION_TABLE: [x for x, _, _ in fields[GAME_CITATION_TABLE]],
        PERFORMANCE_CITATION_TABLE: [x for x, _, _ in fields[PERFORMANCE_CITATION_TABLE]]
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
        # SQLite requires setting foreign key constraint flag on EVERY connection
        DatabaseManager.run_query('PRAGMA foreign_keys = ON')
        # SQLite load the fts5 extension to allow for full text search queries
        DatabaseManager.db.enable_load_extension(True)
        DatabaseManager.db.load_extension("{}".format(DatabaseManager.FTS_EXT_PATH))

    #   TODO: change this to use absolute path to specific db directory
    @classmethod
    def delete_db(cls):
        DatabaseManager.db.close()
        try:
            open(DatabaseManager.current_db_file)
        except IOError:
            return False
        else:
            os.remove(DatabaseManager.current_db_file)

    # Create tables 'fields' are 3-tuples of form (col_name, col_attributes, col_function)
    # like ('name', 'text') or ('id', 'integer primary key') or ('game_id', 'text', foreign_key(Table, attribute))
    @classmethod
    def create_table(cls, table_name, fields):
        query = 'create table {} ({}'.format(table_name, ",".join(["{}".format(z(f, t)) for f, t, z in fields]))
        if cls._constraints:
            query += "," + ",".join([constraint for constraint in cls._constraints]) + ")"
            cls._constraints = []
        else:
            query += ")"
        return cls.run_query(query)

    @classmethod
    def create_tables(cls):
        for table in (cls.EXTRACTED_TABLE, cls.GAME_CITATION_TABLE, cls.PERFORMANCE_CITATION_TABLE):
            if not cls.check_for_table(table):
                click.echo("Table '{}' not found, creating...".format(table))
                cls.create_table(table, cls.fields[table])

        if not cls.check_for_table(cls.FTS_INDEX_TABLE):
            click.echo("Full text search index not found, creating...")
            cls.create_fts_table(cls.FTS_INDEX_TABLE, cls.fields[cls.FTS_INDEX_TABLE])

    @classmethod
    def create_fts_table(cls, fts_table, fields):
        query = "create virtual table {} using fts5 ({}, tokenize='porter unicode61')".format(
            fts_table,
            ", ".join(["{}".format(z(f, t)) for f, t, z in fields]))
        return cls.run_query(query)

    @classmethod
    def insert_into_table(cls, table_name, values):
        query = 'insert into {} values ({})'.format(table_name, ",".join(['?' for _ in values]))
        return cls.run_query(query, values)

    @classmethod
    def run_query(cls, query, parameters=(), commit=True, many=False):
        exec_func = cls.db.executemany if many else cls.db.execute
        try:
            result = exec_func(query, parameters)
        except sqlite3.Error as e:
            print e.message
            return None
        # .commit() method is needed for changes to be saved, can create false positives in tests
        # if left out since current connection will return its changes, but other connections will not see them
        if commit:
            cls.db.commit()
        return result

    @classmethod
    def is_attr_in_db(cls, attr, value, table_name):
        return cls.run_query(r'select exists(select * from {} where {}=?)'.format(table_name, attr), (value,),
                             commit=False).fetchall() != [(0,)]

    @classmethod
    def retrieve_attr_from_db(cls, attr, value, table_name, start_index=0, limit=None):
        result = cls.run_query(r'select * from {} where {}=?'.format(table_name, attr),
                               (value,),
                               commit=False).fetchall()
        return bound_array(result, start_index, limit)

    @classmethod
    def retrieve_multiple_attr_from_db(cls, attrs, values, table_name, relation=OR, start_index=0, limit=None):
        where_clause = cls.get_where_clause(attrs, relation)
        result = cls.run_query(r'select * from {} where {}'.format(table_name, where_clause),
                             values,
                             commit=False).fetchall()
        return bound_array(result, start_index, limit)

    @classmethod
    def retrieve_from_fts(cls, search_strings, source_types=None, start_index=0, limit=None):
        phrases = " ".join(search_strings)
        sources = cls.get_where_clause(['source_type' for _ in source_types], cls.OR) if source_types else None
        query = 'select uuid, source_hash, source_type, content, rank from {0} where {0} match ?{1} order by rank'.format(cls.FTS_INDEX_TABLE, ' and {}'.format(sources) if source_types else '')

        params = (phrases,) if not source_types else [phrases] + source_types
        result = cls.run_query(query, params, commit=False)
        cites = result.fetchall() if result else []
        return bound_array(cites, start_index, limit)

    @classmethod
    def check_for_table(cls, table_name):
        return cls.run_query(r'select exists(select name from sqlite_master where type=? and name=?)',
                             parameters=('table', table_name),
                             commit=False).fetchall() != [(0,)]

    @classmethod
    def add_to_extracted_table(cls, extracted_info, fts=False):
        # This is currently tied to the exact ordering of headers in headers.EXTRACTED_TABLE
        # and is thus pretty flimsy, might need to change this management if our use-cases
        # end up requiring more complexity
        db_values = (None,    # None because primary key
                     extracted_info.get('title', None), # Need .get() since not all types will have each field
                     extracted_info.get('source_uri', None),
                     extracted_info.get('extracted_datetime', None),
                     extracted_info.get('source_file_hash', None),
                     json.dumps(extracted_info))  # 'metadata' field is just a string dump of the JSON extracted_info object

        result = cls.insert_into_table(cls.EXTRACTED_TABLE, db_values)
        if fts and result:
            cls.insert_into_table(cls.FTS_INDEX_TABLE, (None,   # UUID not used
                                                        extracted_info.get('source_file_hash', None),
                                                        'extracted',
                                                        json.dumps(extracted_info)))
        return result

    # Currently adds to citation table if it appears to be a new entry
    # By 'appears' I mean that if all the key value pairs except UUID are identical
    # I assume its a duplicate and do not add it
    @classmethod
    def add_to_citation_table(cls, cite_ref, fts=False):
        table = cls.GAME_CITATION_TABLE if cite_ref.ref_type == GAME_CITE_REF else cls.PERFORMANCE_CITATION_TABLE
        if not cls.check_for_duplicate_citation(cite_ref, table):
            values = list(cite_ref.get_element_values())
            values.insert(0, None)                      # Primary Key
            values.append(datetime.now(tz=pytz.utc))    # Created timestamp
            values.append(cite_ref.to_json_string())    # Cite object
            result = cls.insert_into_table(table, values)
            if fts and result:
                cls.insert_into_table(cls.FTS_INDEX_TABLE, (cite_ref['uuid'],
                                                            None,   # Source file hash not used
                                                            cite_ref.ref_type,
                                                            cite_ref.to_json_string()))
            return result
        return False

    @classmethod
    def check_for_duplicate_citation(cls, cite_ref, table):
        # UUID for incoming cite_ref check will most likely always be unique
        where_clause_keys = cls.get_where_clause(cite_ref.get_element_names(exclude=['uuid']), cls.AND)
        query = r'select exists(select * from {} where {})'.format(table, where_clause_keys)
        result = cls.run_query(query, cite_ref.get_element_values(exclude=['uuid']), commit=False)
        return result.fetchall() != [(0,)]

    @staticmethod
    def get_where_clause(keys, relation):
        return relation.join(["{}=?".format(key) for key in keys])

    @classmethod
    def retrieve_performance_chain(cls, performance_uuid):
        if cls.is_attr_in_db('uuid', performance_uuid, cls.PERFORMANCE_CITATION_TABLE):
            current_db_values = cls.retrieve_attr_from_db('uuid', performance_uuid, cls.PERFORMANCE_CITATION_TABLE, limit=1)[0]
            current = cls.create_cite_ref_from_db(PERF_CITE_REF, current_db_values)
            current_prev_uuid = current['previous_performance_uuid']
            performance_chain = [current]

            if current_prev_uuid:
                prev = cls.retrieve_attr_from_db('uuid', current_prev_uuid, cls.PERFORMANCE_CITATION_TABLE)[0]
                while prev:
                    prev_cite = cls.create_cite_ref_from_db(PERF_CITE_REF, prev)
                    performance_chain.insert(0, prev_cite)
                    prev_uuid = prev_cite['previous_performance_uuid']
                    if prev_uuid:
                        prev = cls.retrieve_attr_from_db('uuid', prev_uuid, cls.PERFORMANCE_CITATION_TABLE)[0]
                    else:
                        prev = None
            return performance_chain
        return []

    @classmethod
    def retrieve_game_ref(cls, game_uuid):
        if cls.is_attr_in_db('uuid', game_uuid, cls.GAME_CITATION_TABLE):
            db_values = cls.retrieve_attr_from_db('uuid', game_uuid, cls.GAME_CITATION_TABLE, limit=1)[0]
            game_cite = cls.create_cite_ref_from_db(GAME_CITE_REF, db_values)
            return game_cite
        return None

    @classmethod
    def retrieve_perf_ref(cls, perf_uuid):
        if cls.is_attr_in_db('uuid', perf_uuid, cls.PERFORMANCE_CITATION_TABLE):
            db_values = cls.retrieve_attr_from_db('uuid', perf_uuid, cls.PERFORMANCE_CITATION_TABLE, limit=1)[0]
            perf_cite = cls.create_cite_ref_from_db(PERF_CITE_REF, db_values)
            return perf_cite
        return None

    @classmethod
    def retrieve_derived_performances(cls, game_uuid):
        perfs = cls.retrieve_attr_from_db('game_uuid', game_uuid, cls.PERFORMANCE_CITATION_TABLE)
        return [cls.create_cite_ref_from_db(PERF_CITE_REF, p_tuple) for p_tuple in perfs if p_tuple != (0,)]

    @classmethod
    def create_cite_ref_from_db(cls, ref_type, db_tuple):
        if ref_type == GAME_CITE_REF:
            db_row_dict = dict(zip(cls.headers[cls.GAME_CITATION_TABLE], db_tuple))
        elif ref_type == PERF_CITE_REF:
            db_row_dict = dict(zip(cls.headers[cls.PERFORMANCE_CITATION_TABLE], db_tuple))
        return generate_cite_ref(ref_type, **db_row_dict)  # Schema version is already present
