__author__ = 'erickaltman'

from setuptools import setup

setup(
    name='citetool-editor',
    version='0.1',
    py_modules=['citetool_editor'],
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        citetool_editor=citetool_editor:cli
    ''',
)
