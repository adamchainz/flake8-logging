from __future__ import annotations

import ast
import sys
from contextlib import contextmanager
from importlib.metadata import version
from typing import Any
from typing import Generator


class Plugin:
    name = "flake8-logging"
    version = version("flake8-logging")

    def __init__(self, tree: ast.AST) -> None:
        self._tree = tree

    def run(self) -> Generator[tuple[int, int, str, type[Any]], None, None]:
        visitor = Visitor()
        visitor.visit(self._tree)

        type_ = type(self)
        for line, col, msg in visitor.errors:
            yield line, col, msg, type_


logger_methods = frozenset(
    (
        "debug",
        "info",
        "warning",
        "error",
        "critical",
        "log",
        "exception",
    )
)
logrecord_attributes = frozenset(
    (
        "asctime",
        "args",
        "created",
        "exc_info",
        "exc_text",
        "filename",
        "funcName",
        "levelname",
        "levelno",
        "lineno",
        "module",
        "msecs",
        "msg",
        "name",
        "pathname",
        "process",
        "processName",
        "relativeCreated",
        "stack_info",
        "taskName",
        "thread",
        "threadName",
    )
)

LOG001 = "LOG001 use logging.getLogger() to instantiate loggers"
LOG002 = "LOG002 use __name__ with getLogger()"
LOG002_names = frozenset(
    (
        "__cached__",
        "__file__",
    )
)
LOG003 = "LOG003 extra key {} clashes with LogRecord attribute"
LOG004 = "LOG004 avoid logger.exception() outside of except clauses"


class Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.errors: list[tuple[int, int, str]] = []
        self._logging_name: str | None = None
        self._logger_name: str | None = None
        self._from_imports: dict[str, str] = {}
        self._module_level = True
        self._stack: list[ast.AST] = []

    def visit(self, node: ast.AST) -> None:
        self._stack.append(node)
        super().visit(node)
        self._stack.pop()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "logging":
                self._logging_name = alias.asname or alias.name
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if node.module is not None and not alias.asname:
                self._from_imports[alias.name] = node.module
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if (
            self._module_level
            and self._logging_name
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "Logger"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == self._logging_name
        ) or (
            isinstance(node.func, ast.Name)
            and node.func.id == "Logger"
            and self._from_imports.get("Logger") == "logging"
        ):
            self.errors.append((node.lineno, node.col_offset, LOG001))

        if (
            self._logging_name
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "getLogger"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == self._logging_name
        ) or (
            isinstance(node.func, ast.Name)
            and node.func.id == "getLogger"
            and self._from_imports.get("getLogger") == "logging"
        ):
            if (
                self._module_level
                and len(self._stack) >= 2
                and isinstance(assign := self._stack[-2], ast.Assign)
                and len(assign.targets) == 1
                and isinstance(assign.targets[0], ast.Name)
            ):
                self._logger_name = assign.targets[0].id

            if (
                node.args
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id in LOG002_names
            ):
                self.errors.append(
                    (node.args[0].lineno, node.args[0].col_offset, LOG002),
                )

        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in logger_methods
            and isinstance(node.func.value, ast.Name)
        ) and (
            (self._logging_name and node.func.value.id == self._logging_name)
            or (self._logger_name and node.func.value.id == self._logger_name)
        ):
            # L003
            extra_keys = ()
            if any((extra_node := kw).arg == "extra" for kw in node.keywords):
                if isinstance(extra_node.value, ast.Dict):
                    extra_keys = [
                        (k.value, k)
                        for k in extra_node.value.keys
                        if isinstance(k, ast.Constant)
                    ]
                elif (
                    isinstance(extra_node.value, ast.Call)
                    and isinstance(extra_node.value.func, ast.Name)
                    and extra_node.value.func.id == "dict"
                ):
                    extra_keys = [(k.arg, k) for k in extra_node.value.keywords]

            for key, key_node in extra_keys:
                if key in logrecord_attributes:
                    if sys.version_info >= (3, 9):
                        lineno = key_node.lineno
                        col_offset = key_node.col_offset
                    else:
                        if isinstance(key_node, ast.keyword):
                            lineno = key_node.value.lineno
                            # Educated guess
                            col_offset = max(
                                0, key_node.value.col_offset - 1 - len(key)
                            )
                        else:
                            lineno = key_node.lineno
                            col_offset = key_node.col_offset

                    self.errors.append(
                        (
                            lineno,
                            col_offset,
                            LOG003.format(repr(key)),
                        )
                    )

            # L004
            if node.func.attr == "exception":
                within_except = False
                for parent in reversed(self._stack):
                    if isinstance(parent, ast.ExceptHandler):
                        within_except = True
                        break
                    elif isinstance(parent, (ast.AsyncFunctionDef, ast.FunctionDef)):
                        break
                if not within_except:
                    self.errors.append(
                        (node.lineno, node.col_offset, LOG004),
                    )

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        with self.inner_scope():
            self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        with self.inner_scope():
            self.generic_visit(node)

    @contextmanager
    def inner_scope(self) -> Generator[None, None, None]:
        original = self._module_level
        self._module_level = False
        try:
            yield
        finally:
            self._module_level = original
