import click
import sys
import os
import json
import pprint
import shutil
import subprocess
from math import ceil
from database import DatabaseManager as dbm
from database import (
    LOCAL_CITATION_DATA_STORE,
    LOCAL_GAME_DATA_STORE,
    LOCAL_DATA_ROOT,
)
from utils import (
    coroutine,
    bound_array,
    clean_for_sqlite_query,
    merge_with_ordered_dict
)
from extractors import ExtractorError
from source_utils import (
    get_extractor_for_uri,
    get_extractor_for_file,
    get_extractor_for_directory,
    get_uri_source_name,
    get_url_source,
    get_file_source_name,
    get_file_hash,
    SourceError
)
from schema import (
    GAME_SCHEMA_VERSION,
    PERF_SCHEMA_VERSION,
    generate_cite_ref,
    GAME_CITE_REF,
    PERF_CITE_REF
)
from app import app

VERSION = '0.1'
__author__ = 'erickaltman'


@click.group()
@click.option('--verbose', is_flag=True, help='To everything that\'s going on.')
@click.option('--no_prompts', is_flag=True, help='Turn off all user prompts (use with care).')
@click.version_option(version=VERSION)
@click.pass_context
def cli(ctx, verbose, no_prompts):
    ctx.obj = dict()    # Context object that stores application state in dict, could make class at some point
    ctx.obj['VERBOSE'] = verbose
    ctx.obj['NO_PROMPTS'] = no_prompts
    #   Check for data root
    if not os.path.exists(LOCAL_DATA_ROOT):
        click.echo("Local data root not found, creating {}".format(LOCAL_DATA_ROOT))
        os.makedirs(LOCAL_DATA_ROOT)

    #   Check for fts lib
    if os.path.exists(dbm.FTS_EXT_PATH):
        pass
    else:
        if os.path.exists(os.path.dirname(os.path.abspath(__file__)) + "/fts5.dylib"):
            click.echo("Copying fts5.dylib to {}".format(LOCAL_DATA_ROOT))
            shutil.copy(os.path.dirname(os.path.abspath(__file__)) + "/fts5.dylib", LOCAL_DATA_ROOT)
        else:
            click.echo("Please put ft5.dylib into {} and run citetool-editor again.".format(LOCAL_DATA_ROOT))

    # Check for tables, extracted, game citation and performance citation
    dbm.create_tables()

    # Check for data directory
    for data_path, path_name in ((LOCAL_GAME_DATA_STORE, "game data"), (LOCAL_CITATION_DATA_STORE, "citation data")):
        if not os.path.exists(data_path):
            click.echo("Local {} store: '{}' not found, creating...".format(path_name, data_path))
            os.makedirs(data_path)


@cli.command(help='Run local access server for citations.')
@click.option('--port', help='Specify port for server. (default={}'.format(8100), default=8100)
def serve(port):
    app.run(port=port, debug=True, threaded=True)

@cli.command(help='Extract metadata from a compatible url.')
@click.argument('uri')
@click.pass_context
def extract_uri(ctx, uri):
    verbose = ctx.obj['VERBOSE']
    no_prompts = ctx.obj['NO_PROMPTS']
    source_name = get_uri_source_name(uri)
    if source_name:
        cond_print(verbose, "Starting extraction of {} source".format(source_name))
    else:
        click.echo("Could not find extractor for given uri:{}. Goodbye!".format(uri))
        sys.exit(1)

    try:
        source = get_url_source(uri)
    except SourceError as e:
        click.echo(e.message)
        sys.exit(1)

    extractor = get_extractor_for_uri(uri, source)
    cond_print(verbose, "Using {} for extraction".format(extractor.__class__.__name__))

    # Check for duplicate entries, by url from source, this is needed since there might be a redirect from the
    # input uri, like http -> https. Could check this in the extractor or tell the user that the url is changing.
    # Though if the redirect always happens it wouldn't matter anyway, since the database retains the redirected url
    cond_print(verbose, 'Checking for duplicates...')
    if not no_prompts and has_potential_duplicates(source.url, 'source_uri', dbm.EXTRACTED_TABLE):
        if settle_for_duplicate(source.url, 'source_uri', dbm.EXTRACTED_TABLE):
            sys.exit(1)

    cond_print(verbose, 'Validating URI...')
    # Check if this is a game url for extraction
    if not extractor.validate():
        if no_prompts or not click.confirm('This doesn\'t appear to be a game related uri. Extract anyway?'):
            sys.exit(1)

    cond_print(verbose, 'Extracting URI...')
    # These are separate since file downloads might rely on subprocesses
    extractor.extract()

    # Block until extraction complete, needed for anything requiring sub-processes
    while not extractor.extracted_info:
        pass

    extracted_info = extractor.extracted_info

    # Create citation from extracted information
    if no_prompts or click.confirm('Create citation from extracted data?'):
        citation, extracted_options = extractor.create_citation()
        if not no_prompts:
            citation = get_citation_user_input(citation, extracted_options)
            if citation.ref_type == GAME_CITE_REF:
                alternate_citation = choose_game_citation(search_locally_with_citation(citation))
            elif citation.ref_type == PERF_CITE_REF:
                alternate_citation = choose_performance_citation(search_locally_with_citation(citation))
            if not alternate_citation:
                dbm.add_to_citation_table(citation, fts=True)
                click.echo('Citation added to database.')
        else:
            dbm.add_to_citation_table(citation, fts=True)

    if 'errors' not in extracted_info and dbm.add_to_extracted_table(extracted_info):
        cond_print(verbose, "Extraction Successful!")
        if not no_prompts:
            summary_prompt(extracted_info)
    else:
        cond_print(verbose, "Extraction Failed!")
        pprint.pprint(extracted_info)


