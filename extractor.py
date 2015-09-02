__author__ = 'erickaltman'
# Extractors
# Classes dealing with automatic extraction of information from urls, files, etc.
# Currently all deal with a base class of extractor and then go from there

# raises NotImplementedError as poor man's abstract base class

import bs4


class Extractor(object):

    def __init__(self, source):
        self.source = source

    def extract_metadata(self):
        raise NotImplementedError

    def extract_file(self, ref):
        raise NotImplementedError

    # Provides access to multiple refs from a single source (which seems to be more common than
    # I initially thought
    def get_refs(self):
        raise NotImplementedError



# Game Citation Extractor listing one for each major citation source

from itertools import izip

# Pairwise function from: http://stackoverflow.com/questions/5389507/iterating-over-every-two-elements-in-a-list
def pairwise(iterable):
    "s -> (s0,s1), (s2,s3), (s4, s5), ..."
    a = iter(iterable)
    return izip(a, a)


# Returns a header selection function for table header
def get_wiki_infobox_header(header):
    def table_func(source):
        return get_wiki_table(source)[header]
    return table_func

def get_wiki_table(source_text):
    bs = bs4.BeautifulSoup(source_text, 'html.parser')
    trs = bs.find('table', class_='infobox').find_all('tr')
    table = {}
    for tr in trs:
        for h_text, v_text in [(h.text, v.text) for h, v in pairwise(tr.find_all('td'))]:
            if h_text in WikipediaExtractor.headers_to_terms.keys():
                table[WikipediaExtractor.headers_to_terms] = v_text




class WikipediaExtractor(GameExtractor):
    headers = {
        'developer':    'Developer(s)',
        'publisher':    'Publisher(s)',
        'distributor':  'Distributor(s)',
        'producer':     'Producer(s)',
        'director':     'Director(s)',
        'designer':     'Designer(s)',
        'programmer':   'Programmer(s)',
        'artist':       'Artist(s)',
        'writer':       'Writer(s)',
        'composer':     'Composer(s)',
        'engine':       'Engine',
        'series':       'Series',
        'platform':     'Platform(s)',
        'release_date': 'Release date(s)',
        'genre':        'Genre(s)',
        'modes':        'Mode(s)'
    }
    # Rewrite at some point? Needed dict both directions, probably should list of tuples
    headers_to_terms = dict([(value, key) for key, value in headers.items()])

    def extract_metadata(self):
        pass

    # Not used here
    def extract_file(self, ref):
        pass

