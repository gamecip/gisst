__author__ = 'erickaltman'
# Extractors
# Classes dealing with automatic extraction of information from urls, files, etc.

# raises NotImplementedError as poor man's abstract base class


import bs4
from datetime import datetime
import pytz
import hashlib
import shutil
import os
import re
from utils import pairwise

local_extract_store = 'extracted_data'



# General Utils


# Saves things to the extract store, currently local storage
# Since this is organized by hashes on the files / pages, multiple
# entries in extracted_data db may refer to the same data
# on the file system.

# Saves pages linked to a uri in the extract_store
# hashed by uri and dt string in ISO format
# Returns hex hash of page_data
def save_page_to_extract_store(uri, dt, page_data):
    # http://stackoverflow.com/questions/273192/in-python-check-if-a-directory-exists-and-create-it-if-necessary
    # Note that not perfect but effective for now

    name_hash = hashlib.sha1(uri + dt).hexdigest()
    hash_dir = "{}/{}".format(local_extract_store, name_hash)

    if not os.path.exists(hash_dir):
        os.makedirs(hash_dir)

    def write_html_file(path, page_data):
        with open(path, 'w') as html_file:
            html_file.write(page_data.encode('utf8'))

    if len(page_data) > 1:
        for i, page in enumerate(page_data):
            write_html_file("{}/{}_{}.html".format(hash_dir, name_hash, i), page_data[i])
    else:
        write_html_file("{}/{}.html".format(hash_dir, name_hash), page_data[0])

    return name_hash


# Save arbitrary file to extract store
# Returns hex hash of file
# NOTE: for now this is using shutil.copy2 see: https://docs.python.org/2/library/shutil.html
# for note regarding the limitation of these copy functions in relation to system-specific file metadata
def save_file_to_extract_store(file_path):

    # TODO: move the filesystem stuff to specific functions

    # http://pythoncentral.io/hashing-files-with-python/
    BLOCKSIZE = 65536
    hasher = hashlib.sha1()
    with open(file_path, 'rb') as a_file:
        buf = a_file.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = a_file.read(BLOCKSIZE)

    hash = hasher.hexdigest()
    hash_dir = "{}/{}".format(local_extract_store, hash)

    #   Copies to directory with original filename
    shutil.copy2(file_path, hash_dir)
    return hash



# Game Citation Extractor listing one for each major citation source
# Includes extractor specific utility functions

class Extractor(object):

    def __init__(self, source):
        self.source = source

    def extract(self):
        raise NotImplementedError

    def validate(self):
        raise NotImplementedError



class WikipediaExtractor(Extractor):
    # List obtained from: https://en.wikipedia.org/wiki/Template:Infobox_video_game
    headers = {
        'developer':        u'Developer(s)',
        'publisher':        u'Publisher(s)',
        'distributor':      u'Distributor(s)',
        'director':         u'Director(s)',
        'producer':         u'Producer(s)',
        'designer':         u'Designer(s)',
        'programmer':       u'Programmer(s)',
        'artist':           u'Artist(s)',
        'writer':           u'Writer(s)',
        'composer':         u'Composer(s)',
        'series':           u'Series',
        'engine':           u'Engine',
        'platform':         u'Platform(s)',
        'release_date':     u'Release date(s)',
        'genre':            u'Genre(s)',
        'modes':            u'Mode(s)',
        'cabinet':          u'Cabinet',
        'arcade_system':    u'Arcade System',
        'cpu':              u'CPU',
        'sound':            u'Sound',
        'display':          u'Display'

    }
    # Rewrite at some point? Needed bi-directional map, probably should list of tuples
    headers_to_terms = dict([(value, key) for key, value in headers.items()])

    def extract(self):
        extracted_info = {}

        s = bs4.BeautifulSoup(self.source.text, 'html.parser')
        now = datetime.now(tz=pytz.utc).isoformat()

        # Direct info
        extracted_info['title'] = s.find('h1', class_='firstHeading').text
        extracted_info['source_uri'] = self.source.url
        extracted_info['extracted_datetime'] = now

        # Info_box information
        # Currently just plops them as a bag of text, there is not a completely consistent
        # means for listing some of these values and they will require additional processing
        info_box = WikipediaExtractor.get_wiki_table(s)
        for key in info_box:
            extracted_info[key] = info_box[key]

        # Save page text to disk
        extracted_info['source_file_hash'] = save_page_to_extract_store(self.source.url, now, [self.source.text])
        return extracted_info

    # Currently searches for the "Category: XXXX video games" tag on a wiki page, where XXXX is a year
    # Every game page should have these, though could include a few more checks if this doesn't cover everything
    def validate(self):
        return re.search("Category:[0-9]{4} video games", self.source.text)

    # Takes in a parsed BeautifulSoup object and exacts the infobox into a dict
    # No additional parsing is done of the table values aside from altering the headers to snake-case
    # and adding the text as line-separated tokens, since most info-boxes use <br/> for lists of terms
    @classmethod
    def get_wiki_table(cls, soup_object):
        trs = soup_object.find('table', class_='infobox').find_all('tr')
        table = {}
        for tr in trs:
            # Look at each pair of td tags, since infobox rows that we care about have two columns
            for h_text, v_text in [(h.text, v.text) for h, v in pairwise(tr.find_all('td'))]:
                # Needed since spaces is table show up as non-breaking Latin space instead of unicode space
                # see: http://stackoverflow.com/questions/10993612/python-removing-xa0-from-string for more details
                h_text = h_text.replace(u'\xa0', u' ')
                if h_text in WikipediaExtractor.headers_to_terms:
                    comp_term = WikipediaExtractor.headers_to_terms[h_text]
                    # removes blank lines and blank indexes
                    table[comp_term] = [x for x in re.split('\n+', v_text) if x != u'']
        return table


class MobyGamesExtractor(Extractor):

    def extract(self):
        pass

    def validate(self):
        pass


class GiantBombExtractor(Extractor):

    def extract(self):
        pass

    def validate(self):
        pass


class YoutubeExtractor(Extractor):

    def extract(self):
        pass

    # Not used, no way to determine if a video is about a video game
    def validate(self):
        pass

class TwitchExtractor(Extractor):

    def extract(self):
        pass

    def validate(self):
        pass
