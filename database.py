__author__ = 'erickaltman'

from pysqlite2 import dbapi2 as sqlite3
import os
import json
import pytz
import click
import uuid
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from datetime import datetime
from functools import partial
from collections import OrderedDict
from itertools import chain
from schema import (
    GAME_CITE_REF,
    PERF_CITE_REF,
    generate_cite_ref
)
from utils import bound_array

LOCAL_DATA_ROOT = os.path.expanduser("~/Library/Application Support/citetool-editor")
DB_FILE_NAME = '{}/cite.db'.format(LOCAL_DATA_ROOT)
DB_TEST_FILE_NAME = 'test_cite.db'
LOCAL_CITATION_DATA_STORE = '{}/cite_data'.format(LOCAL_DATA_ROOT)
LOCAL_GAME_DATA_STORE = '{}/game_data'.format(LOCAL_DATA_ROOT)

#   This is needed for managing db connections in SQLite because Flask runs each
#   session as a thread local
engine = create_engine("sqlite:////{}".format(DB_FILE_NAME))

#   We need to load the FTS extension for each connection
#   This event listener does that for each connection, regardless of whether it requires it
@event.listens_for(engine, "connect")
def connect(dbapi_connection, connection_rec):
    dbapi_connection.enable_load_extension(True)
    dbapi_connection.load_extension(DatabaseManager.FTS_EXT_PATH)

