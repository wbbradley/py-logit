#!/usr/bin/env python

from setuptools import setup, find_packages

setup(
    name='logit',
    version='0.7.4',
    description='A private log for humans',
    author='Will Bradley',
    author_email='williambbradley@gmail.com',
    license='CC0',
    url='https://github.com/wbbradley/logit',
    packages=find_packages(exclude=["*.tests", "*.tests.*", "tests.*",
                                    "tests"]),
    install_requires=['pycrypto', 'boto', 'PyYAML', 'attrdict'],
    entry_points={'console_scripts': [
        'logit = logit.main:main',
    ]},
)
