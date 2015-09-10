__author__ = 'erickaltman'
# Extractors
# Classes dealing with automatic extraction of information from urls, files, etc.


import bs4
from datetime import datetime
import pytz
import hashlib
import shutil
import os
import re
import requests
import json
import youtube_dl
from utils import (
    pairwise,
    pairwise_overlap,
    merge_dicts,
    replace_xa0,
    snake_case
)

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
    name_hash = hashlib.sha1(uri + dt).hexdigest()
    hash_dir = "{}/{}".format(local_extract_store, name_hash)

    # http://stackoverflow.com/questions/273192/in-python-check-if-a-directory-exists-and-create-it-if-necessary
    # Note that not perfect but effective for now
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

    if not os.path.exists(hash_dir):
        os.makedirs(hash_dir)

    #   Copies to directory with original filename
    shutil.copy2(file_path, hash_dir)
    return hash



# Game Citation Extractor listing one for each major citation source
# Includes extractor specific utility functions

class Extractor(object):

    def __init__(self, source):
        self.source = source
        self.extracted_info = None

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
        self.extracted_info = extracted_info

    # Currently searches for the "Category: XXXX video games" tag on a wiki page, where XXXX is a year
    # Every game page should have these, though could include a few more checks if this doesn't cover everything
    def validate(self):
        return re.search("Category:[0-9]{4} video games", self.source.text)

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

    def extract(self):

        # Figure out if specific or general url
        # /game/{platform}/{game name} is specific, otherwise /game/{game name}
        is_specific = re.search(r'http://www.mobygames.com/game/[a-z0-9]+/[a-z0-9\-]+', self.source.url)

        if is_specific:
            main_url = is_specific.group()
        else:
            main_url = re.search(r'http://www.mobygames.com/game/[a-z0-9\-]+', self.source.url).group()

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
        return re.search(r'www.mobygames.com/game/', self.source.url)

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
        if re.search(r'There are no credits for the', page_data.text) or re.search(r'The following releases of this game have credits', page_data.text):
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
    def get_page(uri):
        try:
            source = requests.get(uri)
        except BaseException as e:
            print e.message
            return None
        return source


class GiantBombExtractor(Extractor):

    def extract(self):
        pass

    def validate(self):
        pass


class YoutubeExtractor(Extractor):


    def extract(self):
        youtube_opts  = {
            'outtmpl': u'tmp/%(title)s.%(ext)s', # Template location for temporary file storage
            'writedescription': True, # Write description file to template location
            'writeinfojson': True, # Write JSON info file to template location
            'writeannotations': True, # Write Annotations XML file to template location
            'progress_hooks': [self.wrap_up_extraction], # Hook called on progress updates from youtube-dl process
            'ignoreerrors': True
        }

        # Create tmp directory if not present
        if not os.path.exists('tmp'):
            os.makedirs('tmp')

        # Call youtube_dl extraction process
        with youtube_dl.YoutubeDL(youtube_opts) as ydl:
            ydl.download([self.source.url])

    # No way to determine if a video is about a video game
    # Using youtube-dl regex to check, might change later
    def validate(self):
        import youtube_dl.extractor.youtube as youtube
        return re.search(youtube.YoutubeIE._VALID_URL, self.source.url)

    # Called when download is finished
    def wrap_up_extraction(self, d):
        if d['status'] == 'finished':
            filename = d['filename'].split('/')[1].split('.')[0] # Flimsy for now
            hash = save_file_to_extract_store('tmp/{}.mp4'.format(filename))
            hash_dir = '{}/{}'.format(local_extract_store, hash)

            shutil.copy2('tmp/{}.description'.format(filename), hash_dir)
            shutil.copy2('tmp/{}.info.json'.format(filename), hash_dir)
            shutil.copy2('tmp/{}.annotations.xml'.format(filename), hash_dir)

            with open('tmp/{}.info.json'.format(filename)) as json_file:
                info_json = json.load(json_file)

            extracted_info = {}
            extracted_info['source_uri'] = self.source.url
            extracted_info['source_file_hash'] = hash
            extracted_info['extracted_datetime'] = datetime.now(tz=pytz.utc).isoformat()

            # Currently merging everything, might want to be more discriminate
            extracted_info = merge_dicts(info_json, extracted_info) # info_json['title'] -> extracted_info['title']

            # Clean up tmp directory
            shutil.rmtree('tmp')

            # Signal complete
            self.extracted_info = extracted_info



class TwitchExtractor(Extractor):

    def extract(self):
        pass

    def validate(self):
        pass
