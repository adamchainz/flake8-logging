from __future__ import annotations

import ast
import re
from importlib.metadata import version
from textwrap import dedent

import pytest

from flake8_logging import Plugin


@pytest.fixture
def flake8_path(flake8_path):
    (flake8_path / "setup.cfg").write_text(
        dedent(
            """\
            [flake8]
            select = LOG
            """
        )
    )
    yield flake8_path


def run(source: str) -> list[tuple[int, int, str]]:
    tree = ast.parse(dedent(source))
    return [(line, col, msg) for (line, col, msg, type_) in Plugin(tree).run()]


def test_version(flake8_path):
    result = flake8_path.run_flake8(["--version"])
    version_regex = r"flake8-logging:( )*" + version("flake8-logging")
    unwrapped = "".join(result.out_lines)
    assert re.search(version_regex, unwrapped)


class TestLOG001:
    def test_integration(self, flake8_path):
        (flake8_path / "example.py").write_text(
            dedent(
                """\
                import logging
                logging.Logger("x")
                """
            )
        )

        result = flake8_path.run_flake8()

        assert result.out_lines == [
            "./example.py:2:1: LOG001 use logging.getLogger() to instantiate loggers"
        ]

    def test_attr(self):
        results = run(
            """\
            import logging
            logging.Logger("x")
            """
        )

        assert results == [
            (2, 0, "LOG001 use logging.getLogger() to instantiate loggers")
        ]

    def test_attr_as_name(self):
        results = run(
            """\
            import logging as lm
            lm.Logger("x")
            """
        )

        assert results == [
            (2, 0, "LOG001 use logging.getLogger() to instantiate loggers")
        ]

    def test_attr_in_class_def(self):
        results = run(
            """\
            import logging
            class Maker:
                logger = logging.Logger("x")
            """
        )

        assert results == [
            (3, 13, "LOG001 use logging.getLogger() to instantiate loggers")
        ]

    def test_attr_other_module(self):
        results = run(
            """\
            import our_logging
            our_logging.Logger("x")
            """
        )

        assert results == []

    def test_direct(self):
        results = run(
            """\
            from logging import Logger
            Logger("x")
            """
        )

        assert results == [
            (2, 0, "LOG001 use logging.getLogger() to instantiate loggers")
        ]

    def test_direct_not_from_logging(self):
        results = run(
            """\
            from our_logging import Logger
            Logger("x")
            """
        )

        assert results == []

    def test_direct_aliased(self):
        results = run(
            """\
            from loggin import Logger as _Logger
            _Logger("x")
            """
        )

        assert results == []

    def test_in_function_def(self):
        results = run(
            """\
            import logging
            def test_thing():
                logging.Logger("x")
            """
        )

        assert results == []

    def test_direct_in_function_def(self):
        results = run(
            """\
            from logging import Logger
            def test_thing():
                Logger("x")
            """
        )

        assert results == []

    def test_in_async_function_def(self):
        results = run(
            """\
            import logging
            async def test_thing():
                logging.Logger("x")
            """
        )

        assert results == []

    def test_direct_in_async_function_def(self):
        results = run(
            """\
            from logging import Logger
            async def test_thing():
                Logger("x")
            """
        )

        assert results == []


