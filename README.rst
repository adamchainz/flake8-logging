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

A `Flake8 <https://flake8.readthedocs.io/en/latest/>`_ plugin that checks for issues using the standard library logging module.

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

LOG001 use ``logging.getLogger()`` to instantiate loggers
---------------------------------------------------------

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

LOG002 use ``__name__`` with ``getLogger()``
--------------------------------------------

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

LOG003 ``extra`` key ``'<key>'`` clashes with LogRecord attribute
-----------------------------------------------------------------

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

LOG004 avoid ``exception()`` outside of exception handlers
----------------------------------------------------------

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

Corrected:

.. code-block:: python

    import logging

    response = acme_api()
    if response is None:
        logging.error("ACME failed")

LOG005 use ``exception()`` within an exception handler
------------------------------------------------------

Within an exception handler, the |exception()|__ method is preferable over ``logger.error()``.
The ``exception()`` method captures the exception automatically, whilst ``error()`` needs it to be passed explicitly in the ``exc_info`` argument.
Both methods log with the level ``ERROR``.

.. |exception()| replace:: ``exception()``
__ https://docs.python.org/3/library/logging.html#logging.Logger.exception

This rule detects ``error()`` calls within exception handlers with an ``exc_info`` argument.

Failing example:

.. code-block:: python

    try:
        acme_api()
    except AcmeError as exc:
        logger.error("ACME API failed", exc_info=exc)

Corrected:

.. code-block:: python

    try:
        acme_api()
    except AcmeError:
        logger.exception("ACME API failed")

LOG006 redundant ``exc_info`` argument for ``exception()``
----------------------------------------------------------

The |exception()2|__ method captures the exception automatically, making a truthy ``exc_info`` argument redundant.

.. |exception()2| replace:: ``exception()``
__ https://docs.python.org/3/library/logging.html#logging.Logger.exception

This rule detects ``exception()`` calls within exception handlers with an ``exc_info`` argument that is truthy or the captured exception object.

Failing example:

.. code-block:: python

    try:
        acme_api()
    except AcmeError:
        logger.exception("ACME API failed", exc_info=True)

Corrected:

.. code-block:: python

    try:
        acme_api()
    except AcmeError:
        logger.exception("ACME API failed")

LOG007 use ``error()`` instead of ``exception()`` with ``exc_info=False``
-------------------------------------------------------------------------

The |exception()3|__ method captures the exception automatically.
Disabling this by setting ``exc_info=False`` is the same as using ``error()``, which is clearer and doesn’t need the ``exc_info`` argument.

.. |exception()3| replace:: ``exception()``
__ https://docs.python.org/3/library/logging.html#logging.Logger.exception

This rule detects ``exception()`` calls with an ``exc_info`` argument that is falsy.

Failing example:

.. code-block:: python

    logger.exception("Left phalange missing", exc_info=False)

Corrected:

.. code-block:: python

    logger.exception("Left phalange missing")

LOG008 ``warn()`` is deprecated, use ``warning()`` instead
----------------------------------------------------------

The ``warn()`` method is a deprecated, undocumented alias for |warning()|__
``warning()`` should always be used instead.
The method was deprecated in Python 2.7, in commit `04d5bc00a2 <https://github.com/python/cpython/commit/04d5bc00a219860c69ea17eaa633d3ab9917409f>`__, and removed in Python 3.13, in commit `dcc028d924 <https://github.com/python/cpython/commit/dcc028d92428bd57358a5028ada2a53fc79fc365>`__.

.. |warning()| replace:: ``warning()``
__ https://docs.python.org/3/library/logging.html#logging.Logger.warning

This rule detects calls to ``warn()``.

Failing example:

.. code-block:: python

    logger.warn("Cheesy puns incoming")

Corrected:

.. code-block:: python

    logger.warning("Cheesy puns incoming")
