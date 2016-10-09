__author__ = 'erickaltman'
# Extractors
# Classes dealing with automatic extraction of information from urls, files, etc.


import bs4
import base64
from datetime import datetime
import calendar
import pytz
import hashlib
import shutil
import pipes
import os
import re
import subprocess
import requests
import json
import StringIO
import youtube_dl
from collections import OrderedDict
from utils import (
    pairwise,
    pairwise_overlap,
    merge_dicts,
    replace_xa0,
    snake_case
)
from schema import (
    generate_cite_ref,
    GAME_CITE_REF,
    PERF_CITE_REF,
    GAME_SCHEMA_VERSION,
    PERF_SCHEMA_VERSION
)

from database import (
    LOCAL_CITATION_DATA_STORE,
    LOCAL_GAME_DATA_STORE,
    LOCAL_DATA_ROOT,
)
from database import DatabaseManager as dbm


# General Utils


# Saves things to the extract store, currently local storage
# Since this is organized by hashes on the files / pages, multiple
# entries in extracted_data db may refer to the same data
# on the file system.

TEMP_DIRECTORY = os.path.join(LOCAL_DATA_ROOT, 'tmp')

# Saves pages linked to a uri in the extract_store
# hashed by uri and dt string in ISO format
# Returns hex hash of page_data
def save_page_to_extract_store(uri, dt, page_data):
    name_hash = hashlib.sha1(uri + dt).hexdigest()
    hash_dir = os.path.join(LOCAL_CITATION_DATA_STORE, name_hash)

    # http://stackoverflow.com/questions/273192/in-python-check-if-a-directory-exists-and-create-it-if-necessary
    # Note that not perfect but effective for now
    if not os.path.exists(hash_dir):
        os.makedirs(hash_dir)

    def write_html_file(path, page_data):
        with open(path, 'w') as html_file:
            html_file.write(page_data.encode('utf8'))

    if len(page_data) > 1:
        for i, page in enumerate(page_data):
            write_html_file(os.path.join(hash_dir, "{}_{}.html".format(name_hash, i)), page_data[i])
    else:
        write_html_file(os.path.join(hash_dir, "{}.html".format(name_hash)), page_data[0])

    return name_hash


def get_byte_array_hash(b_array):
    hasher = hashlib.sha1()
    hasher.update(b_array)
    return hasher.hexdigest()

def save_byte_array_to_store(b_array, file_name=None, store_path=None):
    hasher = hashlib.sha1()
    hasher.update(b_array)
    hash = hasher.hexdigest()

    if not store_path:
        hash_dir = os.path.join(LOCAL_CITATION_DATA_STORE, hash)
    else:
        hash_dir = os.path.join(store_path, hash)

    if not os.path.exists(hash_dir):
        os.makedirs(hash_dir)

    if not file_name:
        file_name = "{}_{}".format(hash, calendar.timegm(datetime.utcnow().timetuple()))

    f = open(os.path.join(hash_dir, file_name), "wb")
    f.write(b_array)
    f.close()

    return hash, file_name


# Save arbitrary file to extract store
# Returns hex hash of file
# NOTE: for now this is using shutil.copy2 see: https://docs.python.org/2/library/shutil.html
# for note regarding the limitation of these copy functions in relation to system-specific file metadata
def save_file_to_store(file_path, store_path=None):

    # http://pythoncentral.io/hashing-files-with-python/
    BLOCKSIZE = 65536
    hasher = hashlib.sha1()
    with open(file_path, 'rb') as a_file:
        buf = a_file.read(BLOCKSIZE)
        while len(buf) > 0:
            hasher.update(buf)
            buf = a_file.read(BLOCKSIZE)

    hash = hasher.hexdigest()
    #   Default to citation data store
    if not store_path:
        hash_dir = os.path.join(LOCAL_CITATION_DATA_STORE, hash)
    else:
        hash_dir = os.path.join(store_path, hash)

    if not os.path.exists(hash_dir):
        os.makedirs(hash_dir)

    #   Copies to directory with original filename
    shutil.copy2(file_path, hash_dir)
    return hash

class ExtractorError(BaseException):
    pass

# Game Extractor listing one for each major citation source
# Includes extractor specific utility functions

class Extractor(object):
    supports_games = False
    supports_performances = False

    def __init__(self, source):
        self.source = source
        self.extracted_info = None

    def extract(self, options=None):
        raise NotImplementedError

    def validate(self):
        raise NotImplementedError

    #   Creates citations from extracted data to the best of its abilities
    #   Also returns potentially useful extracted data in an extracted options
    #   dictionary keyed to the fresh uuid of each citation in citations
    def create_citation(self):
        raise NotImplementedError


