=========
Changelog
=========

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