# TODO: extract_file and extract_uri are incredibly similar, combine at some point
@cli.command(help='Extract metadata from a compatible file.')
@click.argument('path_to_file')
@click.option('--partial_citation', help='JSON partial with descriptive fields for extracted citation.')
@click.pass_context
def extract_file(ctx, path_to_file, partial_citation):
    verbose = ctx.obj['VERBOSE']
    no_prompts = ctx.obj['NO_PROMPTS']
    source_name = get_file_source_name(path_to_file)

    # Convert to full path if needed
    full_path = os.path.join(os.getcwd(), path_to_file) if not os.path.isabs(path_to_file) else path_to_file

    # Check if there's actually a file there
    if not os.path.isfile(full_path):
        click.echo("There doesn\'t appear to be a readable file at:{}.\nExiting.".format(path_to_file))
        sys.exit(1)

    # Check if it's actually a potentially valid source
    if source_name:
        cond_print(verbose, "Starting extraction of {} source".format(source_name))
    else:
        click.echo("Could not find extractor for given file path:{}. Goodbye!".format(path_to_file))
        sys.exit(1)

    # Get the appropriate extractor
    extractor = get_extractor_for_file(full_path)
    cond_print(verbose, "Using {} for extraction".format(extractor.__class__.__name__))

    # Check if this is a valid file
    cond_print(verbose, 'Validating File...')
    if not extractor.validate():
        if no_prompts or click.confirm('This doesn\'t appear to be a game related file. Extract anyway?'):
            sys.exit(1)

    # Check for duplicate entries, by hash of source file
    file_hash = get_file_hash(full_path)
    cond_print(verbose, 'Checking for duplicates...')
    if not no_prompts and has_potential_duplicates(file_hash, 'source_file_hash', dbm.EXTRACTED_TABLE):
        if settle_for_duplicate(file_hash, 'source_file_hash', dbm.EXTRACTED_TABLE):
            sys.exit(1)

    cond_print(verbose, 'Extracting URI...')
    try:
        extractor.extract()
    except ExtractorError as e:
        click.echo(e.message)
        sys.exit(1)

    extracted_info = extractor.extracted_info

    if no_prompts or click.confirm('Create citation from extracted data?'):
        citation, extracted_options = extractor.create_citation()
        if partial_citation:
            partial = json.loads(partial_citation)
            citation.elements = merge_with_ordered_dict(partial['description'], citation.elements)
        if not no_prompts:
            citation = get_citation_user_input(citation, extracted_options)
            if citation.ref_type == GAME_CITE_REF:
                alternate_citation = choose_game_citation(search_locally_with_citation(citation))
            elif citation.ref_type == PERF_CITE_REF:
                alternate_citation = choose_performance_citation(search_locally_with_citation(citation))
            if not alternate_citation:
                dbm.add_to_citation_table(citation, fts=True)
                cond_print(verbose, 'Citation added to database.')
        else:
            dbm.add_to_citation_table(citation, fts=True)

    if 'errors' not in extracted_info and dbm.add_to_extracted_table(extracted_info):
        cond_print(verbose, "Extraction Successful!")
        if not no_prompts:
            summary_prompt(extracted_info)
    else:
        cond_print(verbose, "Extraction Failed!")
        pprint.pprint(extracted_info)

