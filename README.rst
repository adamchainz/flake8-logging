==============
flake8-logging
==============

.. image:: https://img.shields.io/github/actions/workflow/status/adamchainz/flake8-logging/main.yml?branch=main&style=for-the-badge
   :target: https://github.com/adamchainz/flake8-logging/actions?workflow=CI

.. image:: https://img.shields.io/badge/Coverage-100%25-success?style=for-the-badge
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

L002: use ``__name__`` with ``getLogger()``
-------------------------------------------

The `logging documentation <https://docs.python.org/3/library/logging.html#logger-objects>`__ recommends this pattern:

.. code-block:: python

    logging.getLogger(__name__)

|__name__|__ is the fully qualified module name, such as ``camelot.spam``, which is the intended format for logger names.

.. |__name__| replace:: ``__name__``
__ https://docs.python.org/3/reference/import.html?#name__

This rule detects probably-mistaken usage of similar module-level dunder constants:

* |__cached__|__ - the pathname of the module’s compiled versio˜, such as ``camelot/__pycache__/spam.cpython-311.pyc``.

  .. |__cached__| replace:: ``__cached__``
  __ https://docs.python.org/3/reference/import.html?#cached__

* |__file__|__ - the pathname of the module, such as ``camelot/spam.py``.

  .. |__file__| replace:: ``__file__``
  __ https://docs.python.org/3/reference/import.html?#file__

Failing example:

.. code-block:: python

    import logging

    logger = logging.Logger(__file__)

Correct example:

.. code-block:: python

    import logging

    logger = logging.getLogger(__name__)
