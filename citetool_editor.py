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
        extractor = get_extractor_for_uri(uri_or_filename)

        # Extract metadata from source uri that is not tied to addition file processing
        extractor.extract_metadata()

        # Many URLs aggregate games by platform and region if there are many versions
        if extractor.has_multiple_refs():
            ref = choose_ref(extractor.get_refs())
        else:
            ref = extractor.single_ref

        # Fill in additional metadata information
        fill_in_elements(ref)

        # Handle potential duplication
        handle_duplicate(ref)

        # If there is an additional file(s) extract them and update ref
        extractor.extract_file(ref)

        # Final update for file metadata
        fill_in_elements(ref)

        # Export (if requested), update database, and exit!
        create_citation_package(ref, export=export)

    elif is_valid_file(uri_or_filename):
        pass
    else:
        click.echo("{} is not a valid input source".format(uri_or_filename))


def choose_ref(refs):
    pass

def fill_in_elements(reference):
    pass


def handle_duplicate(reference):
    pass

# Will expand this much in the future, for right now just outputs JSON to make sure this
# whole she-bang is working
def create_citation_package(reference, export=None):
    pass







