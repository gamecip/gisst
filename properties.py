__author__ = 'erickaltman'

from lxml import html
import uuid
import click

# Properties
class PropertyError(BaseException):
    pass


class Property(object):
    '''
    Base class for properties associated with each extractor.
    Must be subclassed before use. Each property takes a string 'path' or
    a callable object that processes a 'source' from the extractor.
    '''

    def __init__(self, path_or_callable=None, required=False, validate_func=None, cli_message=None):
        if isinstance(path_or_callable, str) or isinstance(path_or_callable, list):
            self.path = path_or_callable
        elif hasattr(path_or_callable, '__call__'):
            self.callable = path_or_callable

        self.required = required
        self.extractor = None
        self.name = None
        self._value = None
        self._cli_message = cli_message

        if validate_func:
            self._validate_func = validate_func
        else:
            self._validate_func = always_true

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    # Must be implemented in subclass
    def extract(self, source):
        raise NotImplementedError

    def validate(self, input_string):
        return self._validate_func(input_string)

    @property
    def cli_message(self):
        return self._cli_message

    @cli_message.setter
    def cli_message(self, value):
        self._cli_message = value


# Small subclasses for different Property types
# if a class is not prefixed with a type, it is assumed that it returns a str or list of strs

# NullProperty is needed for extractors that can extract a full metadata schema (all of them)
# NullPropertys act as a placeholder for a value added by the user
# NullProperty can still validate it's input from user, but cannot extract information from a source
class NullProperty(Property):

    def extract(self, source):
        return None


class XPathProperty(Property):

    def extract(self, source):
        tree = html.fromstring(source)
        self._value = tree.xpath(self.path)


class SingleXPathProperty(Property):

    def extract(self, source):
        tree = html.fromstring(source)
        temp = tree.xpath(self.path)
        try:
            self._value = temp[0]
        except IndexError:
            pass


class CallableProperty(Property):

    def extract(self, source):
        self._value = self.callable(source)


class SelectionProperty(Property):

    def extract(self, source):
        options = self.callable(source)
        click.echo(self.print_options(options))
        while 1:
            selection = click.prompt("Please choose one (by number)", type=int)
            if selection not in range(1, len(options) + 1):
                click.echo("{} is not a valid selection".format(selection))
            elif click.confirm("{}".format(options[selection - 1])):
                break
        self._value = options[selection - 1]

    @staticmethod
    def print_options(self, options):
        return ['{}. {}\n'.format(i, o) for i, o in enumerate(options)]




class UUIDProperty(Property):

    def extract(self, source):
        return uuid.uuid4()

# Validation Functions for Property Values
class ValidationError(BaseException):
    pass


def always_true(input_string):
    return True
