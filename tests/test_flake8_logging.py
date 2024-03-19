from __future__ import annotations

import ast
import logging
import re
import sys
from importlib.metadata import version
from textwrap import dedent

import pytest

from flake8_logging import Plugin
from flake8_logging import flatten_str_chain


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


class TestIntegration:
    def test_version(self, flake8_path):
        result = flake8_path.run_flake8(["--version"])
        version_regex = r"flake8-logging:( )*" + version("flake8-logging")
        unwrapped = "".join(result.out_lines)
        assert re.search(version_regex, unwrapped)

    def test_log001(self, flake8_path):
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


def run(source: str, ignore: tuple[str, ...] = tuple()) -> list[tuple[int, int, str]]:
    tree = ast.parse(dedent(source))
    return [
        (line, col, msg)
        for (line, col, msg, type_) in Plugin(tree).run()
        if msg[:6] not in ignore
    ]


class Ignore015:
    def run(self, source: str) -> list[tuple[int, int, str]]:
        return run(source, ignore=("LOG015",))


class TestLOG001:
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


class TestLOG003(Ignore015):
    def test_module_call(self):
        results = self.run(
            """\
            import logging
            logging.info("Hi", extra={"msg": "Ho"})
            """
        )

        assert results == [
            (2, 26, "LOG003 extra key 'msg' clashes with LogRecord attribute")
        ]

    @pytest.mark.parametrize("key", logging.makeLogRecord({}).__dict__.keys())
    def test_module_call_logrecord_keys(self, key):
        results = self.run(
            f"""\
            import logging
            logging.info("Hi", extra={{"{key}": "Ho"}})
            """
        )

        assert results == [
            (2, 26, f"LOG003 extra key '{key}' clashes with LogRecord attribute")
        ]

    @pytest.mark.parametrize("key", ["asctime", "message"])
    def test_module_call_formatter_keys(self, key):
        results = self.run(
            f"""\
            import logging
            logging.info("Hi", extra={{"{key}": "Ho"}})
            """
        )

        assert results == [
            (2, 26, f"LOG003 extra key '{key}' clashes with LogRecord attribute")
        ]

    def test_module_call_debug(self):
        results = self.run(
            """\
            import logging
            logging.debug("Hi", extra={"msg": "Ho"})
            """
        )

        assert results == [
            (2, 27, "LOG003 extra key 'msg' clashes with LogRecord attribute")
        ]

    def test_module_call_args(self):
        results = self.run(
            """\
            import logging
            logging.info("Hi", extra={"args": (1,)})
            """
        )

        assert results == [
            (2, 26, "LOG003 extra key 'args' clashes with LogRecord attribute")
        ]

    def test_module_call_multiline(self):
        results = self.run(
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
        results = self.run(
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
        results = self.run(
            """\
            import logging
            logging.info("Hi", extra={"response_msg": "Ho"})
            """
        )

        assert results == []

    def test_module_call_no_extra(self):
        results = self.run(
            """\
            import logging
            logging.info("Hi")
            """
        )

        assert results == []

    def test_module_call_extra_unsupported_type(self):
        results = self.run(
            """\
            import logging
            extra = {"msg": "Ho"}
            logging.info("Hi", extra=extra)
            """
        )

        assert results == []

    def test_module_call_in_function_def(self):
        results = self.run(
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
        results = self.run(
            """\
            import logging
            logging.info("Hi", extra=dict(msg="Ho"))
            """
        )

        assert results == [
            (2, 30, "LOG003 extra key 'msg' clashes with LogRecord attribute"),
        ]

    def test_module_call_dict_constructor_unpack(self):
        results = self.run(
            """\
            import logging
            more = {"msg": "Ho"}
            logging.info("Hi", extra=dict(**more))
            """
        )

        assert results == []

    def test_logger_call(self):
        results = self.run(
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
        results = self.run(
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
        results = self.run(
            """\
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Hi", extra=dict(msg="Ho"))
            """
        )

        assert results == [
            (3, 29, "LOG003 extra key 'msg' clashes with LogRecord attribute")
        ]


class TestLOG004(Ignore015):
    def test_module_call(self):
        results = self.run(
            """\
            import logging
            logging.exception("Hi")
            """
        )

        assert results == [
            (2, 0, "LOG004 avoid exception() outside of exception handlers")
        ]

    def test_module_call_in_function_def(self):
        results = self.run(
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
        results = self.run(
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
        results = self.run(
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
        results = self.run(
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
        results = self.run(
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
        results = self.run(
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
        results = self.run(
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


class TestLOG005(Ignore015):
    def test_module_call_with_exc_info(self):
        results = self.run(
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
        results = self.run(
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
        results = self.run(
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
        results = self.run(
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
        results = self.run(
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
        results = self.run(
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
        results = self.run(
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
        results = self.run(
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
        results = self.run(
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


class TestLOG006(Ignore015):
    def test_module_call_with_true(self):
        results = self.run(
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
        results = self.run(
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
        results = self.run(
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
        results = self.run(
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
        results = self.run(
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


class TestLOG007(Ignore015):
    def test_module_call_with_false(self):
        results = self.run(
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
        results = self.run(
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
        results = self.run(
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


class TestLOG008(Ignore015):
    def test_module_call(self):
        results = self.run(
            """\
            import logging
            logging.warn("Squawk")
            """
        )

        assert results == [
            (2, 0, "LOG008 warn() is deprecated, use warning() instead"),
        ]

    def test_logger_call(self):
        results = self.run(
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

        if sys.version_info >= (3, 10):
            pos = (1, 20)
        else:
            pos = (1, 0)
        assert results == [
            (*pos, "LOG009 WARN is undocumented, use WARNING instead"),
        ]

    def test_import_multiline(self):
        results = run(
            """\
            from logging import (
                WARN,
            )
            """
        )

        if sys.version_info >= (3, 10):
            pos = (2, 4)
        else:
            pos = (1, 0)
        assert results == [
            (*pos, "LOG009 WARN is undocumented, use WARNING instead"),
        ]

    def test_import_alias(self):
        results = run(
            """\
            from logging import WARN as whatev
            """
        )

        if sys.version_info >= (3, 10):
            pos = (1, 20)
        else:
            pos = (1, 0)
        assert results == [
            (*pos, "LOG009 WARN is undocumented, use WARNING instead"),
        ]


class TestLOG010(Ignore015):
    def test_module_call(self):
        results = self.run(
            """\
            import logging

            try:
                ...
            except Exception as exc:
                logging.exception(exc)
            """
        )

        assert results == [
            (6, 22, "LOG010 exception() does not take an exception"),
        ]

    def test_module_call_multiline(self):
        results = self.run(
            """\
            import logging

            try:
                ...
            except Exception as exc:
                logging.exception(
                    exc,
                )
            """
        )

        assert results == [
            (7, 8, "LOG010 exception() does not take an exception"),
        ]

    def test_module_call_no_args(self):
        results = self.run(
            """\
            import logging

            try:
                ...
            except Exception as exc:
                logging.exception()
            """
        )

        assert results == []

    def test_module_call_second_arg(self):
        results = self.run(
            """\
            import logging

            try:
                ...
            except Exception as exc:
                logging.exception("Saw %s", exc)
            """
        )

        assert results == []

    def test_module_call_not_exc_handler_name(self):
        results = self.run(
            """\
            import logging

            try:
                ...
            except Exception:
                exc = "Uh-oh"
                logging.exception(exc)
            """
        )

        assert results == []

    def test_module_call_in_function_def(self):
        results = self.run(
            """\
            import logging

            try:
                ...
            except Exception as exc:
                def later():
                    exc = "message"
                    logging.exception(exc)
            """
        )

        assert results == [
            (8, 8, "LOG004 avoid exception() outside of exception handlers")
        ]

    def test_logger_call(self):
        results = self.run(
            """\
            import logging
            logger = logging.getLogger(__name__)

            try:
                ...
            except Exception as exc:
                logger.exception(exc)
            """
        )

        assert results == [
            (7, 21, "LOG010 exception() does not take an exception"),
        ]


class TestLOG011(Ignore015):
    def test_module_call(self):
        results = self.run(
            """\
            import logging

            logging.info(f"Hi {name}")
            """
        )

        assert results == [
            (3, 13, "LOG011 avoid pre-formatting log messages"),
        ]

    def test_module_call_multiline(self):
        results = self.run(
            """\
            import logging

            logging.info(
                f"Hi {name}"
            )
            """
        )

        assert results == [
            (4, 4, "LOG011 avoid pre-formatting log messages"),
        ]

    def test_module_call_log(self):
        results = self.run(
            """\
            import logging

            logging.log(
                logging.INFO,
                f"Hi {name}",
            )
            """
        )

        assert results == [
            (5, 4, "LOG011 avoid pre-formatting log messages"),
        ]

    def test_module_call_str_format(self):
        results = self.run(
            """\
            import logging

            logging.info("Hi {}".format(name))
            """
        )

        assert results == [
            (3, 13, "LOG011 avoid pre-formatting log messages"),
        ]

    def test_module_call_str_doormat(self):
        results = self.run(
            """\
            import logging

            logging.info("Hi {}".doormat(name))
            """
        )

        assert results == []

    def test_module_call_mod_format(self):
        results = self.run(
            """\
            import logging

            logging.info("Hi %s" % (name,))
            """
        )

        assert results == [
            (3, 13, "LOG011 avoid pre-formatting log messages"),
        ]

    def test_module_call_concatenation(self):
        results = self.run(
            """\
            import logging

            logging.info("Hi " + name + "!")
            """
        )

        assert results == [
            (3, 13, "LOG011 avoid pre-formatting log messages"),
        ]

    def test_module_call_concatenation_multiple(self):
        results = self.run(
            """\
            import logging

            logging.info("Hi " + name)
            """
        )

        assert results == [
            (3, 13, "LOG011 avoid pre-formatting log messages"),
        ]

    def test_module_call_concatenation_non_string(self):
        results = self.run(
            """\
            import logging

            logging.info("Hi " + 1)
            """
        )

        assert results == [
            (3, 13, "LOG011 avoid pre-formatting log messages"),
        ]

    def test_module_call_concatenation_f_string(self):
        results = self.run(
            """\
            import logging

            logging.info(f"Hi" "a")
            """
        )

        assert results == [
            (3, 13, "LOG011 avoid pre-formatting log messages"),
        ]

    def test_module_call_concatenation_all_strings(self):
        results = self.run(
            """\
            import logging

            logging.info("Hi " + "name")
            """
        )

        assert results == []

    def test_module_call_non_addition(self):
        results = self.run(
            """\
            import logging

            logging.info("not" - "valid")
            """
        )

        assert results == []

    def test_module_call_keyword(self):
        results = self.run(
            """\
            import logging

            logging.info(msg=f"Hi {name}")
            """
        )

        assert results == [
            (3, 17, "LOG011 avoid pre-formatting log messages"),
        ]

    def test_logger_call(self):
        results = self.run(
            """\
            import logging
            logger = logging.getLogger(__name__)

            logger.info(f"Hi {name}")
            """
        )

        assert results == [
            (4, 12, "LOG011 avoid pre-formatting log messages"),
        ]

    def test_logger_call_str_format(self):
        results = self.run(
            """\
            import logging
            logger = logging.getLogger(__name__)

            logger.info("Hi {name}".format(name=name))
            """
        )

        assert results == [
            (4, 12, "LOG011 avoid pre-formatting log messages"),
        ]

    def test_logger_call_mod_format(self):
        results = self.run(
            """\
            import logging
            logger = logging.getLogger(__name__)

            logger.info("Hi %(name)s" % {"name": name})
            """
        )

        assert results == [
            (4, 12, "LOG011 avoid pre-formatting log messages"),
        ]

    def test_logger_call_concatenation(self):
        results = self.run(
            """\
            import logging
            logger = logging.getLogger(__name__)

            logger.info("Hi " + name)
            """
        )

        assert results == [
            (4, 12, "LOG011 avoid pre-formatting log messages"),
        ]

    def test_logger_call_concatenation_multiple(self):
        results = self.run(
            """\
            import logging
            logger = logging.getLogger(__name__)

            logger.info("Hi " + name + "!")
            """
        )

        assert results == [
            (4, 12, "LOG011 avoid pre-formatting log messages"),
        ]

    def test_logger_call_concatenation_all_strings(self):
        results = self.run(
            """\
            import logging
            logger = logging.getLogger(__name__)

            logger.info("Hi " + "name" + "!")
            """
        )

        assert results == []

    def test_logger_call_keyword(self):
        results = self.run(
            """\
            import logging
            logger = logging.getLogger(__name__)

            logger.info(msg=f"Hi {name}")
            """
        )

        assert results == [
            (4, 16, "LOG011 avoid pre-formatting log messages"),
        ]


class TestLOG012(Ignore015):
    def test_module_call_modpos_args_1_0(self):
        results = self.run(
            """\
            import logging
            logging.info("Blending %s")
            """
        )

        assert results == [
            (2, 13, "LOG012 formatting error: 1 % placeholder but 0 arguments"),
        ]

    def test_module_call_modpos_args_2_0(self):
        results = self.run(
            """\
            import logging
            logging.info("Blending %s %s")
            """
        )

        assert results == [
            (2, 13, "LOG012 formatting error: 2 % placeholders but 0 arguments"),
        ]

    def test_module_call_modpos_args_0_1(self):
        # Presume another style is in use
        results = self.run(
            """\
            import logging
            logging.info("Blending", fruit)
            """
        )

        assert results == []

    def test_module_call_modpos_args_0_percent(self):
        results = self.run(
            """\
            import logging
            logging.info("Blending 100%%")
            """
        )

        assert results == []

    def test_module_call_modpos_args_1_percent(self):
        results = self.run(
            """\
            import logging
            logging.info("Blended %s%% of %s", percent, fruit)
            """
        )

        assert results == []

    def test_module_call_modpos_args_2_1_minwidth(self):
        results = self.run(
            """\
            import logging
            logging.info("Blending %*d", fruit)
            """
        )

        assert results == [
            (2, 13, "LOG012 formatting error: 2 % placeholders but 1 argument"),
        ]

    def test_module_call_modpos_args_2_1_precision(self):
        results = self.run(
            """\
            import logging
            logging.info("Blending %.*d", fruit)
            """
        )

        assert results == [
            (2, 13, "LOG012 formatting error: 2 % placeholders but 1 argument"),
        ]

    def test_module_call_modpos_args_3_1_minwidth_precision(self):
        results = self.run(
            """\
            import logging
            logging.info("Blending %*.*f", fruit)
            """
        )

        assert results == [
            (2, 13, "LOG012 formatting error: 3 % placeholders but 1 argument"),
        ]

    def test_module_call_modpos_joined_args_1_0(self):
        results = self.run(
            """\
            import logging
            logging.info("Blending " + "%s")
            """
        )

        assert results == [
            (2, 13, "LOG012 formatting error: 1 % placeholder but 0 arguments"),
        ]

    def test_module_call_log_modpos_args_1_0(self):
        results = self.run(
            """\
            import logging
            logging.log(logging.INFO, "Blending %s")
            """
        )

        assert results == [
            (2, 26, "LOG012 formatting error: 1 % placeholder but 0 arguments"),
        ]

    def test_module_call_modpos_kwarg(self):
        results = self.run(
            """\
            import logging
            logging.info(msg="Blending %s")
            """
        )

        assert results == []

    def test_module_call_log_modpos_kwarg(self):
        results = self.run(
            """\
            import logging
            logging.log(logging.INFO, msg="Blending %s")
            """
        )

        assert results == []

    def test_module_call_modpos_star_args(self):
        results = self.run(
            """\
            import logging
            logging.info("Blending %s %s", *args)
            """
        )

        assert results == []

    def test_module_call_named(self):
        results = self.run(
            """\
            import logging
            logging.info("Blending %(fruit)s")
            """
        )

        assert results == []

    def test_module_call_strformat(self):
        results = self.run(
            """\
            import logging
            logging.info("Blending {}")
            """
        )

        assert results == []

    def test_module_call_template(self):
        results = self.run(
            """\
            import logging
            logging.info("Blending $fruit")
            """
        )

        assert results == []

    def test_attr_call_modpos_args_1_0(self):
        results = self.run(
            """\
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Blending %s")
            """
        )

        assert results == [
            (3, 12, "LOG012 formatting error: 1 % placeholder but 0 arguments"),
        ]

    def test_attr_call_modpos_joined_args_1_0(self):
        results = self.run(
            """\
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Blending" + " " + "%s")
            """
        )

        assert results == [
            (3, 12, "LOG012 formatting error: 1 % placeholder but 0 arguments"),
        ]


class TestLOG013(Ignore015):
    def test_module_call_missing(self):
        results = self.run(
            """\
            import logging
            logging.info("Blending %(fruit)s", {})
            """
        )

        assert results == [
            (2, 13, "LOG013 formatting error: missing key: 'fruit'"),
        ]

    def test_module_call_unreferenced(self):
        results = self.run(
            """\
            import logging
            logging.info("Blending %(fruit)s", {"fruit": fruit, "colour": "yellow"})
            """
        )

        assert results == [
            (2, 35, "LOG013 formatting error: unreferenced key: 'colour'"),
        ]

    def test_module_call_log_missing(self):
        results = self.run(
            """\
            import logging
            logging.log(logging.INFO, "Blending %(fruit)s", {})
            """
        )

        assert results == [
            (2, 26, "LOG013 formatting error: missing key: 'fruit'"),
        ]

    def test_module_call_log_unreferenced(self):
        results = self.run(
            """\
            import logging
            logging.log(
                logging.INFO,
                "Blending %(fruit)s",
                {"fruit": fruit, "colour": "yellow"},
            )
            """
        )

        assert results == [
            (5, 4, "LOG013 formatting error: unreferenced key: 'colour'"),
        ]

    def test_module_call_all_args(self):
        results = self.run(
            """\
            import logging
            logging.info("Blending %(fruit)s", {"fruit": fruit})
            """
        )

        assert results == []

    def test_module_call_kwarg_all_args(self):
        results = self.run(
            """\
            import logging
            logging.info({"fruit": fruit}, msg="Blending %(fruit)s")
            """
        )

        assert results == []

    def test_module_call_log_kwarg(self):
        results = self.run(
            """\
            import logging
            logging.log(logging.INFO, {"fruit": fruit}, msg="Blending %(fruit)s")
            """
        )

        assert results == []

    def test_attr_call_missing(self):
        results = self.run(
            """\
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Blending %(fruit)s", {})
            """
        )

        assert results == [
            (3, 12, "LOG013 formatting error: missing key: 'fruit'"),
        ]

    def test_attr_call_unreferenced(self):
        results = self.run(
            """\
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Blending %(fruit)s", {"fruit": fruit, "colour": "yellow"})
            """
        )

        assert results == [
            (3, 34, "LOG013 formatting error: unreferenced key: 'colour'"),
        ]

    def test_attr_call_log_missing(self):
        results = self.run(
            """\
            import logging
            logger = logging.getLogger(__name__)
            logger.log(logging.INFO, "Blending %(fruit)s", {})
            """
        )

        assert results == [
            (3, 25, "LOG013 formatting error: missing key: 'fruit'"),
        ]

    def test_attr_call_log_unreferenced(self):
        results = self.run(
            """\
            import logging
            logger = logging.getLogger(__name__)
            logger.log(
                logging.INFO,
                "Blending %(fruit)s",
                {"fruit": fruit, "colour": "yellow"},
            )
            """
        )

        assert results == [
            (6, 4, "LOG013 formatting error: unreferenced key: 'colour'"),
        ]


class TestLOG014(Ignore015):
    def test_module_call(self):
        results = self.run(
            """\
            import logging
            logging.info("Uh oh", exc_info=True)
            """
        )

        assert results == [
            (2, 22, "LOG014 avoid exc_info=True outside of exception handlers"),
        ]

    def test_module_call_truthy(self):
        results = self.run(
            """\
            import logging
            logging.info("Uh oh", exc_info=1)
            """
        )

        assert results == [
            (2, 22, "LOG014 avoid exc_info=True outside of exception handlers"),
        ]

    def test_module_call_name(self):
        results = self.run(
            """\
            import logging
            logging.info("Uh oh", exc_info=maybe)
            """
        )

        assert results == []

    def test_attr_call(self):
        results = self.run(
            """\
            import logging
            logger = logging.getLogger(__name__)
            logger.info("Uh oh", exc_info=True)
            """
        )

        assert results == [
            (3, 21, "LOG014 avoid exc_info=True outside of exception handlers"),
        ]


class TestLOG015:
    def test_root_call(self):
        results = run(
            """\
            import logging
            logging.info(...)
            """
        )
        assert results == [
            (2, 0, "LOG015 avoid logging calls on root logger"),
        ]

    def test_root_call_alias(self):
        results = run(
            """\
            import logging as loglog
            loglog.info(...)
            logging = loglog.getLogger(__name__)
            logging.info(...)
            """
        )
        assert results == [
            (2, 0, "LOG015 avoid logging calls on root logger"),
        ]


class TestFlattenStrChain:
    def run(self, source: str) -> str | None:
        tree = ast.parse(dedent(source))
        expr = tree.body[0]
        assert isinstance(expr, ast.Expr)
        return flatten_str_chain(expr.value)

    def test_single_string(self):
        result = self.run(
            """\
            "Five"
            """
        )

        assert result == "Five"

    def test_single_bytes(self):
        result = self.run(
            """\
            b"Five"
            """
        )

        assert result is None

    def test_two_added(self):
        result = self.run(
            """\
            "Five" + " "
            """
        )

        assert result == "Five "

    def test_two_str_bytes(self):
        result = self.run(
            """\
            "Five" + b" "
            """
        )

        assert result is None

    def test_two_bytes_str(self):
        result = self.run(
            """\
            b"Five" + " "
            """
        )

        assert result is None

    def test_three(self):
        result = self.run(
            """\
            "Five" + " " + "little"
            """
        )

        assert result == "Five little"

    def test_two_plus_implicit(self):
        result = self.run(
            """\
            ("Five" " ") + "little"
            """
        )

        assert result == "Five little"
