__author__ = 'erickaltman'

import re
from setuptools import setup

version = re.search(
    '^__version__\s*=\s*"(.*)"',
    open('citetool_editor/citetool_editor.py').read(),
    re.M
).group(1)

setup(
    name='citetool-editor',
    version=version,
    description="Game Citation Manager and Web Editor",
    packages=["citetool_editor"],
    install_requires=[
        'click>=6',
        'beautifulsoup4',
        'Flask',
        'hachoir-core',
        'hachoir-metadata',
        'hachoir-parser',
        'pytz',
        'SQLAlchemy',
        'youtube-dl',
        'Pillow',
        'gnureadline',
        'requests',
        'pysqlite>=2',
    ],
    entry_points='''
        [console_scripts]
        citetool_editor=citetool_editor.citetool_editor:cli
    ''',
    author="Eric Kaltman",
    author_email="ekaltman@gmail.com",
    include_package_data=True
)
