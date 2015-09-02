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
#   - type: the type of the element's value, current options are simply the
#       python standard types plus uuid
#

import uuid
from datetime import datetime
from lxml import html

GAME_CITE_REF = 'Game'
PERM_CITE_REF = 'Performance'


# Errors parked here
class SchemaError(BaseException):
    pass


# Schema definitions, currently here, will move to another doc if this
# becomes unmanageable
GAME_SCHEMA = {
    'version': {'0.1.0': {
        'elements': [
            ('title',                {'required': True}),
            ('identifier',           {'required': True}),
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
            ('source_data',          {'required': False})
        ]
    }}
}

PERFORMANCE_SCHEMA = {
    'version': {'0.1.0': {
        'elements': [
            ('title',                        {'required': True}),
            ('description',                  {'required': False}),
            ('identifier',                   {'required': True}),
            ('game_citation_identifier',     {'required': False}),
            ('input_events',                 {'required': False}),
            ('data_events',                  {'required': False}),
            ('replay_source',                {'required': False}),
            ('save_state_source',            {'required': False}),
            ('save_state_terminal',          {'required': False}),
            ('emulator',                     {'required': False}),
            ('emulated_system_configuration',{'required': False}),
            ('performer',                    {'required': False}),
            ('previous_performance',         {'required': False}),
            ('performance_start_datetime',   {'required': False}),
            ('performance_location',         {'required': False}),
            ('notes',                        {'required': False}),
            ('additional_elements',          {'required': False})
        ]
    }}
}

# Citation reference wrapper class
class CiteRef(object):

    def __init__(self, schema, version, ref_type):
        self.version = version
        self.elements = dict((element, None) for element in schema['elements'])
        self.schema = schema
        self.ref_type = ref_type

    def get_required_elements(self):
        return [e for e, info in self.schema['elements'] if info['required']]

    def get_missing_elements(self):
        return [e for e, value in self.elements.items() if not value]


# Citation factory method
def generate_cite_ref(ref_type, version):
    if ref_type == GAME_CITE_REF:
        if version not in get_game_cite_versions():
            raise SchemaError('There is no game citation with that version number.')
        return CiteRef(GAME_SCHEMA['version'][version], version, GAME_CITE_REF)
    elif ref_type == PERM_CITE_REF:
        if version not in get_perm_cite_versions():
            raise SchemaError('There is no performance citation with that version number.')
        return CiteRef(PERFORMANCE_SCHEMA['version'][version], version, PERM_CITE_REF)


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