#   TODO: merge both citation functions into one
@cli.command(help='Create a game citation.')
@click.option('--export', help='Return citation JSON string.', is_flag=True)
@click.option('--file_path', help='Create citation from local file.')
@click.option('--directory', help='Create citation from local directory.')
@click.option('--executable', help='Specify executable for --directory flag')
@click.option('--url', help='Create citation from url.')
@click.option('--title', help='Create citation from game title.')
@click.option('--partial', help='Create citation from partial JSON record.')
@click.option('--schema_version', help='Specify schema version (default={}).'.format(GAME_SCHEMA_VERSION),
              default=GAME_SCHEMA_VERSION)
@click.pass_context
def cite_game(ctx, file_path, directory, executable, url, title, partial, export, schema_version):
    verbose = ctx.obj['VERBOSE']
    no_prompts = ctx.obj['NO_PROMPTS']
    alternate_citation = None

    # Make sure that only one input flag is used
    if sum(map(lambda x: 1 if x else 0, [file_path, url, title, partial])) > 1:
        click.echo('Please use only one option for citation source data.')
        click.echo('Usage:\n\tcite --file_path PATH_TO_FILE\n\tcite --url URL\n\tcite --title TITLE\n\tcite --partial JSON_OBJECT')
        sys.exit(1)

    # if no input flag
    if not file_path and not url and not title and not partial and not directory:
        # Make a brand new citation
        if no_prompts:
            cond_print(verbose, 'Cannot create a blank citation with no-prompts flag active.')
            sys.exit(1)
        cond_print('Creating new citation...\n', verbose)
        citation = get_citation_user_input(generate_cite_ref(GAME_CITE_REF, schema_version))
        cond_print('Searching for similar citations...\n', verbose)
        # Check for similar citations
        alternate_citation = choose_game_citation(search_locally_with_citation(citation))

    #   FILE PATH citation
    if file_path:
        extractor = get_extractor_for_file(os.path.expanduser(file_path))
        extractor.extract()
        citation, extracted_options = extractor.create_citation()
        if not no_prompts:
            citation = get_citation_user_input(citation, extracted_options)
            alternate_citation = choose_game_citation(search_locally_with_citation(citation))

    #   DIRECTORY citation
    elif directory:
        extractor = get_extractor_for_directory(os.path.abspath(os.path.expanduser(directory)))
        alternate_citation = None   #   Needed to make sure name is present for check below

        #   Make sure this is a directory
        if not extractor.validate():
            click.echo('{} is not a valid directory.'.format(directory))
            sys.exit(1)

        #   Add in the executable path if provided
        options = {}
        if executable:
            options['main_executable'] = executable

        #   If there's additional information from a partial, load it
        if partial:
            partial_json = json.loads(partial)
            citation = generate_cite_ref(GAME_CITE_REF, GAME_SCHEMA_VERSION, **partial_json['description'])
        else:
            citation = generate_cite_ref(GAME_CITE_REF, GAME_SCHEMA_VERSION, title=directory.split('/')[-1])

        #   Get input if prompts are allowed
        if not no_prompts:
            citation = get_citation_user_input(citation)
            alternate_citation = choose_citation(search_locally_with_citation(citation))

        #   Extract all the files and paths
        extractor.extract(options=options)

        #   Add file_paths to game data store if this is a new citation
        file_info = extractor.extracted_info['file_info']
        if not alternate_citation:
            for fd in file_info:
                fd['game_uuid'] = citation['uuid']
                dbm.insert_into_table(dbm.GAME_FILE_PATH_TABLE, fd.keys(), fd.values())
        else:
        #   Clean up extracted data if alternate citation found (only for prompts call)
            for fd in file_info:
                shutil.rmtree(os.path.join(LOCAL_GAME_DATA_STORE, fd['source_data'], fd['file_path'].split('/')[-1]))

    #   URL citation
    elif url:
        try:
            source = get_url_source(url)
        except SourceError as e:
            click.echo(e.message)
            sys.exit(1)

        extractor = get_extractor_for_uri(url, source)
        extractor.extract()
        # Block if this is a link to a video or other extractor process
        while not extractor.extracted_info:
            pass
        citation, extracted_options = extractor.create_citation()
        if not no_prompts:
            citation = get_citation_user_input(citation, extracted_options)
            alternate_citation = choose_game_citation(search_locally_with_citation(citation))

    #   TITLE citation
    elif title:
        if no_prompts:
            cond_print(verbose, 'Cannot do citation by title with no-prompts flag active.')
            sys.exit(1)
        # Try a local citation search
        alternate_citation = choose_game_citation(search_locally_with_game_title(title))
        citation = None

        # If that didn't work try to search internet
        # Current hard-coded limit as 10, may allow flag for future
        if not alternate_citation:
            citation = choose_game_citation(search_globally_with_game_title(title, limit=10))

        # If that didn't work, make a new citation
        if not citation and not alternate_citation:
            citation = generate_cite_ref(GAME_CITE_REF,
                                         GAME_SCHEMA_VERSION,
                                         title=title)
            # Edit the citation if needed
            citation = get_citation_user_input(citation)

    #   PARTIAL citation
    elif partial:
        partial_json = json.loads(partial)
        # Create citation based on partial description
        citation = generate_cite_ref(GAME_CITE_REF, GAME_SCHEMA_VERSION, **partial_json['description'])

        if not no_prompts:
            # Search locally based on partial description
            alternate_citation = choose_game_citation(search_locally_with_citation(citation))
            # Search globally if that didn't work
            if not alternate_citation:
                citation = choose_game_citation(search_globally_with_game_partial(partial_json))

    # If an alternate was found, don't do anything
    if alternate_citation:
        citation = alternate_citation
    else:
        # Add the new citation to the database
        if citation:
            dbm.add_to_citation_table(citation, fts=True)

    if export and citation:
        click.echo(citation.to_json_string())


