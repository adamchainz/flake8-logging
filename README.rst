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

This rule detects any module-level calls to ``Logger()``.

Failing example:

.. code-block:: python

    import logging

    logger = logging.Logger(__name__)

Corrected:

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

    logger = logging.getLogger(__file__)

Corrected:

.. code-block:: python

    import logging

    logger = logging.getLogger(__name__)

L003: ``extra`` key ``'<key>'`` clashes with LogRecord attribute
----------------------------------------------------------------

The |extra documentation|__ states:

.. |extra documentation| replace:: ``extra`` documentation
__ https://docs.python.org/3/library/logging.html#logging.Logger.debug

    The keys in the dictionary passed in ``extra`` should not clash with the keys used by the logging system.

Such clashes crash at runtime with an error like:

.. code-block:: text

    KeyError: "Attempt to overwrite 'msg' in LogRecord"

Unfortunately, this error is only raised if the message is not filtered out by level.
Tests may therefore not encounter the check, if they run with a limited logging configuration.

This rule detects such clashes by checking for keys matching the |LogRecord attributes|__.

.. |LogRecord attributes| replace:: ``LogRecord`` attributes
__ https://docs.python.org/3/library/logging.html#logrecord-attributes

Failing example:

.. code-block:: python

    import logging
    logger = logging.getLogger(__name__)

    response = acme_api()
    logger.info("ACME Response", extra={"msg": response.msg})

Corrected:

.. code-block:: python

    import logging
    logger = logging.getLogger(__name__)

    response = acme_api()
    logger.info("ACME Response", extra={"response_msg": response.msg})

L004: avoid ``logger.exception()`` outside of ``except`` clauses
----------------------------------------------------------------

The |exception() documentation|__ states:

.. |exception() documentation| replace:: ``exception()`` documentation
__ https://docs.python.org/3/library/logging.html#logging.exception

    This function should only be called from an exception handler.

Calling ``exception()`` outside of an exception handler attaches ``None`` exception information, leading to confusing messages:

.. code-block:: pycon

    >>> logging.exception("example")
    ERROR:root:example
    NoneType: None

Use ``error()`` instead.
To log a caught exception, pass it in the ``exc_info`` argument.

This rule detects ``exception()`` calls outside of exception handlers.

Failing example:

.. code-block:: python

    import logging

    response = acme_api()
    if response is None:
        logging.exception("ACME failed")

Correct example:

.. code-block:: python

    import logging

    response = acme_api()
    if response is None:
        logging.error("ACME failed")