# URI Site Extractors

class WikipediaExtractor(Extractor):
    supports_games = True
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

    def extract(self, options=None):
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
        self.extracted_info = extracted_info

    # Currently searches for the "Category: XXXX video games" tag on a wiki page, where XXXX is a year
    # Every game page should have these, though could include a few more checks if this doesn't cover everything
    def validate(self):
        return re.search("Category:[0-9]{4} video games", self.source.text)

    def create_citation(self):
        pass

    # Takes in a parsed BeautifulSoup object and extracts the infobox into a dict
    # No additional parsing is done of the table values aside from altering the headers to snake-case
    # and adding the text as line-separated tokens, since most info-boxes use <br/> for lists of terms
    @classmethod
    def get_wiki_table(cls, soup_object):
        trs = soup_object.find('table', class_='infobox').find_all('tr')
        table = {}
        for tr in trs:
            # Look at each pair of td tags, since infobox rows that we care about have two columns
            for h_text, v_text in [(replace_xa0(h.text), v.text) for h, v in pairwise(tr.find_all('td'))]:
                if h_text in WikipediaExtractor.headers_to_terms:
                    comp_term = WikipediaExtractor.headers_to_terms[h_text]
                    # removes blank lines and blank indexes
                    table[comp_term] = [x for x in re.split('\n+', v_text) if x != u'']

        return table


