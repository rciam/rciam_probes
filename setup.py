#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from codecs import open
from os import path

__name__ = 'rciam_probes'
__version__ = '1.2.6'

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

# get the dependencies and installs
with open(path.join(here, 'requirements.txt'), encoding='utf-8') as f:
    all_reqs = f.read().split('\n')

install_requires = [x.strip() for x in all_reqs if 'git+' not in x]
dependency_links = [x.strip().replace('git+', '') for x in all_reqs if x.startswith('git+')]

setup(name=__name__,
      version=__version__,
      license='Apache-2.0',
      author='ioigoume@admin.grnet.gr',
      author_email='ioigoume@admin.grnet.gr',
      description='Package includes probes for RCIAM',
      classifiers=[
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.5",
          "Programming Language :: Python :: 3.6",
          "License :: OSI Approved :: Apache Software License",
          "Operating System :: OS Independent",
      ],
      platforms='noarch',
      long_description=long_description,
      long_description_content_type="text/markdown",
      url='https://github.com/rciam/rciam_probes',
      packages=find_packages(exclude=['tests', 'docs']),
      include_package_data=True,
      scripts=["bin/checkcert", "bin/checklogin"],
      python_requires='~=3.5',
      install_requires=install_requires,
      )
