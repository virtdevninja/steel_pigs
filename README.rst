.. image:: https://travis-ci.org/virtdevninja/steel_pigs.svg
    :target: https://travis-ci.org/virtdevninja/steel_pigs

Steel PIGS is a python flask app that is middleware which can be configured to talk to remote inventory systems to
pull data from them to build custom ipxe scripts. This code is based on work done by Major Hayden, and Antony Messerli
on a project called miniplop.

Installing
==========
To install steel_pigs simply use pip like so ::

    pip install steel_pigs


Getting Started
===============
Once steel_pigs is installed you need to create your own custom plugins. For help doing that see the `wiki <https://github.com/virtdevninja/steel-pigs/wiki>`_.
Once you have your plugins built, installed, and have steel_pigs configured to use them simply use your favorite wsgi server
to server the app. Using gunicorn you might do something like this ::

    gunicorn steel_pigs.webapp:app

Next you would configure something like nginx to proxy the content. You could also use mod_wsgi in Apache HTTPD.


Contributing
============
To contribute to steel-pigs please follow the fork, branch, pull request work flow. Tests are required where applicable.
All code should follow pep8 standards, and must support python 2.7 When opening a pull request please
do so against the development branch.

If you wish to contribute a plugin please use the `steel_pigs_plugins <https://github.com/virtdevninja/steel_pigs_plugins>`_ project
on GitHub.


Python Support
==============
* steel-pigs 0.1 and later support Python 2.7


Reporting Issues
================
To report a problem with steel-pigs or to make a feature request open an
`issue <https://github.com/virtdevninja/steel-pigs/issues>`_ on GitHub.


Usage Examples
==============
See the `wiki <https://github.com/virtdevninja/steel-pigs/wiki>`_ on GitHub


Releases
========
Coming soon!