#   Database utility functions, might move somewhere else if there are too many
#   FOR NOW THERE ARE NO FOREIGN KEYS, to allow for them will need to add a
#   'PRAGMA foreign_keys = ON' call before each connection
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
    db = scoped_session(sessionmaker(bind=engine))
    current_db_file = DB_FILE_NAME

    EXTRACTED_TABLE = 'extracted_info'
    GAME_CITATION_TABLE = 'game_citation'
    GAME_FILE_PATH_TABLE = 'game_file_path'
    GAME_SAVE_TABLE = 'game_save_table'
    PERFORMANCE_CITATION_TABLE = 'performance_citation'
    SAVE_STATE_PERFORMANCE_LINK_TABLE = 'save_state_performance_link_table'
    FTS_INDEX_TABLE = 'fts_index_table'
    FTS_EXT_PATH = '{}/fts5.dylib'.format(LOCAL_DATA_ROOT)

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
            ('data_image_checksum_type', 'text',            field_constraint),
            ('data_image_checksum', 'text',                 field_constraint),
            ('data_image_source',   'text',                 field_constraint),
            ('notes',               'text',                 field_constraint),
            ('source_url',          'text',                 field_constraint),
            ('source_data',         'text',                 field_constraint),
            ('schema_version',      'text',                 field_constraint),
            ('created',             'datetime',             field_constraint),
            ('cite_object',         'text',                 field_constraint)
        ],
        GAME_FILE_PATH_TABLE: [
            ('id',                  'integer primary key',  field_constraint),
            ('game_uuid',           'text',                 field_constraint),
            ('save_state_uuid',     'text',                 field_constraint),
            ('is_executable',       'boolean',              field_constraint),
            ('main_executable',     'boolean',              field_constraint),
            ('file_path',           'text',                 field_constraint),
            ('source_data',         'text',                 field_constraint)
        ],
        GAME_SAVE_TABLE: [
            ('id',                                  'integer primary key',  field_constraint),
            ('uuid',                                'text',                 field_constraint),
            ('description',                         'text',                 field_constraint),
            ('game_uuid',                           'text',                 field_constraint),
            ('save_state_source_data',              'text',                 field_constraint),
            ('compressed',                          'boolean',              field_constraint),
            ('rl_starts_data',                      'text',                 field_constraint),
            ('rl_lengths_data',                     'text',                 field_constraint),
            ('rl_total_length',                     'integer',              field_constraint),
            ('save_state_type',                     'text',                 field_constraint), #  Values are 'battery', or 'state', may make ENUM later
            ('emulator_name',                       'text',                 field_constraint),
            ('emulator_version',                    'text',                 field_constraint),
            ('emt_stack_pointer',                   'integer',              field_constraint),
            ('stack_pointer',                       'integer',              field_constraint),
            ('time',                                'integer',              field_constraint),
            ('has_screen',                          'integer',              field_constraint),
            ('created_on',                          'datetime',             field_constraint), #    If this is imported, get creation date of file
            ('created',                             'datetime',             field_constraint)  #    Timestamp for db entry
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
        ],
        SAVE_STATE_PERFORMANCE_LINK_TABLE: [
            ('performance_uuid', 'text', field_constraint),
            ('save_state_uuid', 'text', field_constraint),
            ('time_index', 'integer', field_constraint),
            ('action', 'text', field_constraint) #    Action is "load" or "save"
        ]
    }

    headers = {
        EXTRACTED_TABLE: ('id', 'title', 'source_uri', 'extracted_datetime', 'source_file_hash', 'metadata'),
        FTS_INDEX_TABLE: ('uuid', 'source_hash', 'source_type', 'content'),
        GAME_CITATION_TABLE: [x for x, _, _ in fields[GAME_CITATION_TABLE]],
        PERFORMANCE_CITATION_TABLE: [x for x, _, _ in fields[PERFORMANCE_CITATION_TABLE]],
        GAME_FILE_PATH_TABLE: [x for x, _, _ in fields[GAME_FILE_PATH_TABLE]],
        GAME_SAVE_TABLE: [x for x, _, _ in fields[GAME_SAVE_TABLE]],
        SAVE_STATE_PERFORMANCE_LINK_TABLE: [x for x, _, _ in fields[SAVE_STATE_PERFORMANCE_LINK_TABLE]]
    }


    @classmethod
    def delete_db(cls):
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
        for table in (cls.EXTRACTED_TABLE,
                      cls.GAME_CITATION_TABLE,
                      cls.PERFORMANCE_CITATION_TABLE,
                      cls.GAME_SAVE_TABLE,
                      cls.GAME_FILE_PATH_TABLE,
                      cls.SAVE_STATE_PERFORMANCE_LINK_TABLE):
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
    def insert_into_table(cls, table_name, keys, values):
        query = 'insert into {}({}) values ({})'.format(table_name, #table to insert into
                                                         ",".join([k for k in keys]), #columns in table
                                                         ",".join([':{}'.format(k) for k in keys])) #mapping of columns ids to placeholder assignments for values
        return cls.run_query(query, dict(zip(keys,values)))

    @classmethod
    def update_table(cls, table_name, fields, values, where_fields, where_values, where_relation=AND):
        where_clause = cls.get_where_clause(where_fields, where_values, where_relation)
        set_clause = ", ".join(['{} = :{}'.format(f, f) for f in fields])
        result = cls.run_query(r'update {} set {} where {}'.format(table_name, set_clause, where_clause),
                               dict(zip(chain(fields, where_fields),chain(values, where_values))))
        return result

    @classmethod
    def delete_from_table(cls, table_name, fields, values, relation=AND):
        where_clause = cls.get_where_clause(fields, values, relation)
        result = cls.run_query(r'delete from {} where {}'.format(table_name, where_clause), dict(zip(fields, values)))
        return result

    @classmethod
    def run_query(cls, query, parameters=None, commit=True, many=False):
        try:
            result = cls.db.execute(query, parameters) if parameters else cls.db.execute(query)
        except sqlite3.Error as e:
            cls.db.rollback()
            print e.message
            return None
        # .commit() method is needed for changes to be saved, can create false positives in tests
        # if left out since current connection will return its changes, but other connections will not see them
        res = result.fetchall()
        if commit:
            cls.db.commit()
        return res

    @classmethod
    def retrieve_all_from_table(cls, table_name, start_index=0, limit=None):
        return bound_array(cls.run_query(r'select * from {}'.format(table_name), commit=False), start_index, limit)

    @classmethod
    def is_attr_in_db(cls, attr, value, table_name):
        return cls.run_query(r'select exists(select * from {0} where {1}=:{1})'.format(table_name, attr), {attr: value},
                             commit=False) != [(0,)]

    @classmethod
    def retrieve_attr_from_db(cls, attr, value, table_name, start_index=0, limit=None):
        result = cls.run_query(r'select * from {0} where {1}=:{1}'.format(table_name, attr, attr),
                               {attr: value},
                               commit=False)
        return bound_array(result, start_index, limit)

    @classmethod
    def retrieve_multiple_attr_from_db(cls, attrs, values, table_name, relation=OR, start_index=0, limit=None):
        where_clause = cls.get_where_clause(attrs, values, relation)
        result = cls.run_query(r'select * from {} where {}'.format(table_name, where_clause),
                             dict(zip(attrs, values)),
                             commit=False)
        return bound_array(result, start_index, limit)

    @classmethod
    def retrieve_from_fts(cls, search_strings, source_types=None, start_index=0, limit=None):
        phrases = " ".join(search_strings)
        sources = cls.get_where_clause_k_v(['source_type' for _ in source_types], ['{}'.format(s) for s in source_types], source_types, cls.OR) if source_types else None
        query = 'select uuid, source_hash, source_type, content, rank from {0} where {0} match :content{1} order by rank'.format(cls.FTS_INDEX_TABLE, ' and {}'.format(sources) if source_types else '')

        if not source_types:
            params = {'content': phrases}
        else:
            params = {k: k for k in source_types}
            params['content'] = phrases
        result = cls.run_query(query, params, commit=False)
        cites = result if result else []
        return bound_array(cites, start_index, limit)

    @classmethod
    def check_for_table(cls, table_name):
        return cls.run_query(r'select exists(select name from sqlite_master where type=:table and name=:name)',
                             parameters={'table': 'table', 'name': table_name},
                             commit=False) != [(0,)]

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

        result = cls.insert_into_table(cls.EXTRACTED_TABLE, cls.headers[cls.EXTRACTED_TABLE], db_values)
        if fts and result:
            cls.insert_into_table(cls.FTS_INDEX_TABLE, cls.headers[cls.FTS_INDEX_TABLE], (None,
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
            result = cls.insert_into_table(table, cls.headers[table], values)
            if fts and result:
                cls.insert_into_table(cls.FTS_INDEX_TABLE, cls.headers[cls.FTS_INDEX_TABLE], (cite_ref['uuid'],
                                                            None,   # Source file hash not used
                                                            cite_ref.ref_type,
                                                            cite_ref.to_json_string()))
            return result
        return False

    @classmethod
    def add_to_save_state_table(cls, fts=False, **fields):
        table = cls.GAME_SAVE_TABLE
        uid = str(uuid.uuid4())
        values = []
        values.insert(0, None)
        values.append(fields.get('uuid', uid))
        values.append(fields.get('description'))
        values.append(fields.get('game_uuid'))
        values.append(fields.get('save_state_source_data'))
        values.append(fields.get('rl_starts_data'))
        values.append(fields.get('rl_lengths_data'))
        values.append(fields.get('rl_total_length'))
        values.append(fields.get('compressed'))
        values.append(fields.get('save_state_type'))
        values.append(fields.get('emulator_name'))
        values.append(fields.get('emulator_version'))
        values.append(fields.get('emt_stack_pointer'))
        values.append(fields.get('stack_pointer'))
        values.append(fields.get('time'))
        values.append(fields.get('has_screen'))
        values.append(fields.get('created_on'))
        values.append(fields.get('created'))
        result = cls.insert_into_table(table, cls.headers[table], values)
        if fts and result:
            cls.insert_into_table(cls.FTS_INDEX_TABLE, cls.headers[cls.FTS_INDEX_TABLE], (fields.get('uuid'),
                                                        fields.get('save_state_source_data'),
                                                        fields.get('save_state_type'),
                                                        " ".join(x for x in fields.values() if isinstance(x, str) or isinstance(x, unicode))))
        return uid


    @classmethod
    def add_to_file_path_table(cls, **fields):
        table = cls.GAME_FILE_PATH_TABLE
        values = []
        values.insert(0, None)
        values.append(fields.get('game_uuid'))
        values.append(fields.get('save_state_uuid'))
        values.append(fields.get('is_executable'))
        values.append(fields.get('main_executable'))
        values.append(fields.get('file_path'))
        values.append(fields.get('source_data'))
        result = cls.insert_into_table(table, cls.headers[table], values)

    @classmethod
    def add_screen_to_state(cls, uuid):
        cls.update_table(cls.GAME_SAVE_TABLE, ('has_screen',), (True,), ['uuid'], [uuid])
        return True

    #   Copy existing file information to new record for save_state
    @classmethod
    def link_existing_file_to_save_state(cls, new_save_state_uuid, file_id):
        file = cls.retrieve_file_path(id=file_id)
        if file:
            source_file = file[0]
            source_file['save_state_uuid'] = new_save_state_uuid
            source_file['id'] = None
            new_values = source_file.values()
        else:
            return []

        return cls.insert_into_table(cls.GAME_FILE_PATH_TABLE, cls.headers[cls.GAME_FILE_PATH_TABLE], new_values)

    @classmethod
    def link_save_state_to_performance(cls, state_uuid, perf_uuid, time_index, action):
        if cls.is_attr_in_db('uuid', state_uuid, cls.GAME_SAVE_TABLE) and \
                cls.is_attr_in_db('uuid', perf_uuid, cls.PERFORMANCE_CITATION_TABLE):
            cls.insert_into_table(cls.SAVE_STATE_PERFORMANCE_LINK_TABLE,
                                  ['performance_uuid', 'save_state_uuid', 'time_index', 'action'],
                                  [perf_uuid, state_uuid, time_index, action])
            return cls.retrieve_state_perf_link(state_uuid, perf_uuid)
        else:
            return None

    #   Check if we already have the file in the database
    @classmethod
    def check_for_existing_file(cls, file_path, source_data):
        results = cls.retrieve_file_path(file_path=file_path, source_data=source_data, save_state_uuid=None)
        if results:
            return results[0]['id']
        else:
            return None

    #   Returns list of tuples [(source_path, target_path), ...]
    @classmethod
    def retrieve_paths_for_save_state(cls, save_state_uuid):
        paths = cls.retrieve_file_path(save_state_uuid=save_state_uuid)
        return [("/game_data/{}/{}".format(sd, fn), fp) for sd, fp, fn in map(lambda p: (p['source_data'],
                                                                                p['file_path'],
                                                                                p['file_path'].split('/')[-1]),
                                                                              paths)]

    @classmethod
    def check_for_duplicate_citation(cls, cite_ref, table):
        # UUID for incoming cite_ref check will most likely always be unique
        where_clause_keys = cls.get_where_clause(cite_ref.get_element_names(exclude=['uuid']), cite_ref.get_element_values(exclude=['uuid']), cls.AND)
        query = r'select exists(select * from {} where {})'.format(table, where_clause_keys)
        result = cls.run_query(query, dict(cite_ref.get_element_items(exclude=['uuid'])), commit=False)
        return result != [(0,)]

    @staticmethod
    def get_where_clause(keys, values, relation):
        return relation.join(map(lambda kv: "{}=:{}".format(kv[0], kv[0]) if kv[1] else "{} is null".format(kv[0]), zip(keys, values)))

    @staticmethod
    def get_where_clause_k_v(keys, var_names, values, relation):
        return relation.join(map(lambda kv: "{}:={}".format(kv[0],kv[1]) if kv[2] else "{} is null".format(kv[0]), zip(keys, var_names, values)))

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
                    prev = cls.retrieve_attr_from_db('uuid', prev_uuid, cls.PERFORMANCE_CITATION_TABLE)[0] if prev_uuid else None
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

    #   For now returns list of dicts with relevant state information
    @classmethod
    def retrieve_save_state(cls, **fields):
        states =  cls.retrieve_multiple_attr_from_db(fields.keys(), fields.values(), cls.GAME_SAVE_TABLE, cls.AND)
        return [OrderedDict(zip(cls.headers[cls.GAME_SAVE_TABLE], state_tuple)) for state_tuple in states]

    @classmethod
    def retrieve_state_perf_link(cls, state_uuid, perf_uuid):
        link = cls.retrieve_multiple_attr_from_db(['save_state_uuid', 'performance_uuid'],
                                                  [state_uuid, perf_uuid],
                                                  cls.SAVE_STATE_PERFORMANCE_LINK_TABLE, cls.AND)
        if link:
            return OrderedDict(zip(cls.headers[cls.SAVE_STATE_PERFORMANCE_LINK_TABLE], link[0]))
        else:
            return None

    @classmethod
    def retrieve_all_state_perf_links(cls, perf_uuid):
        links = cls.retrieve_multiple_attr_from_db(['performance_uuid'],
                                                   [perf_uuid],
                                                   cls.SAVE_STATE_PERFORMANCE_LINK_TABLE)
        link_info = [{'state_record': cls.retrieve_save_state(uuid=link[cls.headers[cls.SAVE_STATE_PERFORMANCE_LINK_TABLE].index('save_state_uuid')])[0],
                      'time_index': link[cls.headers[cls.SAVE_STATE_PERFORMANCE_LINK_TABLE].index('time_index')],
                      'action': link[cls.headers[cls.SAVE_STATE_PERFORMANCE_LINK_TABLE].index('action')]} for link in links]
        return link_info

    #   For now returns list of dicts with relevant path information
    @classmethod
    def retrieve_file_path(cls, **fields):
        paths = cls.retrieve_multiple_attr_from_db(fields.keys(), fields.values(), cls.GAME_FILE_PATH_TABLE, cls.AND)
        return [OrderedDict(zip(cls.headers[cls.GAME_FILE_PATH_TABLE], path_tuple)) for path_tuple in paths]

    @classmethod
    def create_cite_ref_from_db(cls, ref_type, db_tuple):
        if ref_type == GAME_CITE_REF:
            db_row_dict = dict(zip(cls.headers[cls.GAME_CITATION_TABLE], db_tuple))
        elif ref_type == PERF_CITE_REF:
            db_row_dict = dict(zip(cls.headers[cls.PERFORMANCE_CITATION_TABLE], db_tuple))
        return generate_cite_ref(ref_type, **db_row_dict)  # Schema version is already present