@cli.command(help='Create a performance citation.')
@click.option('--export', help='Return citation JSON string.', is_flag=True)
@click.option('--file_path', help='Create citation from local file.')
@click.option('--url', help='Create citation from url.')
@click.option('--partial', help='Create citation from partial JSON record.')
@click.option('--schema_version', help='Specify schema version.', default=GAME_SCHEMA_VERSION)
@click.pass_context
def cite_performance(ctx, export, file_path, url, partial, schema_version):
    verbose = ctx.obj['VERBOSE']
    no_prompts = ctx.obj['NO_PROMPTS']
    alternate_citation = None

    # Make sure that only one input flag is used
    if sum(map(lambda x: 1 if x else 0, [file_path, url, partial])) > 1:
        click.echo('Please use only one option for citation source data.')
        click.echo('Usage:\n\t{} --file_path PATH_TO_FILE\n\t{} --url URL\n\t{} --partial JSON_OBJECT'.format('cite_performance'))
        sys.exit(1)

    if not file_path and not url and not partial:
        if no_prompts:
            cond_print(verbose, 'Cannot create a blank citation with no-prompts flag active.')
        cond_print(verbose, 'Creating a new citation...')
        citation = get_citation_user_input(generate_cite_ref(PERF_CITE_REF, PERF_SCHEMA_VERSION))
        cond_print(verbose, 'Searching for similar citations...')
        alternate_citation = choose_performance_citation(search_locally_with_citation(citation))

    if file_path:
        extractor = get_extractor_for_file(os.path.expanduser(file_path))
        extractor.extract()
        citation, extracted_options = extractor.create_citation()
        if not no_prompts:
            citation = get_citation_user_input(citation, extracted_options)
            alternate_citation = search_locally_with_citation(citation)
    elif url:
        try:
            source = get_url_source(url)
        except SourceError as e:
            click.echo(e.message)
            sys.exit(1)
        extractor = get_extractor_for_uri(url, source)
        extractor.extract()
        #   Block while waiting for extraction to finish, necessary for video downloads
        while not extractor.extracted_info:
            pass
        citation, extracted_options = extractor.create_citation()
        if not no_prompts:
            citation = get_citation_user_input(citation, extracted_options)
            alternate_citation = choose_game_citation(search_locally_with_citation(citation))
    elif partial:
        partial_json = json.loads(partial)
        # Create citation based on partial description
        citation = generate_cite_ref(PERF_CITE_REF, PERF_SCHEMA_VERSION, **partial_json['description'])
        # Search locally based on partial description
        if not no_prompts:
            alternate_citation = choose_performance_citation(search_locally_with_citation(citation))

    if alternate_citation:
        citation = alternate_citation
    else:
        if citation:
            dbm.add_to_citation_table(citation, fts=True)

    if export and citation:
        click.echo(citation.to_json_string())


