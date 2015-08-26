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


GAME_SCHEMA = {
    'title':
        {
            'required': True,
            'type': 'String'
        },
    'identifier':
        {
            'required': True,
            'type': 'uuid'
        },
    'platform':
        {
            'required': False,
            'type': 'String'
        },
    'developer':
        {
            'required': False,
            'type': 'String'
        },
    'publisher':
        {
            'required': False,
            'type': 'String'
        },
    'distributor':
        {
            'required': False,
            'type': 'String'
        },
    'copyright_year':
        {
            'required': False,
            'type': 'String'
        },
    'date_published':
        {
            'required': False,
            'type': 'String'
        },
    'localization_region':
        {
            'required': False,
            'type': 'String'
        },
    'version':
        {
            'required': False,
            'type': 'String'
        },
    'data_image_checksum':
        {
            'required': False,
            'type': 'String'
        },
    'data_image_source':
        {
            'required': False,
            'type': 'String'
        },
    'notes':
        {
            'required': False,
            'type': 'String'
        }
}

PERFORMANCE_SCHEMA = {
    'title':
        {
            'required': False,
            'type': 'String'
        },
    'description':
        {
            'required': False,
            'type': 'String'
        },
    'identifier':
        {
            'required': False,
            'type': 'String'
        },
    'game_citation_identifier':
        {
            'required': False,
            'type': 'String'
        },
    'input_events':
        {
            'required': False,
            'type': 'List'
        },
    'data_events':
        {
            'required': False,
            'type': 'List'
        },
    'replay_source':
        {
            'required': False,
            'type': 'String'
        },
    'save_state_source':
        {
            'required': False,
            'type': 'String'
        },
    'save_state_terminal':
        {
            'required': False,
            'type': 'String'
        },
    'emulator':
        {
            'required': False,
            'type': 'String'
        },
    'emulated_system_configuration':
        {
            'required': False,
            'type': 'List'
        },
    'performer':
        {
            'required': False,
            'type': 'List'
        },
    'previous_performance':
        {
            'required': False,
            'type': 'uuid'
        },
    'performance_start_datetime':
        {
            'required': False,
            'type': 'String'
        },
    'performance_location':
        {
            'required': False,
            'type': 'String'
        },
    'notes':
        {
            'required': False,
            'type': 'String'
        },
    'additional_elements':
        {
            'required': False,
            'type': 'List'
        }
}

# Stub reference classes for creation by the create_schema_object
# methods. Will probably be changing this and adding functionality
# in the future.


class GameRef:
    pass


class PerformanceRef:
    pass


# These are pretty much identical right now, will be much different
# later.
def create_game_schema_object():
    gr = GameRef()
    for (element, info) in GAME_SCHEMA.items():
        gr.__dict__[element] = dict(value=None, required=info['required'])
    return gr


def create_performance_schema_object():
    pr = PerformanceRef()
    for (element, info) in PERFORMANCE_SCHEMA.items():
        pr.__dict__[element] = dict(value=None, required=info['required'])
    return pr
