__author__ = 'erickaltman'

import re
import requests
import extractors

# Error classes
class SourceError(BaseException):
    pass

source_uris = [
    ('archive.org',     'The Internet Archive', extractors.Extractor),
    ('archive.vg',      'Archive.vg',           extractors.Extractor),
    ('mamedb.com',      'MAME Database',        extractors.Extractor),
    ('gamesdbase.com',  'Games Database',       extractors.Extractor),
    ('wikipedia.org',   'Wikipedia',            extractors.WikipediaExtractor),
    ('mobygames.com',   'Moby Games',           extractors.MobyGamesExtractor),
    ('giantbomb.com',   'Giant Bomb',           extractors.GiantBombExtractor),
    ('twitch.tv',       'Twitch',               extractors.TwitchExtractor),
    ('youtube.com',     'YouTube',              extractors.YoutubeExtractor)
]

def get_extractor_for_uri(uri, source):
    for search_uri, _, extractor_class in source_uris:
        if re.search(search_uri, uri):
            return extractor_class(source)


def get_uri_source_name(uri):
    for search_uri, name, _ in source_uris:
        if re.search(search_uri, uri):
            return name

def get_file_source_name(filename):
    pass


def get_url_source(source_uri):
    try:
        source = requests.get(source_uri)
    except BaseException as e:
        raise SourceError(e.message)
    return source