class TestLOG002:
    def test_integration(self, flake8_path):
        (flake8_path / "example.py").write_text(
            dedent(
                """\
                import logging
                logging.getLogger(__file__)
                """
            )
        )

        result = flake8_path.run_flake8()

        assert result.out_lines == [
            "./example.py:2:19: LOG002 use __name__ with getLogger()"
        ]

    def test_attr(self):
        results = run(
            """\
            import logging
            logging.getLogger(__file__)
            """
        )

        assert results == [(2, 18, "LOG002 use __name__ with getLogger()")]

    def test_attr_cached(self):
        results = run(
            """\
            import logging
            logging.getLogger(__cached__)
            """
        )

        assert results == [(2, 18, "LOG002 use __name__ with getLogger()")]

    def test_attr_in_function_def(self):
        results = run(
            """\
            import logging
            def thing():
                logging.getLogger(__file__)
            """
        )

        assert results == [(3, 22, "LOG002 use __name__ with getLogger()")]

    def test_direct(self):
        results = run(
            """\
            from logging import getLogger
            getLogger(__file__)
            """
        )

        assert results == [(2, 10, "LOG002 use __name__ with getLogger()")]

    def test_attr_dunder_name(self):
        results = run(
            """\
            import logging
            logging.getLogger(__name__)
            """
        )

        assert results == []

    def test_attr_other_module(self):
        results = run(
            """\
            import our_logging
            our_logging.getLogger(__file__)
            """
        )

        assert results == []


class TestLOG003:
    def test_integration(self, flake8_path):
        (flake8_path / "example.py").write_text(
            dedent(
                """\
                import logging
                logging.info("Hi", extra={"msg": "Ho"})
                """
            )
        )

        result = flake8_path.run_flake8()

        assert result.out_lines == [
            "./example.py:2:27: LOG003 extra key 'msg' clashes with LogRecord attribute"
        ]

    def test_module_call(self):
        results = run(
            """\
            import logging
            logging.info("Hi", extra={"msg": "Ho"})
            """
        )

        assert results == [
            (2, 26, "LOG003 extra key 'msg' clashes with LogRecord attribute")
        ]

    def test_module_call_debug(self):
        results = run(
            """\
            import logging
            logging.debug("Hi", extra={"msg": "Ho"})
            """
        )

        assert results == [
            (2, 27, "LOG003 extra key 'msg' clashes with LogRecord attribute")
        ]

    def test_module_call_args(self):
        results = run(
            """\
            import logging
            logging.info("Hi", extra={"args": (1,)})
            """
        )

        assert results == [
            (2, 26, "LOG003 extra key 'args' clashes with LogRecord attribute")
        ]

    def test_module_call_multiline(self):
        results = run(
            """\
            import logging
            logging.info(
                "Hi",
                extra={
                    "msg": "Ho",
                },
            )
            """
        )

        assert results == [
            (5, 8, "LOG003 extra key 'msg' clashes with LogRecord attribute")
        ]

    def test_module_call_multiple(self):
        results = run(
            """\
            import logging
            logging.info(
                "Hi",
                extra={
                    "args": (1,),
                    "msg": "Ho",
                },
            )
            """
        )

        assert results == [
            (5, 8, "LOG003 extra key 'args' clashes with LogRecord attribute"),
            (6, 8, "LOG003 extra key 'msg' clashes with LogRecord attribute"),
        ]

    def test_module_call_no_clash(self):
        results = run(
            """\
            import logging
            logging.info("Hi", extra={"response_msg": "Ho"})
            """
        )

        assert results == []

    def test_module_call_no_extra(self):
        results = run(
            """\
            import logging
            logging.info("Hi")
            """
        )

        assert results == []

    def test_module_call_extra_unsupported_type(self):
        results = run(
            """\
            import logging
            extra = {"msg": "Ho"}
            logging.info("Hi", extra=extra)
            """
        )

        assert results == []

    def test_module_call_in_function_def(self):
        results = run(
            """\
            import logging
            def thing():
                logging.info("Hi", extra={"msg": "Ho"})
            """
        )

        assert results == [
            (3, 30, "LOG003 extra key 'msg' clashes with LogRecord attribute")
        ]

    def test_module_call_dict_constructor(self):
        results = run(
            """\
            import logging
            logging.info("Hi", extra=dict(msg="Ho"))
            """
        )

        assert results == [
            (2, 30, "LOG003 extra key 'msg' clashes with LogRecord attribute")
        ]

    def test_logger_call(self):
        results = run(
            """\
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Hi", extra={"msg": "Ho"})
            """
        )

        assert results == [
            (3, 25, "LOG003 extra key 'msg' clashes with LogRecord attribute")
        ]

    def test_logger_call_other_name(self):
        results = run(
            """\
            import logging
            log = logging.getLogger(__name__)
            log.info("Hi", extra={"msg": "Ho"})
            """
        )

        assert results == [
            (3, 22, "LOG003 extra key 'msg' clashes with LogRecord attribute")
        ]

    def test_logger_call_dict_constructor(self):
        results = run(
            """\
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Hi", extra=dict(msg="Ho"))
            """
        )

        assert results == [
            (3, 29, "LOG003 extra key 'msg' clashes with LogRecord attribute")
        ]


