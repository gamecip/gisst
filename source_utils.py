__author__ = 'erickaltman'

import re
import os
import requests
import extractors
import hashlib

# Error classes
class SourceError(BaseException):
    pass

# Super simple regex, source name, extractor class
source_uris = [
    ('archive\.org',     'The Internet Archive', extractors.Extractor),
    ('archive\.vg',      'Archive.vg',           extractors.Extractor),
    ('mamedb\.com',      'MAME Database',        extractors.Extractor),
    ('gamesdbase\.com',  'Games Database',       extractors.Extractor),
    ('wikipedia\.org',   'Wikipedia',            extractors.WikipediaExtractor),
    ('mobygames\.com',   'Moby Games',           extractors.MobyGamesExtractor),
    ('giantbomb\.com',   'Giant Bomb',           extractors.GiantBombExtractor),
    ('twitch\.tv',       'Twitch',               extractors.TwitchExtractor),
    ('youtube\.com',     'YouTube',              extractors.YoutubeExtractor)
]

source_exts = [
    ('\.fm2$', 'FCEUX Movie File', extractors.FM2Extractor),
]

def get_extractor_for_uri(uri, source):
    for search_uri, _, extractor_class in source_uris:
        if re.search(search_uri, uri):
            return extractor_class(source)


def get_uri_source_name(uri):
    for search_uri, name, _ in source_uris:
        if re.search(search_uri, uri):
            return name
    return None

def get_extractor_for_file(filepath):
    for search_file, _, extractor_class in source_exts:
        if re.search(search_file, filepath):
            return extractor_class(filepath)


def get_file_source_name(filename):
    for ext, name, _ in source_exts:
        if re.search(ext, filename):
            return name
    return None


def get_url_source(source_uri):
    try:
        source = requests.get(source_uri)
    except BaseException as e:
        raise SourceError(e.message)
    return source


def get_file_hash(file_path):
    # http://pythoncentral.io/hashing-files-with-python/
    BLOCKSIZE = 65536
    hasher = hashlib.sha1()
    with open(file_path, 'rb') as a_file:
        buf = a_file.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = a_file.read(BLOCKSIZE)
    return hasher.hexdigest()
