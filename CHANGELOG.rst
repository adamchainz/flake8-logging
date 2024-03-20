=========
Changelog
=========

1.6.0 (2024-03-20)
------------------

* Add rule LOG015 that detects use of the root logger through calls like ``logging.info()``.

  Thanks to John Litborn in `PR #96 <https://github.com/adamchainz/flake8-logging/pull/96>`__.

1.5.0 (2024-01-23)
------------------

* Extend LOG003 disallowed ``extra`` keys to include ``message``.

  Thanks to Bartek Ogryczak in `PR #77 <https://github.com/adamchainz/flake8-logging/pull/77>`__.

1.4.0 (2023-10-10)
------------------

* Add rule LOG013 that detects mismatches between named ``%``-style formatting placeholders and keys in dict argument.

* Add rule LOG014 that detects ``exc_info=True`` outside of exception handlers.

1.3.1 (2023-09-17)
------------------

* Fix LOG012 false positive with unpacked arguments like ``*args``.

* Fix LOG012 false positive with ``%%`` in formatting strings.

1.3.0 (2023-09-17)
------------------

* Add rule LOG012 that detects mismatches between ``%``-style formatting placeholders and arguments.

1.2.0 (2023-09-04)
------------------

* Add rule LOG009 that detects use of the undocumented ``WARN`` constant.

* Add rule LOG010 that detects passing calls to ``exception()`` passing a handled exception as the first argument.

* Add rule LOG011 that detects pre-formatted log messages.

1.1.0 (2023-08-25)
------------------

* LOG001: Avoid detecting inside function definitions when using ``Logger`` directly.

* Add rule LOG005 that recomends ``exception()`` over ``error()`` within ``except`` clauses.

* Add rule LOG006 that detects redundant ``exc_info`` arguments in calls to ``exception()``.

* Add rule LOG007 that detects ``exception()`` calls with falsy ``exc_info`` arguments, which are better written as ``error()``.

* Add rule LOG008 that detects calls to the deprecated, undocumented ``warn()`` method.

1.0.2 (2023-08-24)
------------------

* Change error codes to start with ``LOG`` so they are more specific.

1.0.1 (2023-08-24)
------------------

* Correct entry point definition so codes are picked up by default.

1.0.0 (2023-08-24)
------------------

* Initial release.
