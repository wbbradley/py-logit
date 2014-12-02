#!/usr/bin/env python

from setuptools import setup

setup(
    name='logit',
    version='0.7.2',
    description='A private log for humans',
    author='Will Bradley',
    author_email='williambbradley@gmail.com',
    license='CC0',
    url='https://github.com/wbbradley/logit',
    packages=['logit'],
    install_requires=['pycrypto', 'boto', 'PyYAML'],
    entry_points={'console_scripts': [
        'logit = logit.main:main',
    ]},
)