class MobyGamesExtractor(Extractor):
    supports_games = True
    headers = {
        'coreGameRelease': {
            'publisher':        u'Published by',
            'developer':        u'Developed by',
            'release_date':     u'Released',
            'official_site':    u'Official Site',
            'platform':         u'Platforms',
            'also_for':         u'Also For'
    },
        'coreGameGenre': {
            'genre':            u'Genre',
            'perspective':      u'Perspective',
            'theme':            u'Theme',
            'esrb_rating':      u'ESRB Rating',
            'sport':            u'Sport'
        }
    }

    platform_uri_regex = r'/game/[a-z0-9\-]+/[a-z0-9\-]+'
    general_game_uri_regex = r'/game/[a-z0-9\-]+'

    def extract(self, options=None):

        # Figure out if specific or general url
        # /game/{platform}/{game name} is specific, otherwise /game/{game name}
        is_specific = re.search(r'http://www\.mobygames\.com/game/[a-z0-9\-]+/[a-z0-9\-_]+', self.source.url)

        if is_specific:
            main_url = is_specific.group()
        else:
            main_url = re.search(r'http://www\.mobygames\.com/game/[a-z0-9\-_]+', self.source.url).group()

        main_page = self.get_page(main_url)
        credits_page = self.get_page(main_url + '/credits')
        release_page = self.get_page(main_url + '/release-info')
        specs_page = self.get_page(main_url + '/techinfo')
        rating_page = self.get_page(main_url + '/rating-systems')

        extracted_info = merge_dicts(MobyGamesExtractor.scrape_main_page(main_page),
                                     MobyGamesExtractor.scrape_credit_page(credits_page),
                                     MobyGamesExtractor.scrape_release_page(release_page),
                                     MobyGamesExtractor.scrape_specs_page(specs_page),
                                     MobyGamesExtractor.scrape_rating_page(rating_page))

        html_data = [x.text for x in [y for y in (main_page, credits_page, release_page, specs_page, rating_page) if y]]
        now = datetime.now(tz=pytz.utc).isoformat()
        extracted_info['extracted_datetime'] = now
        extracted_info['source_uri'] = self.source.url # should this be the base main_url or the specific one slurped?
        extracted_info['source_file_hash'] = save_page_to_extract_store(self.source.url,
                                                                        now,
                                                                        html_data)
        self.extracted_info = extracted_info

    def validate(self):
        return re.search(r'www\.mobygames\.com/game/', self.source.url)

    #   If ignore options is True create_citation will choose first option from extracted data
    def create_citation(self, ignore_options=False):
        if not self.extracted_info:
            return []

        def add_to_cite_or_options(cite, extracted, e_options, source_key, target_key):
            values = extracted[source_key] if source_key in extracted else None
            if values:
                if isinstance(values, list):
                    if not ignore_options and len(values) > 1:
                        cite[target_key] = None
                        e_options[target_key] = values
                    else:
                        cite[target_key] = values[0]
                else:
                    cite[target_key] = values
            return cite, e_options

        cite_ref = generate_cite_ref(GAME_CITE_REF, GAME_SCHEMA_VERSION)
        extracted_options = dict()
        for s, t in [
            ('developer', 'developer'),
            ('publisher', 'publisher'),
            ('distributor', 'distributor'),
            ('title', 'title'),
            ('release_date', 'date_published'),
            ('platform', 'platform'),
            ('source_uri', 'source_url'),
            ('source_file_hash', 'source_data')
        ]:
            cite_ref, extracted_options = add_to_cite_or_options(cite_ref, self.extracted_info, extracted_options, s, t)

        if cite_ref['date_published']:
            year = re.search(r"[0-9]{4}", cite_ref['date_published'])
            if year:
                cite_ref['copyright_year'] = year.group()

        return cite_ref, extracted_options

    @staticmethod
    def get_search_uris(search_terms, offset=None, include_attributes=False):
        uri = "http://www.mobygames.com/search/quick"
        get_data = {
            'q': "+".join(search_terms.split(' ')), # search terms
            'p': -1,                                # platform = 'All Platforms'
            'sFilter': 1,                           # use a search filter
            'sG': 'on'                              # turn on 'Games' search filter
        }

        #   Offset automatically defaults to floor of 50 increments
        #   [1-49] -> 0, [51-99] -> 50, [101-149] -> 100, etc.
        if offset:
            get_data['offset'] = offset % 50 * 50
        if include_attributes:
            get_data['sA'] = 'on'

        page_data = MobyGamesExtractor.get_page(uri, get_data)

        b = bs4.BeautifulSoup(page_data.text, 'html.parser')
        #   Grab all the hrefs on the page and convert them to absolute urls
        uris = ["http://www.mobygames.com" + u['href'] for u in b.find_all('a')]

        #   Filter out all those that are not explicit links to a game + platform page
        return [u for u in uris if re.search(MobyGamesExtractor.platform_uri_regex, u)]

    @staticmethod
    def scrape_main_page(page_data):
        main_dict = {}

        if not page_data:
            return main_dict

        b = bs4.BeautifulSoup(page_data.text, 'html.parser')

        # Title
        main_dict['title'] = b.find('h1', class_='niceHeaderTitle').find('a').text

        # Title Platform
        header_platform = b.find('h1', class_='niceHeaderTitle').find('small')
        if header_platform:
            main_dict['platform'] = [re.sub(r'\(|\)', u'', header_platform.text)]

        # Uses headers to find information in specific div, applies edit_funcs to list of terms if
        # some processing is needed, edit_func takes a list of terms and a field name and returns a list of terms
        # Current just adds to the main_dict from the outer scope
        def core_box_extraction(div_id, edit_funcs):
            for field, div_string in MobyGamesExtractor.headers[div_id].items():
                core_div = b.find('div', id=div_id).find('div', string=div_string)
                if core_div:
                    ts = [replace_xa0(x.text) for x in core_div.next_sibling()]
                    main_dict[field] = reduce((lambda terms, func: func(terms, field)),
                                              edit_funcs,
                                              [replace_xa0(x.text) for x in core_div.next_sibling()])

        def clear_also_for(terms, f):
            if f == 'also_for':
                try:
                    terms.remove(u'Combined View') # Not a platform!
                except ValueError:
                    pass
            return terms

        # Probably want official site url saved
        def add_official_site_url(terms, f):
            if f == 'official_site':
                main_dict['official_site_url'] = b.find(id='coreGameRelease').find('a', string=terms[0])['href']
            return terms

        # Publisher, Developer, Release Date, Platforms
        core_box_extraction('coreGameRelease', (clear_also_for, add_official_site_url))
        # Genre, Theme, Perspective, Sport, ESRB Rating
        core_box_extraction('coreGameGenre', ())

        return main_dict

    @staticmethod
    def scrape_credit_page(page_data):
        main_dict = {}

        if not page_data:
            return main_dict

        # Some entries have no credits for that specific version (first match)
        # Others have recommendations for other credits if they are available (second),
        # We don't follow that second link since this should just extract the exact root url the user requested
        if re.search(r'There are no credits for the', page_data.text) or\
                re.search(r'The following releases of this game have credits', page_data.text):
            main_dict['credits'] = 'none'
            return main_dict

        b = bs4.BeautifulSoup(page_data.text, 'html.parser')

        # All MobyGames credit listings in tables with credits split by contributing companies
        # credits_dict -> {company_name: job_position: [name_of_person, ...]}
        def extract_credits_table(table_object):
            credits_dict = {}
            cred_header = None
            for tr in table_object.find_all('tr'):
                tds = tr.find_all('td')
                if len(tds) == 1:
                    cred_header = replace_xa0(tds[0].text)
                    if cred_header == u'Credits':
                        cred_header = u'General'
                    credits_dict[cred_header] = {}
                else:
                    h_text = replace_xa0(tds[0].text)
                    # This searches by linked names, so does not catch additional text not in an <a> tag
                    # So if <a>{person name}</a>{other text}, only person name is captured
                    v = {'names': [replace_xa0(a.text) for a in tds[1].find_all('a')],
                         'full_text': replace_xa0(tds[1].text)}
                    credits_dict[cred_header][h_text] = v
            return credits_dict

        # Currently only scraping direct credits, could also scrap collaborations if that would be useful
        main_dict['credits'] = extract_credits_table(b.find('table', summary='List of Credits'))

        return main_dict

    @staticmethod
    def scrape_release_page(page_data):
        main_dict = {}

        if not page_data:
            return main_dict

        b = bs4.BeautifulSoup(page_data.text, 'html.parser')

        # Try to get the first h2's parent, only h2's on release page are platform names
        # If not present, there is no release information
        try:
            release_div = b.find('h2').parent
        except AttributeError:
            return main_dict

        main_dict['release_platforms'] = {}

        # Releases are a straight list of divs without much identifying information, thus this organization
        # instead of a rather large for loop and condition mess
        header_rules = (('header', 'attr'), ('header', 'rel_info'))
        attr_rules = (('attr', 'attr'), ('attr', 'rel_info'))
        patch_rules = (('patch', 'patch_rel_info'),)
        patch_rel_info_rules = (('patch_rel_info', 'patch_rel_info'),)
        rel_info_rules = (('rel_info', 'rel_info'), ('rel_info', 'patch'))
        index_rule = (('rel_info', 'attr'), ('rel_info', 'header'), ('patch_rel_info', 'header'))
        stop_rule = (('attr', None), ('rel_info', None), ('patch_rel_info', None))

        def create_div_tuple(div):
            if div.name == u'h2':
                # ('header', platform name)
                return 'header', replace_xa0(div.text)
            elif div.name == u'b':
                # ('patch', None)
                return 'patch', None
            elif 'class' in div.attrs and u'relInfo' in div['class']:
                # ('patch_rel_info', {relInfoTitle: relInfoDetails, ...})
                return 'patch_rel_info', dict([(replace_xa0(div.find(class_='relInfoTitle').text),
                                                replace_xa0(div.find(class_='relInfoDetails').text))])
            elif 'class' in div.attrs and u'floatholder' in div['class']:
                # ('attr', {attr_name: [value, ...]})
                return 'attr', {snake_case(replace_xa0(div.find(class_='fl').text)): [a.text for a in div.find_all('a')]}
            elif div.find(class_='relInfo'):
                # ('rel_info', {relInfoTitle: relInfoDetails, ...})
                return 'rel_info', dict([(replace_xa0(r.find(class_='relInfoTitle').text),
                                          replace_xa0(r.find(class_='relInfoDetails').text)) for r in div.find_all(class_='relInfo')])
            else:
                return None, None

        # Pages with patch histories insert newline characters that convert to NavigableStrings, don't want those
        release_divs = map(create_div_tuple, [c for c in release_div.children if not isinstance(c, bs4.NavigableString)])
        release_platform = None
        rel_dict = {'releases': []}
        for first, second in pairwise_overlap(release_divs):
            rule = (first[0], second[0])
            if rule in header_rules:
                # Start a new listing for platform
                release_platform = first[1]
                main_dict['release_platforms'][release_platform] = []
            elif rule in patch_rules:
                # Add key for patch history
                rel_dict['patch_history'] = []
            elif rule in attr_rules:
                # Add key / value to release dict
                rel_dict = merge_dicts(rel_dict, first[1])
            elif rule in rel_info_rules:
                # Add new relInfo to release dict
                rel_dict['releases'].append(first[1])
            elif rule in patch_rel_info_rules:
                # Add patch relInfo to release dict
                rel_dict['patch_history'].append(first[1])
            elif rule in index_rule:
                # Add new relInfo to current release dict and start new one
                if rule[0] == 'rel_info':
                    rel_dict['releases'].append(first[1])
                elif rule[0] == 'patch_rel_info':
                    rel_dict['patch_history'].append(first[1])
                main_dict['release_platforms'][release_platform].append(rel_dict)
                rel_dict = {'releases': []}
            elif rule in stop_rule:
                # Out of release information divs, clean up and stop processing
                if rule[0] == 'attr':
                    rel_dict = merge_dicts(rel_dict, first[1])
                elif rule[0] == 'rel_info':
                    rel_dict['releases'].append(first[1])
                elif rule[0] == 'patch_rel_info':
                    rel_dict['patch_history'].append(first[1])
                main_dict['release_platforms'][release_platform].append(rel_dict)
                break

        return main_dict

    @staticmethod
    def scrape_specs_page(page_data):
        main_dict = {}
        if not page_data:
            return main_dict

        b = bs4.BeautifulSoup(page_data.text, 'html.parser')

        main_dict['specs'] = []

        # All spec information in platform specific tables
        for table in b.find_all('table', class_='techInfo'):
            tds = table.find_all('td')[1:]  # First td is table header title
            table_dict = dict([(snake_case(replace_xa0(h.text)),
                               [replace_xa0(a.text) for a in v.find_all('a')]) for h, v in pairwise(tds)])
            table_dict['platform'] = replace_xa0(table.find('thead').text)
            main_dict['specs'].append(table_dict)

        return main_dict

    @staticmethod
    def scrape_rating_page(page_data):
        main_dict = {}
        if not page_data:
            return main_dict

        b = bs4.BeautifulSoup(page_data.text, 'html.parser')

        main_dict['rating_platform'] = {}

        for h in b.find_all('h2'):
            rating_dict = dict([tuple(replace_xa0(tr.text).split(u':', 1)) for tr in h.next_sibling.find_all('tr')])
            main_dict['rating_platform'][replace_xa0(h.text)] = rating_dict

        return main_dict

    @staticmethod
    def get_page(uri, params=None):
        try:
            source = requests.get(uri, params=params)
        except BaseException as e:
            print e.message
            return None
        return source


