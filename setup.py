#   Copyright 2015 Michael Rice <michael@michaelrice.org>
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

import os

from setuptools import setup, find_packages


def read(fname):
    with open(os.path.join(os.path.dirname(__file__), fname)) as fn:
        return fn.read()

with open('requirements.txt') as f:
    required = f.read().splitlines()

with open('test-requirements.txt') as f:
    required_for_tests = f.read().splitlines()

setup(
    name='steel_pigs',
    version='0.1',
    packages=find_packages(exclude=["test*"]),
    url='https://github.com/virtdevninja/steel_pigs',
    license='License :: OSI Approved :: Apache Software License',
    author='Michael Rice',
    author_email='michael@michaelrice.org',
    description='Powerful iPXE Generation Service',
    long_description=read('README.rst'),
    platforms=['Windows', 'Linux', 'Solaris', 'Mac OS-X', 'Unix'],
    test_suite='tests',
    zip_safe=True,
    tests_require=required_for_tests,
    package_data={
        'static': 'steel_pigs/static/*',
        'templates': 'steel_pigs/templates/*'
    },
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'pigs_dev_server = steel_pigs.scripts.run_server:dev_server',
            'pigs_run_server = steel_pigs.scripts.run_server:run_server'
        ]
    },
)
