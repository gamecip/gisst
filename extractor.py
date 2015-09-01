__author__ = 'erickaltman'
# Extractors
# Classes dealing with automatic extraction of information from urls, files, etc.
# Currently all deal with a base class of extractor and then go from there

# raises NotImplementedError as poor man's abstract base class

from properties import (
    NullProperty, SingleXPathProperty,
    UUIDProperty, SelectionProperty)
import bs4

class Extractor(object):

    def __init__(self, source, reference):
        self._properties = {}
        self.source = source
        self._ref = reference

        klass = self.__class__
        for element, info in self._ref.schema.items():
            if hasattr(klass, element):
                self._properties[element] = klass.__dict__[element]
            else:
                setattr(klass, element, NullProperty())
                klass.__dict__[element].required = info['required']
                klass.__dict__[element].extractor = self
                klass.__dict__[element].name = element
                klass.__dict__[element].cli_message = "".join(str(element).replace('_', ' ')).title() + "?"

    def extract(self):
        for prop in self._properties:
            self._ref.update_element(prop.name, prop.extract(self.source))

    def add_element_value_pair(self, element_name, value):
        if element_name in self._ref.schema.keys():
            self._ref.update_element(element_name, value)

    def retrieve_element_value(self, element_name):
        return self._ref.elements[element_name]

    def reference_object(self):
        return self._ref

    def get_missing_element_names(self):
        elements = []
        for element, value in self._ref.elements:
            if not value:
                elements.append(element)
        return elements

    def get_all_element_names(self):
        return [element for element in self._ref.schema.keys()]


# Game Citation Extractor listing one for each major citation source and a generic extractor
# this also includes callable functions for CallableProperty on a specific extractor

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
    trs = bs.find('table').find_all('tr')
    table = {}
    for tr in trs:
        for h_text, v_text in [(h.text, v.text) for h, v in pairwise(tr.find_all('td'))]:
            if h_text in WikipediaExtractor.headers_to_terms.keys():
                table[WikipediaExtractor.headers_to_terms] = v_text




class WikipediaExtractor(Extractor):
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

    title = SingleXPathProperty(r'//*[@id="firstHeading"]/i')
    identifier = UUIDProperty()
    platform = SelectionProperty(get_wiki_infobox_header('platform'))