class GiantBombExtractor(Extractor):

    def extract(self, options=None):
        pass

    def validate(self):
        pass


# URI Video extractors

class YoutubeExtractor(Extractor):
    supports_performances = True


    def extract(self, options=None):
        youtube_opts  = {
            'outtmpl': u'{}/%(title)s.%(ext)s'.format(TEMP_DIRECTORY), # Template location for temporary file storage
            'writedescription': True, # Write description file to template location
            'writeinfojson': True, # Write JSON info file to template location
            'writeannotations': True, # Write Annotations XML file to template location
            'progress_hooks': [self.wrap_up_extraction], # Hook called on progress updates from youtube-dl process
            'ignoreerrors': True,
            'format': 'mp4' # Only downloads mp4 for now (if available)
        }

        # Create tmp directory if not present
        if not os.path.exists(TEMP_DIRECTORY):
            os.makedirs(TEMP_DIRECTORY)

        # Call youtube_dl extraction process
        with youtube_dl.YoutubeDL(youtube_opts) as ydl:
            ydl.download([self.source.url])

    # No way to determine if a video is about a video game
    # Using youtube-dl regex to check, might change later
    def validate(self):
        import youtube_dl.extractor.youtube as youtube
        return re.search(youtube.YoutubeIE._VALID_URL, self.source.url)

    # TODO: why does this return an empty list?
    def create_citation(self):
        if not self.extracted_info:
            return []

        element_dict = {'start_datetime':datetime.strptime(self.extracted_info['upload_date'], '%Y%m%d'),
                        'replay_source_purl': self.extracted_info['source_uri'],
                        'replay_source_file_ref': self.extracted_info['source_file_hash'],
                        'replay_source_file_name': self.extracted_info['source_file_name'],
                        'recording_agent': self.extracted_info['uploader'],
                        'title': self.extracted_info['fulltitle'],
                        'description': self.extracted_info['description']}

        citation = generate_cite_ref(PERF_CITE_REF, PERF_SCHEMA_VERSION, **element_dict)
        return citation, {}

    # Called when download is finished
    def wrap_up_extraction(self, d):
        if d['status'] == 'finished':
            filename = d['filename'].split('/')[-1].rpartition('.')[0] # Flimsy for now
            filename_with_ext = d['filename'].split('/')[-1]
            hash = save_file_to_store(os.path.join(TEMP_DIRECTORY, filename_with_ext))
            hash_dir = os.path.join(LOCAL_CITATION_DATA_STORE, hash)

            shutil.copy2(os.path.join(TEMP_DIRECTORY, "{}.description".format(filename)), hash_dir)
            shutil.copy2(os.path.join(TEMP_DIRECTORY, "{}.info.json".format(filename)), hash_dir)
            shutil.copy2(os.path.join(TEMP_DIRECTORY, "{}.annotations.xml".format(filename)), hash_dir)

            with open(os.path.join(TEMP_DIRECTORY, "{}.info.json".format(filename))) as json_file:
                info_json = json.load(json_file)

            extracted_info = {}
            extracted_info['source_uri'] = self.source.url
            extracted_info['source_file_hash'] = hash
            extracted_info['extracted_datetime'] = datetime.now(tz=pytz.utc).isoformat()
            extracted_info['source_file_name'] = filename_with_ext

            # Currently merging everything, might want to be more discriminate
            extracted_info = merge_dicts(info_json, extracted_info) # info_json['title'] -> extracted_info['title']

            # Clean up tmp directory
            shutil.rmtree(TEMP_DIRECTORY)

            # Signal complete
            self.extracted_info = extracted_info



