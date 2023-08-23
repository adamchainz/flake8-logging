==============
flake8-logging
==============

.. image:: https://img.shields.io/github/actions/workflow/status/adamchainz/flake8-logging/main.yml?branch=main&style=for-the-badge
   :target: https://github.com/adamchainz/flake8-logging/actions?workflow=CI

.. image:: https://img.shields.io/pypi/v/flake8-logging.svg?style=for-the-badge
   :target: https://pypi.org/project/flake8-logging/

.. image:: https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge
   :target: https://github.com/psf/black

.. image:: https://img.shields.io/badge/pre--commit-enabled-brightgreen?logo=pre-commit&logoColor=white&style=for-the-badge
   :target: https://github.com/pre-commit/pre-commit
   :alt: pre-commit

A `Flake8 <https://flake8.readthedocs.io/en/latest/>`_ plugin to improve logging.

Requirements
============

Python 3.8 to 3.12 supported.

Installation
============

First, install with ``pip``:

.. code-block:: sh

     python -m pip install flake8-logging

Second, if you define Flake8’s ``select`` setting, add the ``L`` prefix to it.
Otherwise, the plugin should be active by default.

----

**Linting a Django project?**
Check out my book `Boost Your Django DX <https://adamchainz.gumroad.com/l/byddx>`__ which covers Flake8 and many other code quality tools.

----

Rules
=====

L001: use ``logging.getLogger()`` to instantiate loggers
--------------------------------------------------------

The `Logger Objects documentation section <https://docs.python.org/3/library/logging.html#logger-objects>`__ starts:

  Note that Loggers should NEVER be instantiated directly, but always through the module-level function ``logging.getLogger(name)``.

Directly instantiated loggers are not added into the logger tree, so their messages are discarded.
This means you’ll never see any messages on such loggers.
Use |getLogger()|__ to correctly instantiate loggers.

.. |getLogger()| replace:: ``getLogger()``
__ https://docs.python.org/3/library/logging.html#logging.getLogger

This rule detects any module-level logger instantiation.

Failing example:

.. code-block:: python

    import logging

    logger = logging.Logger(__name__)

Correct example:

.. code-block:: python

    import logging

    logger = logging.getLogger(__name__)
