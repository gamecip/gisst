__author__ = 'erickaltman'

import re
import requests
from extractor import Extractor, WikipediaExtractor
from schema import GAME_SCHEMA, GameRef
from database import db

source_uris = [
    ('archive.org',     'The Internet Archive', Extractor),
    ('archive.vg',      'Archive.vg',           Extractor),
    ('mamedb.com',      'MAME Database',        Extractor),
    ('gamesdbase.com',  'Games Database',       Extractor),
    ('wikipedia.org',   'Wikipedia',            WikipediaExtractor),
    ('mobygames.com',   'Moby Games',           Extractor),
    ('giantbomb.com',   'Giant Bomb',           Extractor),
    ('twitch.tv',       'Twitch',               Extractor),
    ('youtube.com',     'YouTube',              Extractor)
]


def is_valid_uri(uri):
    try:
        requests.get(uri)
    except:
        return False
    return True


def process_game_uri(uri):
    e_class = find_extractor_class(uri)
    return e_class(requests.get(uri).text, GameRef)


def process_game_file(file_name):
    pass


def process_performance_uri(uri):
    pass


def process_performance_file(file_name):
    pass


def get_source_name(uri):
    for search_uri, name, _ in source_uris:
        if re.search(search_uri, uri):
            return name


def find_extractor_class(uri):
    for search_uri, _, extractor_class in source_uris:
        if re.search(search_uri, uri):
            return extractor_class