class TestLOG004:
    def test_integration(self, flake8_path):
        (flake8_path / "example.py").write_text(
            dedent(
                """\
                import logging
                logging.exception("Hi")
                """
            )
        )

        result = flake8_path.run_flake8()

        assert result.out_lines == [
            "./example.py:2:1: LOG004 avoid exception() outside of exception handlers"
        ]

    def test_module_call(self):
        results = run(
            """\
            import logging
            logging.exception("Hi")
            """
        )

        assert results == [
            (2, 0, "LOG004 avoid exception() outside of exception handlers")
        ]

    def test_module_call_in_function_def(self):
        results = run(
            """\
            import logging
            def thing():
                logging.exception("Hi")
            """
        )

        assert results == [
            (3, 4, "LOG004 avoid exception() outside of exception handlers")
        ]

    def test_module_call_wrapped_in_function_def(self):
        # We can’t guarantee when the function will be called…
        results = run(
            """\
            import logging
            try:
                acme_api()
            except AcmeError:
                def handle():
                    logging.exception("Hi")
                handle()
            """
        )

        assert results == [
            (6, 8, "LOG004 avoid exception() outside of exception handlers")
        ]

    def test_module_call_ok(self):
        results = run(
            """\
            import logging
            try:
                acme_api()
            except AcmeError:
                logging.exception("Hi")
            """
        )

        assert results == []

    def test_module_call_ok_in_function_def(self):
        results = run(
            """\
            import logging
            def thing():
                try:
                    acme_api()
                except AcmeError:
                    logging.exception("Hi")
            """
        )

        assert results == []

    def test_logger_call(self):
        results = run(
            """\
            import logging
            logger = logging.getLogger(__name__)
            logger.exception("Hi")
            """
        )

        assert results == [
            (3, 0, "LOG004 avoid exception() outside of exception handlers")
        ]

    def test_logger_call_in_function_def(self):
        results = run(
            """\
            import logging
            logger = logging.getLogger(__name__)
            def thing():
                logger.exception("Hi")
            """
        )

        assert results == [
            (4, 4, "LOG004 avoid exception() outside of exception handlers")
        ]

    def test_logger_call_ok(self):
        results = run(
            """\
            import logging
            logger = logging.getLogger(__name__)
            try:
                acme_api()
            except AcmeError:
                logger.exception("Hi")
            """
        )

        assert results == []


