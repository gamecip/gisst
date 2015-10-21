__author__ = 'erickaltman'

from itertools import izip, tee
from functools import wraps
import timeit

# Pairwise non-overlap function from: http://stackoverflow.com/questions/5389507/iterating-over-every-two-elements-in-a-list
def pairwise(iterable):
    "s -> (s0,s1), (s2,s3), (s4, s5), ..."
    a = iter(iterable)
    return izip(a, a)

# Pairwise function from: https://docs.python.org/2/library/itertools.html
def pairwise_overlap(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return izip(a, b)

# Dictionary Merge from: http://stackoverflow.com/questions/38987/how-can-i-merge-two-python-dictionaries-in-a-single-expression
def merge_dicts(*dict_args):
    '''
    Given any number of dicts, shallow copy and merge into a new dict,
    precedence goes to key value pairs in latter dicts.
    '''
    result = {}
    for dictionary in dict_args:
        result.update(dictionary)
    return result


# Replace latin non-breaking space with unicode space in unicode string
# Needed since spaces is table show up as non-breaking Latin space instead of unicode space
# see: http://stackoverflow.com/questions/10993612/python-removing-xa0-from-string for more details
def replace_xa0(string):
    if isinstance(string, unicode):
        return string.replace(u'\xa0', u' ')
    return string

# 'Hi Everyone' -> 'hi_everyone'
def snake_case(string):
    if isinstance(string, unicode):
        return string.replace(u' ', u'_').lower()
    elif isinstance(string, str):
        return string.replace(' ', '_').lower()
    return string

# Checks path for specific command
# From: http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
def which(program):
    import os

    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)

    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None

def coroutine(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        generator = func(*args, **kwargs)
        next(generator)
        return generator
    return wrapper


def timing(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = timeit.default_timer()
        result = func(*args, **kwargs)
        elapsed = timeit.default_timer() - start_time
        print elapsed
        return result
    return wrapper


def bound_array(array, start_index=0, limit=None):
    if limit:
        sub_array = array[:limit]
        return sub_array[start_index:]
    return array[start_index:]


def clean_for_sqlite_query(text):
    puncs = (':', ',')
    funcs = [lambda t, x=x: t.replace(x, '') for x in puncs]
    return reduce(lambda y, z: z(y), funcs, text)
