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

GAME_SCHEMA = {
    'title':                {'required': True},
    'identifier':           {'required': True},
    'platform':             {'required': False},
    'developer':            {'required': False},
    'publisher':            {'required': False},
    'distributor':          {'required': False},
    'copyright_year':       {'required': False},
    'date_published':       {'required': False},
    'localization_region':  {'required': False},
    'version':              {'required': False},
    'data_image_checksum':  {'required': False},
    'data_image_source':    {'required': False},
    'notes':                {'required': False}
}

PERFORMANCE_SCHEMA = {
    'title':                        {'required': True},
    'description':                  {'required': False},
    'identifier':                   {'required': True},
    'game_citation_identifier':     {'required': False},
    'input_events':                 {'required': False},
    'data_events':                  {'required': False},
    'replay_source':                {'required': False},
    'save_state_source':            {'required': False},
    'save_state_terminal':          {'required': False},
    'emulator':                     {'required': False},
    'emulated_system_configuration':{'required': False},
    'performer':                    {'required': False},
    'previous_performance':         {'required': False},
    'performance_start_datetime':   {'required': False},
    'performance_location':         {'required': False},
    'notes':                        {'required': False},
    'additional_elements':          {'required': False}
}

# Stub reference classes for creation by the create_schema_object
# methods. Will probably be changing this and adding functionality
# in the future.


class Ref(object):

    def __init__(self):
        self.elements = {}
        self.schema = None

    def update_element(self, element_name, value):
        self.elements[element_name] = value

    def delete_element(self, element_name):
        del self.elements[element_name]

    @property
    def values(self):
        return [self.elements[e] for e in self.schema.keys()]


class GameRef(Ref):

    def __init__(self):
        super(GameRef, self).__init__()
        self.schema = GAME_SCHEMA


class PerformanceRef(Ref):

    def __init__(self):
        super(PerformanceRef, self).__init__()
        self.schema = PERFORMANCE_SCHEMA

# These are pretty much identical right now, will be much different
# later.
def create_game_schema_object():
    gr = GameRef()
    for element, info in GAME_SCHEMA.items():
        gr.__dict__[element] = dict(value=None, required=info['required'])
    return gr


def create_performance_schema_object():
    pr = PerformanceRef()
    for element, info in PERFORMANCE_SCHEMA.items():
        pr.__dict__[element] = dict(value=None, required=info['required'])
    return pr


def print_cite_ref(cite_ref):
    print_message = "Current {} Info\n".format(cite_ref.__class__.__name__)
    for element, info in cite_ref:
        print_message += "{} : {} \n".format(element, str(info['value']))

