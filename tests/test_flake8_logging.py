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
