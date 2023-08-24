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
            select = L
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


class TestL001:
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
            "./example.py:2:1: L001 use logging.getLogger() to instantiate loggers"
        ]

    def test_attr(self):
        results = run(
            """\
            import logging
            logging.Logger("x")
            """
        )

        assert results == [
            (2, 0, "L001 use logging.getLogger() to instantiate loggers")
        ]

    def test_attr_as_name(self):
        results = run(
            """\
            import logging as lm
            lm.Logger("x")
            """
        )

        assert results == [
            (2, 0, "L001 use logging.getLogger() to instantiate loggers")
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
            (3, 13, "L001 use logging.getLogger() to instantiate loggers")
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
            (2, 0, "L001 use logging.getLogger() to instantiate loggers")
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

    def test_in_async_function_def(self):
        results = run(
            """\
            import logging
            async def test_thing():
                logging.Logger("x")
            """
        )

        assert results == []


class TestL002:
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
            "./example.py:2:19: L002 use __name__ with getLogger()"
        ]

    def test_attr(self):
        results = run(
            """\
            import logging
            logging.getLogger(__file__)
            """
        )

        assert results == [(2, 18, "L002 use __name__ with getLogger()")]

    def test_attr_cached(self):
        results = run(
            """\
            import logging
            logging.getLogger(__cached__)
            """
        )

        assert results == [(2, 18, "L002 use __name__ with getLogger()")]

    def test_attr_in_function_def(self):
        results = run(
            """\
            import logging
            def thing():
                logging.getLogger(__file__)
            """
        )

        assert results == [(3, 22, "L002 use __name__ with getLogger()")]

    def test_direct(self):
        results = run(
            """\
            from logging import getLogger
            getLogger(__file__)
            """
        )

        assert results == [(2, 10, "L002 use __name__ with getLogger()")]

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


class TestL003:
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
            "./example.py:2:27: L003 extra key 'msg' clashes with LogRecord attribute"
        ]

    def test_module_call(self):
        results = run(
            """\
            import logging
            logging.info("Hi", extra={"msg": "Ho"})
            """
        )

        assert results == [
            (2, 26, "L003 extra key 'msg' clashes with LogRecord attribute")
        ]

    def test_module_call_debug(self):
        results = run(
            """\
            import logging
            logging.debug("Hi", extra={"msg": "Ho"})
            """
        )

        assert results == [
            (2, 27, "L003 extra key 'msg' clashes with LogRecord attribute")
        ]

    def test_module_call_args(self):
        results = run(
            """\
            import logging
            logging.info("Hi", extra={"args": (1,)})
            """
        )

        assert results == [
            (2, 26, "L003 extra key 'args' clashes with LogRecord attribute")
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
            (5, 8, "L003 extra key 'msg' clashes with LogRecord attribute")
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
            (5, 8, "L003 extra key 'args' clashes with LogRecord attribute"),
            (6, 8, "L003 extra key 'msg' clashes with LogRecord attribute"),
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
            (3, 30, "L003 extra key 'msg' clashes with LogRecord attribute")
        ]

    def test_module_call_dict_constructor(self):
        results = run(
            """\
            import logging
            logging.info("Hi", extra=dict(msg="Ho"))
            """
        )

        assert results == [
            (2, 30, "L003 extra key 'msg' clashes with LogRecord attribute")
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
            (3, 25, "L003 extra key 'msg' clashes with LogRecord attribute")
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
            (3, 22, "L003 extra key 'msg' clashes with LogRecord attribute")
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
            (3, 29, "L003 extra key 'msg' clashes with LogRecord attribute")
        ]