class TwitchExtractor(Extractor):

    def extract(self, options=None):
        pass

    def validate(self):
        pass


class FM2Extractor(Extractor):
    supports_performances = True
    # Header information obtained from: http://www.fceux.com/web/FM2.html
    headers = (
        'version', 'emuVersion', 'rerecordCount', 'palFlag',
        'NewPPU', 'FDS', 'fourscore', 'port0', 'port1', 'port2',
        'binary', 'length', 'romFilename', 'comment', 'subtitle',
        'guid', 'romChecksum', 'savestate'
    )
    required = (
        'version', 'emuVersion', 'port0', 'port1', 'port2',
        'romFilename', 'guid', 'romChecksum'
    )

    def extract(self, options=None):
        extracted_info = {}

        # Open file to extract header information
        with open(self.source, 'r') as source_file:
            for line in source_file:
                try:
                    header, value = line.split(' ', 1)
                except ValueError:
                    # Reached input data, stop processing
                    break

                if header in FM2Extractor.headers:
                    if header == 'romChecksum':
                        # For some reason rom checksum is a base64 encoded MD5 hex
                        extracted_info['romChecksum_converted'] = base64.b64decode(value.split(':')[1]).encode('hex')
                        extracted_info['romChecksum'] = line.split(' ', 1)[1].replace('\n', '')
                    elif header in ('comment', 'subtitle'):
                        if header not in extracted_info:
                            extracted_info[header] = []
                        extracted_info[header].append(value)
                    else:
                        extracted_info[header] = line.split(' ', 1)[1].replace('\n', '') # Used for most fields

        extracted_info['title'] = self.source.split('/')[-1] # Just get non-pathed filename
        extracted_info['extracted_datetime'] = datetime.now(tz=pytz.utc).isoformat()
        extracted_info['source_file_hash'] = save_file_to_store(self.source)

        self.extracted_info = extracted_info

    # Just returns true, validating the file might be going overboard for now
    # We already check ext anyway
    def validate(self):
        return True