@cli.command(help='Search for citations with a game partial.')
@click.argument('partial_description')
@click.option('--game_only', help='Limit search to game citations.', is_flag=True)
@click.option('--perf_only', help='Limit search to performance citations.', is_flag=True)
@click.pass_context
def search(ctx, partial_description, game_only, perf_only):
    no_prompts = ctx.obj['NO_PROMPTS']

    if game_only and perf_only:
        click.echo('Choose either game_only or perf_only flags, not both')
        sys.exit(1)

    partial_dict = json.loads(partial_description)
    #   For now we are assuming that we will not want to search the extracted data sets
    if game_only:
        exclude_refs = ('performance', 'extracted')
    elif perf_only:
        exclude_refs = ('game', 'extracted')
    else:
        exclude_refs = ('extracted',)

    results = search_locally_with_partial(partial_dict, exclude_ref_types=exclude_refs)

    results_dict = prep_search_results(results)

    if no_prompts:
        click.echo(json.dumps(results_dict))
    else:
        if not results and not perf_only:
            if click.confirm('No results found, search online sources for games?'):
                citations = search_globally_with_game_partial(partial_dict)
                results_dict = dict()
                results_dict['games'] = [c.elements for c in citations]
                results_dict['total_records_found'] = len(citations)
                results_dict['total_game_records'] = len(citations)
                click.echo(json.dumps(results_dict))
        else:
            click.echo(json.dumps(results_dict))


@cli.command(help='Create a gif from a performance citation.')
@click.argument('uuid')
@click.argument('start', type=int)
@click.argument('end', type=int)
@click.option('--regenerate', help='Force regeneration even if extract already present.', is_flag=True)
@click.pass_context
def gif_performance(ctx, uuid, start, end, regenerate):
    verbose = ctx.obj['VERBOSE']
    #   Peformance retrieval
    perf = dbm.retrieve_perf_ref(uuid)

    if not perf:
        click.echo('Invalid performance uuid: {}'.format(uuid))
        sys.exit(1)

    cond_print(verbose, "Found performance: {}, '{}'".format(uuid, perf['title']))

    #   GIF creation
    gif_source_path = "'{}/{}/{}'".format(os.path.abspath(LOCAL_CITATION_DATA_STORE),
                                          perf['replay_source_file_ref'],
                                          perf['replay_source_file_name'])
    gif_segment_dir = "{}_{}".format(start, end)
    gif_abs_path = "{}/{}/gif/{}".format(os.path.abspath(LOCAL_CITATION_DATA_STORE),
                                         perf['replay_source_file_ref'],
                                         gif_segment_dir)
    gif_palette_name = "{}_{}_{}_palette.png".format(uuid, start, end)
    gif_file_name = "{}_{}_{}.gif".format(uuid, start, end)

    #   All commands are just straight defaults for now, basic settings are:
    #   FPS: 10
    #   Height: 320
    #   Width: Scale to height
    ffmpeg_palette = '/usr/local/bin/ffmpeg -y -ss {} -t {} -i {} -vf fps=10,scale=320:-1:flags=lanczos,palettegen {}'.format(
        start,
        end - start,
        gif_source_path,
        "'{}/{}'".format(gif_abs_path, gif_palette_name)
    )
    ffmpeg_gif = '/usr/local/bin/ffmpeg -ss {} -t {} -i {} -i {} -filter_complex "fps=10,scale=320:-1:flags=lanczos[x];[x][1:v]paletteuse" {}'.format(
        start,
        end - start,
        gif_source_path,
        "'{}/{}'".format(gif_abs_path, gif_palette_name),
        "'{}/{}'".format(gif_abs_path, gif_file_name)
    )

    #   Check if gif is already present, and remove if regenerate flag is set
    if os.path.isdir(gif_abs_path) and regenerate:
        cond_print(verbose, "--regenerate flag active, deleting previous gif information")
        shutil.rmtree(gif_abs_path)
    elif os.path.isdir(gif_abs_path):
        click.echo('Gif for that time index already present, please use --regenerate to override this message.')
        sys.exit(1)

    #   Create gif directory
    cond_print(verbose, "Creating gif directory at {}".format(gif_abs_path))
    os.makedirs(gif_abs_path)

    #   Run gif creation processes
    cond_print(verbose, "Running gif creation processes...")
    cond_print(verbose, "{}".format(ffmpeg_palette))
    try:
        subprocess.check_call(ffmpeg_palette, shell=True)
    except subprocess.CalledProcessError as e:
        click.echo(e.message)
        sys.exit(1)

    cond_print(verbose, "{}".format(ffmpeg_gif))
    try:
        subprocess.check_call(ffmpeg_gif, shell=True)
    except subprocess.CalledProcessError as e:
        click.echo(e.message)
        sys.exit(1)

    cond_print(verbose, "Success!")