class TestLOG005:
    def test_integration(self, flake8_path):
        (flake8_path / "example.py").write_text(
            dedent(
                """\
                import logging
                try:
                    int(x)
                except ValueError as exc:
                    logging.error("Bad int", exc_info=exc)
                """
            )
        )

        result = flake8_path.run_flake8()

        assert result.out_lines == [
            "./example.py:5:5: LOG005 use exception() within an exception handler"
        ]

    def test_module_call_with_exc_info(self):
        results = run(
            """\
            import logging
            try:
                int(x)
            except ValueError as exc:
                logging.error("Bad int", exc_info=exc)
            """
        )

        assert results == [
            (5, 4, "LOG005 use exception() within an exception handler"),
        ]

    def test_module_call_with_exc_info_true(self):
        results = run(
            """\
            import logging
            try:
                int(x)
            except ValueError as exc:
                logging.error("Bad int", exc_info=True)
            """
        )

        assert results == [
            (5, 4, "LOG005 use exception() within an exception handler"),
        ]

    def test_module_call_with_exc_info_1(self):
        results = run(
            """\
            import logging
            try:
                int(x)
            except ValueError as exc:
                logging.error("Bad int", exc_info=1)
            """
        )

        assert results == [
            (5, 4, "LOG005 use exception() within an exception handler"),
        ]

    def test_module_call_with_exc_info_string(self):
        results = run(
            """\
            import logging
            try:
                int(x)
            except ValueError as exc:
                logging.error("Bad int", exc_info="yes")
            """
        )

        assert results == [
            (5, 4, "LOG005 use exception() within an exception handler"),
        ]

    def test_module_call_without_exc_info(self):
        results = run(
            """\
            import logging
            try:
                int(x)
            except ValueError:
                logging.error("Bad int")
            """
        )

        assert results == [
            (5, 4, "LOG005 use exception() within an exception handler"),
        ]

    def test_module_call_with_false_exc_info(self):
        results = run(
            """\
            import logging
            try:
                int(x)
            except ValueError:
                logging.error("Bad int", exc_info=False)
            """
        )

        assert results == []

    def test_module_call_with_alternative_exc_info(self):
        results = run(
            """\
            import logging
            try:
                int(x)
            except ValueError as exc:
                exc2 = AttributeError("Bad int")
                logging.error("Bad int", exc_info=exc2)
            """
        )

        assert results == []

    def test_logger_call_with_exc_info(self):
        results = run(
            """\
            import logging
            logger = logging.getLogger(__name__)
            try:
                int(x)
            except ValueError as exc:
                logger.error("Bad int", exc_info=exc)
            """
        )

        assert results == [
            (6, 4, "LOG005 use exception() within an exception handler"),
        ]

    def test_logger_call_with_exc_info_true(self):
        results = run(
            """\
            import logging
            logger = logging.getLogger(__name__)
            try:
                int(x)
            except ValueError as exc:
                logging.error("Bad int", exc_info=True)
            """
        )

        assert results == [
            (6, 4, "LOG005 use exception() within an exception handler"),
        ]


class TestLOG006:
    def test_integration(self, flake8_path):
        (flake8_path / "example.py").write_text(
            dedent(
                """\
                import logging
                try:
                    1/0
                except ZeroDivisionError:
                    logging.exception("Oops", exc_info=True)
                """
            )
        )

        result = flake8_path.run_flake8()

        assert result.out_lines == [
            "./example.py:5:31: LOG006 redundant exc_info argument for exception()"
        ]

    def test_module_call_with_true(self):
        results = run(
            """\
            import logging
            try:
                1/0
            except ZeroDivisionError:
                logging.exception("Oops", exc_info=True)
            """
        )

        assert results == [
            (5, 30, "LOG006 redundant exc_info argument for exception()"),
        ]

    def test_module_call_with_exc(self):
        results = run(
            """\
            import logging
            try:
                1/0
            except ZeroDivisionError as exc:
                logging.exception("Oops", exc_info=exc)
            """
        )

        assert results == [
            (5, 30, "LOG006 redundant exc_info argument for exception()"),
        ]

    def test_module_call_with_different_exc(self):
        results = run(
            """\
            import logging
            try:
                1/0
            except ZeroDivisionError as exc:
                exc2 = AttributeError("?")
                logging.exception("Oops", exc_info=exc2)
            """
        )

        assert results == []

    def test_logger_call_with_true(self):
        results = run(
            """\
            import logging
            logger = logging.getLogger(__name__)
            try:
                1/0
            except ZeroDivisionError:
                logger.exception("Oops", exc_info=True)
            """
        )

        assert results == [
            (6, 29, "LOG006 redundant exc_info argument for exception()"),
        ]

    def test_logger_call_with_exc(self):
        results = run(
            """\
            import logging
            logger = logging.getLogger(__name__)
            try:
                1/0
            except ZeroDivisionError as exc:
                logger.exception("Oops", exc_info=exc)
            """
        )

        assert results == [
            (6, 29, "LOG006 redundant exc_info argument for exception()"),
        ]


