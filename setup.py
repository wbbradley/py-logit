#!/usr/bin/env python

from setuptools import setup

setup(
    name='logit-safe',
    version='0.6',
    description='A private log for humans',
    author='Will Bradley',
    author_email='williambbradley@gmail.com',
    license='CC0',
    url='https://github.com/wbbradley/logit',
    packages=['logit'],
    install_requires=['boto', 'PyYAML'],
    entry_points={'console_scripts': [
        'logit = logit.logit:main',
    ]},
)
