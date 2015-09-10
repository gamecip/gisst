__author__ = 'erickaltman'

import click
import cmd
import sys
import os
import json
import pprint
from database import DatabaseManager as dbm
from source_utils import (
    get_extractor_for_uri,
    get_extractor_for_file,
    get_uri_source_name,
    get_url_source,
    get_file_source_name,
    get_file_hash,
    SourceError
)
from extractors import local_extract_store

VERSION = '0.1'


@click.group()
@click.option('--verbose', is_flag=True)
@click.pass_context
def cli(ctx, verbose):
    ctx.obj = dict()    # Context object that stores application state in dict, could make class at some point
    ctx.obj['VERBOSE'] = verbose
    dbm.connect_to_db() # Connect to or create db


@cli.command()
@click.argument('uri')
@click.pass_context
def extract_uri(ctx, uri):
    verbose = ctx.obj['VERBOSE']
    check_for_extract_db_and_data()
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
    if has_potential_duplicates(source.url, 'source_uri'):
        if settle_for_duplicate(source.url, 'source_uri'):
            sys.exit(1)

    cond_print(verbose, 'Validating URI...')
    # Check if this is a game url for extraction
    if not extractor.validate():
        if not click.confirm('This doesn\'t appear to be a game related uri. Extract anyway?'):
            sys.exit(1)

    cond_print(verbose, 'Extracting URI...')
    # These are separate since file downloads might rely on subprocesses
    extractor.extract()

    # Block until extraction complete, needed for anything requiring sub-processes
    while not extractor.extracted_info:
        pass

    extracted_info = extractor.extracted_info

    if 'errors' not in extracted_info and add_to_extracted_database(extracted_info):
        cond_print(verbose, "Extraction Successful!")
        summary_prompt(extracted_info)
    else:
        cond_print(verbose, "Extraction Failed!")
        pprint.pprint(extracted_info)


# TODO: extract_file and extract_uri are incredibly similar, combine at some point
@cli.command()
@click.argument('path_to_file')
@click.pass_context
def extract_file(ctx, path_to_file):
    verbose = ctx.obj['VERBOSE']
    check_for_extract_db_and_data()
    source_name = get_file_source_name(path_to_file)

    # Convert to full path if needed
    full_path = os.path.join(os.getcwd(), path_to_file) if not os.path.isabs(path_to_file) else path_to_file

    # Check if there's actually a file there
    if not os.path.isfile(full_path):
        click.echo("There doesn\' appear to be a readable file at:{}.\nExiting.".format(path_to_file))
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
        if not click.confirm('This doesn\'t appear to be a game related uri. Extract anyway?'):
            sys.exit(1)


    # Check for duplicate entries, by hash of source file
    hash = get_file_hash(full_path)
    cond_print(verbose, 'Checking for duplicates...')
    if has_potential_duplicates(hash, 'source_file_hash'):
        if settle_for_duplicate(hash, 'source_file_hash'):
            sys.exit(1)

    cond_print(verbose, 'Extracting URI...')
    extractor.extract()
    extracted_info = extractor.extracted_info

    if 'errors' not in extracted_info and add_to_extracted_database(extracted_info):
        cond_print(verbose, "Extraction Successful!")
        summary_prompt(extracted_info)
    else:
        cond_print(verbose, "Extraction Failed!")
        pprint.pprint(extracted_info)


def cond_print(condition, message):
    if condition:
        click.echo(message)


def summary_prompt(info):
    while 1:
        show_info = prompt_input("Show info? (f)ull / (s)ummary / (n)o", ('f', 'F', 's', 'S', 'n', 'N'))
        if show_info in ('f','F'):
            click.echo(pprint.pformat(info, indent=2))
        elif show_info in ('s','S'):
            click.echo(pprint.pformat(info, indent=2, depth=1))
        break


def has_potential_duplicates(value, field):
    return dbm.is_attr_in_db(field, value, dbm.EXTRACTED_TABLE)


def get_duplicates(value, field):
    dup_tuples = dbm.retrieve_attr_from_db(field, value, dbm.EXTRACTED_TABLE)
    return [dict(zip(dbm.headers[dbm.EXTRACTED_TABLE], dup)) for dup in dup_tuples]


def settle_for_duplicate(value, field):
    dups = get_duplicates(value, field)
    while 1:
        answer = prompt_input('{} potential duplicates found. (v)iew / (i)gnore? / (q)uit?'.format(len(dups)),
                              ('V', 'v', 'I', 'i', 'Q', 'q'))
        if answer in ('V', 'v'):
            dup_list = ""
            for i, dup in enumerate(dups):
                dup_list += "{}) {} {} {}\n".format(i + 1, dup['title'], dup[field], dup['extracted_datetime'])
            while 1:
                click.echo(dup_list)
                c_s = 'Choose a number to view [{}], (c)ontinue extraction or (q)uit'.format('1-{}'.format(len(dups)) if len(dups) > 1 else '1')
                sel = prompt_input(c_s, ['C', 'c', 'Q', 'q'] + map(str, range(1, len(dups))))
                if sel in ('Q', 'q'):
                    break
                elif sel in map(str, range(1, len(dups))):
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
            click.echo('{} not a valid choice.')
            continue
        else:
            return s


def add_to_extracted_database(extracted_info):
    # This is currently tied to the exact ordering of headers in dbm.headers.EXTRACTED_TABLE
    # and is thus pretty flimsy, might need to change this management if our use-cases
    # end up requiring more complexity
    db_values = (None,    # None because primary key
                 extracted_info.get('title', None), # Need .get() since not all types will have each field
                 extracted_info.get('source_uri', None),
                 extracted_info.get('extracted_datetime', None),
                 extracted_info.get('source_file_hash', None),
                 json.dumps(extracted_info))  # 'metadata' field is just a string dump of the JSON extracted_info object

    insert_data = dbm.insert_into_table(dbm.EXTRACTED_TABLE, db_values)

    if not insert_data:
        click.echo("Error adding data to {}.".format(dbm.EXTRACTED_TABLE))

    return insert_data

# Currently assumes user will want this to be created
# TODO: allow user defined extracted data root
def check_for_extract_db_and_data():
    # Check for extracted data table
    if not dbm.check_for_table(dbm.EXTRACTED_TABLE):
        click.echo("Extracted data table not found, creating...")
        dbm.create_table(dbm.EXTRACTED_TABLE, dbm.fields[dbm.EXTRACTED_TABLE])

    # Check for extracted data directory
    if not os.path.exists(local_extract_store):
        click.echo("Local extract store: '{}' not found, creating...".format(local_extract_store))
        os.makedirs(local_extract_store)

# Needed for testing as script for debugging, not used when run as a command
if __name__ == '__main__':
    cli()