class TestLOG007:
    def test_integration(self, flake8_path):
        (flake8_path / "example.py").write_text(
            dedent(
                """\
                import logging
                try:
                    1/0
                except ZeroDivisionError:
                    logging.exception("Oops", exc_info=False)
                """
            )
        )

        result = flake8_path.run_flake8()

        assert result.out_lines == [
            "./example.py:5:31: LOG007 use error() instead of exception() with "
            + "exc_info=False"
        ]

    def test_module_call_with_false(self):
        results = run(
            """\
            import logging
            try:
                1/0
            except ZeroDivisionError:
                logging.exception("Oops", exc_info=False)
            """
        )

        assert results == [
            (5, 30, "LOG007 use error() instead of exception() with exc_info=False"),
        ]

    def test_module_call_with_0(self):
        results = run(
            """\
            import logging
            try:
                1/0
            except ZeroDivisionError:
                logging.exception("Oops", exc_info=0)
            """
        )

        assert results == [
            (5, 30, "LOG007 use error() instead of exception() with exc_info=False"),
        ]

    def test_logger_call_with_false(self):
        results = run(
            """\
            import logging
            logger = logging.getLogger(__name__)
            try:
                1/0
            except ZeroDivisionError:
                logger.exception("Oops", exc_info=False)
            """
        )

        assert results == [
            (6, 29, "LOG007 use error() instead of exception() with exc_info=False"),
        ]


class TestLOG008:
    def test_integration(self, flake8_path):
        (flake8_path / "example.py").write_text(
            dedent(
                """\
                import logging
                logging.warn("Squawk")
                """
            )
        )

        result = flake8_path.run_flake8()

        assert result.out_lines == [
            "./example.py:2:1: LOG008 warn() is deprecated, use warning() instead"
        ]

    def test_module_call(self):
        results = run(
            """\
            import logging
            logging.warn("Squawk")
            """
        )

        assert results == [
            (2, 0, "LOG008 warn() is deprecated, use warning() instead"),
        ]

    def test_logger_call(self):
        results = run(
            """\
            import logging
            logger = logging.getLogger(__name__)
            logger.warn("Squawk")
            """
        )

        assert results == [
            (3, 0, "LOG008 warn() is deprecated, use warning() instead"),
        ]


class TestLOG009:
    def test_integration(self, flake8_path):
        (flake8_path / "example.py").write_text(
            dedent(
                """\
                import logging
                logging.WARN
                """
            )
        )

        result = flake8_path.run_flake8()

        assert result.out_lines == [
            "./example.py:2:1: LOG009 WARN is undocumented, use WARNING instead"
        ]

    def test_access(self):
        results = run(
            """\
            import logging
            logging.WARN
            """
        )

        assert results == [
            (2, 0, "LOG009 WARN is undocumented, use WARNING instead"),
        ]

    def test_access_alias(self):
        results = run(
            """\
            import logging as log
            log.WARN
            """
        )

        assert results == [
            (2, 0, "LOG009 WARN is undocumented, use WARNING instead"),
        ]

    def test_import(self):
        results = run(
            """\
            from logging import WARN
            """
        )

        assert results == [
            (1, 20, "LOG009 WARN is undocumented, use WARNING instead"),
        ]

    def test_import_multiline(self):
        results = run(
            """\
            from logging import (
                WARN,
            )
            """
        )

        assert results == [
            (2, 4, "LOG009 WARN is undocumented, use WARNING instead"),
        ]

    def test_import_alias(self):
        results = run(
            """\
            from logging import WARN as whatev
            """
        )

        assert results == [
            (1, 20, "LOG009 WARN is undocumented, use WARNING instead"),
        ]
