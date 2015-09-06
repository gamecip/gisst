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
    get_uri_source_name,
    get_url_source,
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
    cond_print(verbose, "Starting extraction of {} source".format(get_uri_source_name(uri)))

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
    if has_potential_duplicates(source.url):
        if settle_for_duplicate(source.url):
            sys.exit(1)

    cond_print(verbose, 'Validating URI...')
    # Check if this is a game url for extraction
    if not extractor.validate():
        if not click.confirm('This doesn\'t appear to be a game related uri. Extract anyway?'):
            sys.exit(1)

    extracted_info = extractor.extract()

    if 'errors' not in extracted_info:
        # This is currently tied to the exact ordering of headers in dbm.headers.EXTRACTED_TABLE
        # and is thus pretty flimsy, might need to change this management if our use-cases
        # end up requiring more complexity
        db_values = (None,    # None because primary key
                     extracted_info['title'],
                     extracted_info['source_uri'],
                     extracted_info['extracted_datetime'],
                     extracted_info['source_file_hash'],
                     json.dumps(extracted_info))  # 'metadata' field is just a string dump of the JSON extracted_info object


        if not dbm.insert_into_table(dbm.EXTRACTED_TABLE, db_values):
            click.echo("Error adding data to {}.".format(dbm.EXTRACTED_TABLE))

        cond_print(verbose, "Extraction Successful!")
        summary_prompt(extracted_info)
    else:
        pprint.pprint(extracted_info)




@cli.command()
@click.argument('path_to_file')
@click.pass_context
def extract_file(ctx, path_to_file):
    verbose = ctx.obj['VERBOSE']


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


def has_potential_duplicates(uri):
    return dbm.is_attr_in_db('source_uri', uri, dbm.EXTRACTED_TABLE)


def get_duplicates(uri):
    dup_tuples = dbm.retrieve_attr_from_db('source_uri', uri, dbm.EXTRACTED_TABLE)
    return [dict(zip(dbm.headers[dbm.EXTRACTED_TABLE], dup)) for dup in dup_tuples]


def settle_for_duplicate(uri):
    dups = get_duplicates(uri)
    while 1:
        answer = prompt_input('{} potential duplicates found. (v)iew / (i)gnore?'.format(len(dups)), ('V', 'v', 'I', 'i'))
        if answer in ('V', 'v'):
            dup_list = ""
            for i, dup in enumerate(dups):
                dup_list += "{}) {} {} {}\n".format(i + 1, dup['title'], dup['source_uri'], dup['extracted_datetime'])
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


# Current assumes user will want this to be created
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


if __name__ == '__main__':
    cli()