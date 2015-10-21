__author__ = 'erickaltman'

# Storing the current ideations of the game and performance metadata
# here. Will probably alter this setup if we end up changing things a
# lot or if maintenance becomes an issue.
#
# THIS WILL CHANGE rather soon, just need a placeholder for the schema information
# that is not in a google doc.
#
# Each schema consists of elements that take specific types of values
# and comport to specific properties:
#
#   - required: if True this element is required for a complete citation
#   - default: default value is nothing else is provided
#

import uuid
import json
import datetime
import pprint
from collections import OrderedDict

GAME_CITE_REF = 'game'
PERF_CITE_REF = 'performance'
GAME_SCHEMA_VERSION = '0.1.0'
PERF_SCHEMA_VERSION = '0.1.0'

# Errors parked here
class SchemaError(BaseException):
    pass


# Schema definitions, currently here, will move to another doc if this
# becomes unmanageable
GAME_SCHEMA = {
    'version': {'0.1.0':
        {
            'elements': [
                ('title',                {'required': True}),
                ('uuid',                 {'required': True}),
                ('platform',             {'required': False}),
                ('developer',            {'required': False}),
                ('publisher',            {'required': False}),
                ('distributor',          {'required': False}),
                ('copyright_year',       {'required': False}),
                ('date_published',       {'required': False}),
                ('localization_region',  {'required': False}),
                ('version',              {'required': False}),
                ('data_image_checksum',  {'required': False}),
                ('data_image_source',    {'required': False}),
                ('notes',                {'required': False}),
                ('source_url',           {'required': False}),
                ('source_data',          {'required': False}),
                ('schema_version',       {'required': True,
                                          'default': '0.1.0'}),
            ]
        }
    }
}

PERFORMANCE_SCHEMA = {
    'version': {'0.1.0': {
        'elements': [
            ('title',                           {'required': True}),
            ('description',                     {'required': False}),
            ('uuid',                            {'required': True}),
            ('game_uuid',                       {'required': False}),
            ('inputs',                          {'required': False}),
            ('input_events',                    {'required': False}),
            ('data_events',                     {'required': False}),
            ('replay_source_purl',              {'required': False}),
            ('replay_source_file_ref',          {'required': False}),
            ('recording_agent',                 {'required': False}),
            ('save_state_source_purl',          {'required': False}),
            ('save_state_source_file_ref',      {'required': False}),
            ('save_state_terminal_purl',        {'required': False}),
            ('save_state_terminal_file_ref',    {'required': False}),
            ('emulator_name',                   {'required': False}),
            ('emulator_version',                {'required': False}),
            ('emulator_operating_system',       {'required': False}),
            ('emulator_system_dependent_images',{'required': False}),
            ('emulator_system_configuration',   {'required': False}),
            ('performer',                       {'required': False}),
            ('previous_performance_uuid',       {'required': False}),
            ('start_datetime',                  {'required': False}),
            ('location',                        {'required': False}),
            ('notes',                           {'required': False}),
            ('additional_info',                 {'required': False}),
            ('schema_version',                  {'required': True,
                                                 'default': '0.1.0'})
        ]
    }}
}

# Citation reference wrapper class
class CiteRef(object):

    def __init__(self, schema, schema_version, ref_type, **kwargs):
        self.elements = OrderedDict((e, i.get('default', None)) for e, i in schema['elements'])
        self.schema = schema
        self.ref_type = ref_type
        self.schema_version = schema_version

        for key in kwargs:
            if key in self.elements:
                self.elements[key] = kwargs[key]

        if not self['uuid']:
            self['uuid'] = str(uuid.uuid4())

    def get_required_elements(self):
        return tuple([e for e, info in self.schema['elements'] if info['required']])

    def get_missing_elements(self):
        return tuple([e for e, value in self.elements.items() if not value])

    def get_element_names(self, exclude=None):
        if exclude:
            return tuple([e for e in self.elements.keys() if e not in exclude])
        return tuple([e for e in self.elements.keys()])

    def get_element_values(self, exclude=None):
        if exclude:
            return tuple([v for e, v in self.elements.items() if e not in exclude])
        return tuple([v for v in self.elements.values()])

    def to_json_string(self):
        #   Convert datetimes to strings for json encoding
        json_dict = dict(map(lambda x: (x[0], x[1].isoformat()) if isinstance(x[1], datetime.datetime) else (x[0], x[1]),
                        self.elements.items()))
        return json.dumps(json_dict)

    def to_pretty_string(self):
        return "\n".join(["{} : {}".format(e, v) for e, v in self.elements.items()])

    def __repr__(self):
        return str(self.elements)

    def __getitem__(self, key):
        return self.elements[key]

    def __setitem__(self, key, value):
        if key in self.elements:
            self.elements[key] = value
        else:
            raise KeyError('{} not found in cite reference elements.')


# Citation factory method
def generate_cite_ref(ref_type, schema_version, **kwargs):
    ref_select = dict([(GAME_CITE_REF, GAME_SCHEMA), (PERF_CITE_REF, PERFORMANCE_SCHEMA)])
    if ref_type == GAME_CITE_REF:
        if schema_version not in get_game_cite_versions():
            raise SchemaError('There is no game citation with that version number.')
    elif ref_type == PERF_CITE_REF:
        if schema_version not in get_perm_cite_versions():
            raise SchemaError('There is no performance citation with that version number.')

    if 'schema_version' in kwargs:
        return CiteRef(ref_select[ref_type]['version'][schema_version], ref_type=ref_type, **kwargs)
    else:
        return CiteRef(ref_select[ref_type]['version'][schema_version], schema_version, ref_type, **kwargs)


# Citation Utilities
def get_game_cite_versions():
    return GAME_SCHEMA['version'].keys()


def get_perm_cite_versions():
    return PERFORMANCE_SCHEMA['version'].keys()


def print_cite_ref(cite_ref):
    print_message = "Current {} Info\n: Cite Version: {}".format(cite_ref.ref_type, cite_ref.version)
    for element, _ in cite_ref.schema['elements']:  # using schema here to always print in same order
        print_message += "{} : {} \n".format(element, cite_ref.elements[element])
    return print_message

