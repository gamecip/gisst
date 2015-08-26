__author__ = 'erickaltman'

import urllib2
import re
from database import db
from schema import create_game_schema_object, create_performance_schema_object

source_uris = [
    ('archive.org', 'The Internet Archive'),
    ('archive.vg', 'Archive.vg'),
    ('mamedb.com', 'MAME Database'),
    ('gamesdbase.com', 'Games Database'),
    ('wikipedia.org', 'Wikipedia'),
    ('coolrom.com', 'CoolRom'),     # flagging since might be a copyright issue
    ('mobygames.com', 'Moby Games'),
    ('emulationzone.org', 'Emulation Zone'),
    ('giantbomb.com', 'Giant Bomb'),
    ('twitch.tv', 'Twitch'),
    ('youtube.com', 'YouTube')
]


def is_valid_uri(uri):
    try:
        urllib2.urlopen(uri)
    except:
        return False
    return True


def process_game_uri(uri):
    pass


def process_performance_uri(uri):
    pass


def get_source_name(uri):
    for (search_uri, name) in source_uris:
        if re.search(search_uri, uri):
            return name
