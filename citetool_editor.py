__author__ = 'erickaltman'

import click
import cmd
import subprocess
import hachoir_metadata
from uri_utils import get_source_name, process_game_uri, is_valid_uri



VERSION = '0.1'

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
@click.argument('uri_or_filename')
def generate((uri_or_filename)):
    '''Generate metadata information and citation package data from source URI or video file'''
    if is_valid_uri(uri_or_filename):
        click.echo("Collecting information from {}".format(get_source_name(uri_or_filename)))
        fill_in_metadata(process_game_uri(uri_or_filename))
    elif is_valid_filetype(uri_or_filename):
        pass
    else:
        click.echo("{} is not a valid input source".format(uri_or_filename))




def is_valid_file(uri):
    pass


def fill_in_metadata(cite_object):
    pass