def prep_search_results(results):

    def make_performance_package(performance):
        pack = {}
        game = dbm.retrieve_game_ref(performance['game_uuid'])
        pack['game'] = game.elements if game else None
        pack['performance'] = performance.elements
        #   Last performance is current performance
        pack['previous_performances'] = [i.elements for i in dbm.retrieve_performance_chain(performance['uuid'])[:-1]]
        return pack

    results_dict = dict()
    results_dict['games'] = [c.elements for c in results if c.ref_type == GAME_CITE_REF]
    results_dict['performances'] = [p for p in map(make_performance_package,
                                                   [x for x in results if x.ref_type == PERF_CITE_REF])]
    results_dict['total_game_records'] = len(results_dict['games'])
    results_dict['total_performance_records'] = len(results_dict['performances'])
    results_dict['total_records'] = len(results)
    return results_dict


def get_citation_user_input(citation_object, extracted_options=None):
    if extracted_options:
        for opt in extracted_options:
            while 1:
                values = extracted_options[opt]
                sel_nums = map(str, range(1, len(values)))
                click.echo('There are multiple options for {}.'.format(opt))
                for i, o in enumerate(values):
                    click.echo('{}. {}'.format(i + 1, o))
                selection = prompt_input('Choose a value or (m)erge values or (c)reate new value.',
                                         ['m', 'M', 'c', 'C'] + sel_nums)
                if selection in sel_nums:
                    citation_object[opt] = values[int(selection) - 1]
                elif selection in ('m', 'M'):
                    citation_object[opt] = " | ".join(values)
                elif selection in ('c', 'C'):
                    value = click.prompt('New value for {}'.format(opt))
                    citation_object[opt] = value
                break
    if click.confirm('Would you like to view the current citation?'):
        while 1:
            click.echo(citation_object.to_pretty_string())
            selection = prompt_input('Choose a field to edit or (c)ontinue with this citation',
                                     list(citation_object.get_element_names()) + ['c', 'C'])
            if selection in ('c', 'C'):
                break
            else:
                value = click.prompt('Please enter new value for {}'.format(selection))
                citation_object[selection] = value
    return citation_object


def search_locally_with_citation(citation):
    comb = zip(citation.get_element_names(exclude=('uuid', 'source_data', 'source_url')),
               citation.get_element_values(exclude=('uuid', 'source_data', 'source_url')))
    partial = dict(start_index=0,
                   description=dict([(e, v) for e, v in comb if e not in citation.get_missing_elements()]))
    if citation.ref_type == GAME_CITE_REF:
        result = search_locally_with_game_partial(partial)
    elif citation.ref_type == PERF_CITE_REF:
        result = search_locally_with_performance_partial(partial)
    return result