class GenericVideoExtractor(Extractor):
    supports_performances = True

    def extract(self, options=None):
        #   Need to import hachoir libraries in local scope because they overwrite sys.stdout / sys.stderr
        #   when imported, there is a configuration somewhere but I couldn't find it
        from hachoir_core.error import HachoirError
        from hachoir_parser import createParser
        from hachoir_metadata import extractMetadata

        extracted_info = {}

        filename = self.source.split('/')[-1]
        self.source = unicode(self.source)
        parser = createParser(self.source)
        if not parser:
            raise ExtractorError('Unable to parse file.')

        try:
            metadata = extractMetadata(parser)
        except HachoirError as e:
            raise ExtractorError('HachoirError: {}'.format(e.message))

        text = metadata.exportPlaintext()
        extracted_info['metadata_plain'] = text
        extracted_info['duration'] = metadata.get('duration').total_seconds()
        extracted_info['mime_type'] = metadata.get('mime_type')
        extracted_info['creation_date'] = metadata.get('creation_date').isoformat()
        extracted_info['last_modification'] = metadata.get('last_modification').isoformat()
        extracted_info['width'] = metadata.get('width')
        extracted_info['height'] = metadata.get('height')
        extracted_info['endian'] = metadata.get('endian')
        extracted_info['comments'] = metadata.getValues('comment')
        extracted_info['filename'] = filename
        extracted_info['title'] = filename.split('.')[0]

        extracted_info['source_file_hash'] = save_file_to_store(self.source)

        self.extracted_info = extracted_info

    #   Not much information from basic video files
    def create_citation(self):
        citation = generate_cite_ref(PERF_CITE_REF, PERF_SCHEMA_VERSION)
        citation['title'] = self.extracted_info['title']
        citation['replay_source_file_ref'] = self.extracted_info['source_file_hash']
        citation['start_datetime'] = self.extracted_info['creation_date']
        return citation, {}

    def validate(self):
        return True


#   ROM Extractors

