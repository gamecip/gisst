__author__ = 'erickaltman'

import click
import cmd
import sys
import os
import json
from uri_utils import get_source_name, process_game_uri, is_valid_uri
from file_utils import is_valid_file
from schema import print_cite_ref
from database import DatabaseManager as dbm



VERSION = '0.1'

# For interactive shell, might remove
local_context = dict()

class CitetoolShell(cmd.Cmd):

    def preloop(self):
        print "Starting up Citetool Editor shell"

    def do_quit(self, arg):
        pass

    def do_exit(self, arg):
        pass

    def postcmd(self, stop, line):
        if line in ('quit', 'exit'):
            return True

    def postloop(self):
        print "Exiting Citetool Editor shell, bye."


@click.group()
def cli():
    '''Command line tool for generating, retrieving, and converting of Citetool citation files'''
    pass

@cli.command()
def shell():
    '''Starts interactive shell'''
    cts = CitetoolShell()
    cts.prompt = '> '
    cts.cmdloop(intro='Welcome to the Citetool Editor Shell, v' + VERSION)

@cli.command()
@click.option('--export',
              default=os.getcwd(),
              help='Exports citation to local filesystem, defaults to cwd unless given a path')
@click.argument('uri_or_filename')
def generate(uri_or_filename, export):
    '''Generate metadata information and citation package data from source URI or video file'''
    if is_valid_uri(uri_or_filename):
        click.echo("Collecting information from {}".format(get_source_name(uri_or_filename)))
        extractor = process_game_uri(uri_or_filename)
        fill_in_elements(extractor)
        check_for_duplicate(extractor)
        create_citation_package(extractor, export=export)
    elif is_valid_file(uri_or_filename):
        pass
    else:
        click.echo("{} is not a valid input source".format(uri_or_filename))


def fill_in_elements(extractor):
    click.echo("Could not extract " + extractor.get_missing_element_names())
    click.echo(print_cite_ref(extractor.reference_object()))
    if click.confirm("Add more metadata?"):
        valid_elements = extractor.get_all_element_names()
        while 1:
            element_name = (click.prompt("Which element?")).replace(" ", "_").lowercase()
            if element_name in valid_elements:
                prop = getattr(extractor, element_name)
                value = click.prompt(prop.cli_message)
                if prop.validate(value):
                    extractor.add_element_value_pair(element_name, value)
                    click.echo(print_cite_ref(extractor.reference_object()))
                    if click.confirm("Add more metadata?"):
                        continue
                    else:
                        break
                else:
                    click.echo("Value {} not allowed for field {}.".format(value, element_name))

            else:
                click.echo("{} not a valid element name.")
                continue


def check_for_duplicate(extractor):
    dbm.connect_to_db()
    if dbm.is_game_in_db(extractor.title.value):
        if click.confirm("Found a match for title: {} in database. View?"):
            click.echo(print_cite_ref(extractor.reference_object()))
            if not click.confirm("Proceed with extraction anyway?"):
                sys.exit(1)


# Will expand this much in the future, for right now just outputs JSON to make sure this
# whole she-bang is working
def create_citation_package(extractor, export=None):

    if export:
        json.dump(extractor.reference_object().elements, export)

    dbm.insert_into_table(dbm.GAME_TABLE, extractor.reference_object().values)