def search_locally_with_partial(partial, exclude_ref_types=None):
    start_index = int(partial['start_index'])
    limit = int(partial['limit']) if 'limit' in partial else None
    #   Apparently Python DB API and Sqlite and commas (,), parans ((,)), and colons (:) do not play nice with FTS?
    search_strings = [clean_for_sqlite_query(unicode(v)) for k, v in partial['description'].items()]
    source_index = dbm.headers[dbm.FTS_INDEX_TABLE].index('source_type')
    uuid_index = dbm.headers[dbm.FTS_INDEX_TABLE].index('uuid')

    if not exclude_ref_types:
        results = dbm.retrieve_from_fts(search_strings, start_index=start_index, limit=limit)
    else:
        results = [x for x in dbm.retrieve_from_fts(search_strings) if x[source_index] not in exclude_ref_types]

    def get_cite_for_result(result):
        ref_type = result[source_index]
        uuid = result[uuid_index]
        if ref_type == GAME_CITE_REF:
            table = dbm.GAME_CITATION_TABLE
        if ref_type == PERF_CITE_REF:
            table = dbm.PERFORMANCE_CITATION_TABLE

        db_values = dbm.retrieve_attr_from_db('uuid', uuid, table, limit=1)[0]
        citation = dbm.create_cite_ref_from_db(ref_type, db_values)
        return citation

    # Results should already be sorted by rank
    citations = map(get_cite_for_result, results)
    # Results not already limited if there were exclusions
    if exclude_ref_types:
        return bound_array(citations, start_index=start_index, limit=limit)
    return citations


def search_locally_with_game_partial(game_partial):
    return search_locally_with_partial(game_partial, exclude_ref_types=(PERF_CITE_REF, 'extracted', 'state', 'battery'))


def search_locally_with_performance_partial(perf_partial):
    return search_locally_with_partial(perf_partial, exclude_ref_types=(GAME_CITE_REF, 'extracted', 'state', 'battery'))


def search_locally_with_game_title(title):
    partial = {'description': {'title': title}, 'start_index': 0}
    return search_locally_with_game_partial(partial)


def search_globally_with_game_title(title, limit=None):
    partial = {'description': {'title': title}, 'start_index': 0}
    if limit:
        partial['limit'] = limit
    return search_globally_with_game_partial(partial)


def search_globally_with_game_partial(citation_partial):
    citations = []
    NEW = 'new'
    OLD = 'old'

    @coroutine
    def process_citation_url():
        while True:
            url = (yield)
            if not dbm.is_attr_in_db('source_url', url, dbm.GAME_CITATION_TABLE):
                click.echo('Extracting url {} through coroutine.'.format(url))
                extractor = get_extractor_for_uri(url, get_url_source(url))
                extractor.extract()
                citation, extracted_options = extractor.create_citation()
                citations.append((citation, NEW))
            else:
                click.echo('Found {} in local db.'.format(url))
                citation = dbm.create_cite_ref_from_db(GAME_CITE_REF,
                                                       dbm.retrieve_attr_from_db(
                                                           'source_url',
                                                           url,
                                                           dbm.GAME_CITATION_TABLE)[0])
                citations.append((citation, OLD))

    #   Currently this search is only through MobyGames, may work on federated search
    #   in the future. Also only searches on title for now
    #   Just need the extractor, don't need its state
    search_string = citation_partial['description']['title']
    limit = citation_partial['limit'] if 'limit' in citation_partial else None
    search_uris = get_extractor_for_uri('http://www.mobygames.com', None).get_search_uris(search_string)

    if limit and limit <= len(search_uris) - 1:
        search_uris = search_uris[:limit]

    # Process coroutine
    # Send uris to coroutine generator
    for uri in search_uris:
        process_citation_url().send(uri)

    #   Block until all the search citations return
    while len(citations) != len(search_uris):
        pass

    for c in citations:
        if c[1] == NEW:
            dbm.add_to_citation_table(c[0], fts=True)

    return [c for c, _ in citations]


def choose_game_citation(citations):
    return choose_citation(citations, cite_fields=('title', 'platform', 'version', 'copyright_year'))


def choose_performance_citation(citations):
    return choose_citation(citations, cite_fields=('title', 'description', 'performer'))


def choose_citation(citations, cite_fields=None):
    if citations:
        pagination_limit = 10
        current_page = 0
        citation = None
        num_cites = len(citations)
        max_page = max(int(ceil(num_cites * 1.0 / pagination_limit)) - 1, 0)
        click.echo('{} possibly relevant citation{} found.'.format(num_cites, 's' if num_cites != 1 else ''))
        while 1:
            min_bound = current_page * pagination_limit
            max_bound = min(num_cites, (current_page + 1) * pagination_limit)
            selection_numbers = map(str, range(min_bound + 1, max_bound + 1))
            click.echo('Showing entries {}-{} of {}'.format(min_bound + 1, max_bound, num_cites))
            for i, c in enumerate(citations[min_bound:max_bound]):
                index = i + 1 if current_page == 0 else i + min_bound + 1
                click.echo('{}. {} {} {}'.format(index, *[c[field] for field in cite_fields]))
            selection = prompt_input('Choose a number, (n)ext page, (p)revious page, or (q)uit.',
                                     ['n', 'N', 'p', 'P', 'q', 'Q'] + selection_numbers)
            if selection in selection_numbers:
                citation = citations[int(selection) - 1]
                click.echo(citation.to_pretty_string())
                if click.confirm('Use this citation?'):
                    break
            elif selection in ('n', 'N'):
                current_page = min(current_page + 1, max_page)
            elif selection in ('p', 'P'):
                current_page = max(current_page - 1, 0)
            elif selection in ('q', 'Q'):
                break
        return citation
    return None