def parse_ucon64_output(ucon64_buffer, headers, rom_source_index, info_start_index, k_v_index):
    parse_data = {}
    in_dat_info = False
    dat_count = 0
    for index, line in enumerate(ucon64_buffer.readlines()):
        if index < k_v_index:  # Non-keyed header lines
            if index == rom_source_index: parse_data['rom_image_source'] = line.strip()
            elif index == info_start_index: parse_data['platform'] = line.strip()
            elif index == info_start_index + 1: parse_data['title'] = line.strip()
            elif index == info_start_index + 2: parse_data['publisher'] = line.strip()
            elif index == info_start_index + 3: parse_data['localization_region'] = line.strip()
            elif index == info_start_index + 4: parse_data['rom_size'] = line.strip()
        elif len(line.strip()) > 0:           # in header lines or .dat file description
            key, value = line.split(':') if not in_dat_info else (None, None)
            if key in headers:
                # Check if in DAT info at end of file
                if key == 'DAT info':
                    in_dat_info = True
                    continue    # start counting dat lines on next iteration
                else:
                    parse_data[key] = value.strip()

            if in_dat_info:
                if dat_count == 1:
                    parse_data['rom_title'] = line.strip()
                elif dat_count == 4:
                    parse_data['dat_info'] = line.strip()
                dat_count += 1
    return parse_data



class SMCExtractor(Extractor):
    headers = ('Padded', r'Interleaved/Swapped', r'Backup unit/emulator header',
               'HiROM', 'Internal size', 'ROM type', 'ROM speed', 'SRAM',
               'Version', 'Checksum', 'Inverse checksum', r'Checksum (CRC32)',
               'DAT info')

    def extract(self, options=None):
        try:
            devnull = open(os.devnull)
            subprocess.Popen(['ucon64'], stdout=devnull, stderr=devnull).communicate()
        except OSError as e:
            if e.errno == os.errno.ENOENT:
                return ExtractorError("ucon64 not found, cannot extract {}".format(self.source))

        full_path = os.path.abspath(self.source)

        #   Prep Ucon64 and parse Ucon64 output
        proc = subprocess.Popen(['ucon64', full_path], stdout=subprocess.PIPE)
        parse_data = parse_ucon64_output(proc.stdout, self.headers, 6, 12, 18)

        #   Copy file information to appropriate extracted fields
        parse_data['version'] = parse_data['Version']
        parse_data['data_image_checksum'] = parse_data['Checksum (CRC32)']
        parse_data['data_image_checksum_type'] = 'crc32'

        #   Save rom data to game_data store
        parse_data['source_data'] = save_file_to_store(self.source, store_path=LOCAL_GAME_DATA_STORE)
        parse_data['data_image_source'] = full_path.split('/')[-1]
        self.extracted_info = parse_data

    def create_citation(self):
        citation = generate_cite_ref(GAME_CITE_REF, GAME_SCHEMA_VERSION)
        cite_map = (('Version', 'version'),
                    ('title', 'title'),
                    ('publisher', 'publisher'),
                    ('localization_region', 'localization_region'),
                    ('platform', 'platform'),
                    ('data_image_checksum', 'data_image_checksum'),
                    ('data_image_checksum_type', 'data_image_checksum_type'),
                    ('data_image_source', 'data_image_source'),
                    ('source_data', 'source_data'))
        for extract_key, schema_key in cite_map:
            citation[schema_key] = self.extracted_info[extract_key]

        return citation, {}

    #   Validates always since file name checked out
    def validate(self):
        return True


class NESExtractor(Extractor):
    headers = ('Padded', 'Interleaved/Swapped', 'Backup unit/emulator header',
               'Internal size', 'Internal PRG size', 'Internal CHR size',
               'Memory mapper (iNES)', 'Television standard', 'Mirroring',
               'Cartridge RAM', 'Save RAM', '512-byte trainer', 'VS-System',
               'Date', 'Checksum (CRC32)', 'DAT info')

    def extract(self, options=None):
        try:
            devnull = open(os.devnull)
            subprocess.Popen(['ucon64'], stdout=devnull, stderr=devnull).communicate()
        except OSError as e:
            if e.errno == os.errno.ENOENT:
                return ExtractorError("ucon64 not found, cannot extract {}".format(self.source))

        full_path = os.path.abspath(self.source)

        #   Prep Ucon64 and parse Ucon64 output
        proc = subprocess.Popen(['ucon64', full_path], stdout=subprocess.PIPE)
        parse_data = parse_ucon64_output(proc.stdout, self.headers, 8, 10, 16)

        #   Copy file information to appropriate extracted fields
        parse_data['data_image_checksum'] = parse_data['Checksum (CRC32)']
        parse_data['data_image_checksum_type'] = 'crc32'
        if 'Date' in parse_data:
            parse_data['date_published'] = datetime.strptime(parse_data['Date'], "%m/%Y").isoformat()
        else:
            parse_data['date_published'] = None

        #   Save rom data to game_data store
        parse_data['source_data'] = save_file_to_store(self.source, store_path=LOCAL_GAME_DATA_STORE)
        parse_data['data_image_source'] = full_path.split('/')[-1]
        self.extracted_info = parse_data

    def create_citation(self):
        citation = generate_cite_ref(GAME_CITE_REF, GAME_SCHEMA_VERSION)
        cite_map = (('title', 'title'),
                    ('publisher', 'publisher'),
                    ('localization_region', 'localization_region'),
                    ('platform', 'platform'),
                    ('data_image_checksum', 'data_image_checksum'),
                    ('data_image_checksum_type', 'data_image_checksum_type'),
                    ('data_image_source', 'data_image_source'),
                    ('date_published', 'date_published'),
                    ('source_data', 'source_data'))
        for extract_key, schema_key in cite_map:
            citation[schema_key] = self.extracted_info[extract_key]

        return citation, {}

    #   Again, if file extension works, then we're good for now
    def validate(self):
        return True

