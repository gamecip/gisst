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
        'SQLAlchemy==1.0.12',
        'youtube-dl',
        'Pillow',
        'pyreadline',
        'requests',
        'Whoosh'
    ],
    entry_points='''
        [console_scripts]
        citetool_editor=citetool_editor.citetool_editor:cli
    ''',
    author="Eric Kaltman",
    author_email="ekaltman@gmail.com",
    include_package_data=True,
    package_data={
        'static': 'citetool_editor/static/*',
        'templates': 'citetool_editor/templates/*'
    }
)