def cond_print(condition, message):
    if condition:
        click.echo(message)


def summary_prompt(info):
    while 1:
        show_info = prompt_input("Show info? (f)ull / (s)ummary / (n)o", ('f', 'F', 's', 'S', 'n', 'N'))
        if show_info in ('f', 'F'):
            click.echo(pprint.pformat(info, indent=2))
        elif show_info in ('s', 'S'):
            click.echo(pprint.pformat(info, indent=2, depth=1))
        break


def has_potential_duplicates(value, field, table_name):
    return dbm.is_attr_in_db(field, value, table_name)


def get_duplicates(value, field, table_name):
    dup_tuples = dbm.retrieve_attr_from_db(field, value, table_name)
    return [dict(zip(dbm.headers[table_name], dup)) for dup in dup_tuples]


def settle_for_duplicate(value, field, table_name):
    dups = get_duplicates(value, field, table_name)
    while 1:
        answer = prompt_input('{} potential duplicate{} found. (v)iew / (i)gnore? / (q)uit?'.format(
            len(dups),
            's' if not len(dups) == 1 else ''),
            ('V', 'v', 'I', 'i', 'Q', 'q')
        )

        if answer in ('V', 'v'):
            dup_list = ""
            for i, dup in enumerate(dups):
                dup_list += "{}) {} {} {}\n".format(i + 1, dup['title'], dup[field], dup['extracted_datetime'])
            while 1:
                click.echo(dup_list)
                sel_indices = map(str, range(1, len(dups) + 1))
                c_s = 'Choose a number to view [{}], (c)ontinue extraction or (q)uit'.format(
                    '1-{}'.format(len(dups)) if len(dups) > 1 else '1')
                sel = prompt_input(c_s, ['C', 'c', 'Q', 'q'] + sel_indices)
                if sel in ('Q', 'q'):
                    break
                elif sel in sel_indices:
                    click.echo(pprint.pprint(json.loads(dups[int(sel) - 1]['metadata']), indent=2))
                    if click.confirm('View another?'):
                        continue
                    else:
                        s = prompt_input('(Q)uit or (c)ontinue extraction', ('Q', 'q', 'C', 'c'))
                        if s in ('Q', 'q'):
                            return True
                return False
            return True
        elif answer in ('Q', 'q'):
            return True
        else:
            return False


def prompt_input(prompt_text, options):
    while 1:
        s = click.prompt(prompt_text)
        if s not in options:
            click.echo('"{}" not a valid choice.'.format(s))
            continue
        else:
            return s

@cli.command(help='Clear local data')
@click.option('--ignore_game_data', help="Clear everything but local game data files.")
@click.pass_context
def clear(ctx, ignore_game_data):
    no_prompts = ctx.obj['NO_PROMPTS']

    if no_prompts:
        clear_local_data(ignore_game_data)
    else:
        conf_message = "all" if not ignore_game_data else "all citation"
        if click.confirm("Warning: This will erase {} data. Are you sure? ".format(conf_message)):
            clear_local_data(ignore_game_data)


def clear_local_data(ignore_game_data=False):
    if os.path.exists(LOCAL_DATA_ROOT):
        if ignore_game_data:
            try:
                shutil.rmtree(LOCAL_CITATION_DATA_STORE)
            except OSError as e:
                click.echo(e.message)

            dbm.delete_db()
        else:
            try:
                shutil.rmtree(LOCAL_DATA_ROOT)
            except OSError as e:
                click.echo(e.message)
    else:
        click.echo("No local data found, exiting.")

# Needed for testing as script for debugging, not used when run as a command
if __name__ == '__main__':
    cli()