class Z64Extractor(Extractor):
    #   Apparently no date information in N64 dat files
    headers = ('Padded', 'Interleaved/Swapped', 'Backup unit/emulator header', 'Checksum',
               '2nd Checksum', 'Search checksum (CRC32)', 'Data checksum (CRC32)',
               'DAT info'
               )

    def extract(self, options=None):
        try:
            subprocess.call('ucon64')
        except OSError:
            return ExtractorError("ucon64 not found, cannot extract {}".format(self.source))

        full_path = os.path.abspath(self.source)

        proc = subprocess.Popen(['ucon64', full_path], stdout=subprocess.PIPE)
        parse_data = parse_ucon64_output(proc.stdout, self.headers, 6, 13, 19)

        parse_data['data_image_checksum'] = parse_data['Data checksum (CRC32)']
        parse_data['data_image_checksum_type'] = 'crc32'

        parse_data['source_data'] = save_file_to_store(self.source, store_path=LOCAL_GAME_DATA_STORE)
        parse_data['data_image_source'] = full_path.split('/')[-1]
        self.extracted_info = parse_data


    def create_citation(self):
        citation = generate_cite_ref(GAME_CITE_REF, GAME_SCHEMA_VERSION)
        cite_map = (('title', 'title'),
                    ('publisher', 'publisher'),
                    ('localization_region', 'localization_region'),
                    ('platform', 'platform'),
                    ('data_image_checksum', 'data_image_checksum'),
                    ('data_image_checksum_type', 'data_image_checksum_type'),
                    ('data_image_source', 'data_image_source'),
                    ('source_data', 'source_data'))
        for extract_key, schema_key in cite_map:
            citation[schema_key] = self.extracted_info[extract_key]

        return citation, {}

    def validate(self):
        return True

#   Directory Extractor
#   Used for games that are contained in a directory structure

class DirectoryExtractor(Extractor):

    def extract(self, options=None):
        dir_path = os.path.abspath(os.path.expanduser(self.source))
        files = []
        main_exe_set = False

        for d, subdirs, file_list in os.walk(dir_path):
            #   If at top of tree, relative directory is blank
            dir_relative_path = "/" if dir_path == d else d.replace(dir_path, "/")

            # check if hidden directory and skip
            if re.match("\.[a-zA-Z0-9]+", dir_relative_path):
                continue

            main_executable = options.get('main_executable')
            for f in file_list:
                file_dict = OrderedDict.fromkeys(dbm.headers[dbm.GAME_FILE_PATH_TABLE])
                #   check for hidden files and skip
                if f[0] == ".":
                    continue

                if main_executable and not main_exe_set and f == main_executable:
                    file_dict['is_executable'] = True
                    file_dict['main_executable'] = True
                    main_exe_set = True
                else:
                    if f.split('.')[-1] in ('EXE', 'exe'):
                        file_dict['is_executable'] = True
                        if not main_executable and not main_exe_set:    # set first executable you find as 'main' if not specified
                            file_dict['main_executable'] = True
                            main_exe_set = True

                #   File path is relative to source directory, so strip absolute path
                file_dict['file_path'] = os.path.join(dir_relative_path, f)
                #   Source data path is absolute, so leave it
                file_dict['source_data'] = save_file_to_store(os.path.join(d, f), LOCAL_GAME_DATA_STORE)
                files.append(file_dict)

        self.extracted_info = {"file_info": files}
            

    def create_citation(self):

        for fd in self.extracted_info['file_info']:
            pass


    def validate(self):
        return os.path.isdir(self.source)

#   Executable Extractor
#   Mainly for MS-DOS executables at this point