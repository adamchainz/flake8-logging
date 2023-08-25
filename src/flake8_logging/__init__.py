from __future__ import annotations

import ast
import sys
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
        "warn",
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
LOG004 = "LOG004 avoid exception() outside of exception handlers"
LOG005 = "LOG005 use exception() within an exception handler"
LOG006 = "LOG006 redundant exc_info argument for exception()"
LOG007 = "LOG007 use error() instead of exception() with exc_info=False"
LOG008 = "LOG008 warn() is deprecated, use warning() instead"
LOG009 = "LOG009 WARN is undocumented, use WARNING instead"


class Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.errors: list[tuple[int, int, str]] = []
        self._logging_name: str | None = None
        self._logger_name: str | None = None
        self._from_imports: dict[str, str] = {}
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
        if node.module == "logging":
            for alias in node.names:
                if alias.name == "WARN":
                    if sys.version_info >= (3, 10):
                        lineno = alias.lineno
                        col_offset = alias.col_offset
                    else:
                        lineno = node.lineno
                        col_offset = node.col_offset
                    self.errors.append((lineno, col_offset, LOG009))
                if not alias.asname:
                    self._from_imports[alias.name] = node.module
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if (
            self._logging_name
            and isinstance(node.value, ast.Name)
            and node.value.id == self._logging_name
            and node.attr == "WARN"
        ):
            self.errors.append((node.lineno, node.col_offset, LOG009))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if (
            (
                self._logging_name
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "Logger"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == self._logging_name
            )
            or (
                isinstance(node.func, ast.Name)
                and node.func.id == "Logger"
                and self._from_imports.get("Logger") == "logging"
            )
        ) and not self._at_module_level():
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
                len(self._stack) >= 2
                and isinstance(assign := self._stack[-2], ast.Assign)
                and len(assign.targets) == 1
                and isinstance(assign.targets[0], ast.Name)
                and not self._at_module_level()
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
            # LOG008
            if node.func.attr == "warn":
                self.errors.append((node.lineno, node.col_offset, LOG008))

            # LOG003
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
                    if isinstance(key_node, ast.keyword):
                        lineno, col_offset = keyword_pos(key_node)
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

            if node.func.attr == "exception":
                handler = self._current_except_handler()

                # LOG004
                if not handler:
                    self.errors.append(
                        (node.lineno, node.col_offset, LOG004),
                    )

                if any((exc_info := kw).arg == "exc_info" for kw in node.keywords):
                    # LOG006
                    if (
                        isinstance(exc_info.value, ast.Constant)
                        and exc_info.value.value
                    ) or (
                        handler
                        and isinstance(exc_info.value, ast.Name)
                        and exc_info.value.id == handler.name
                    ):
                        self.errors.append(
                            (*keyword_pos(exc_info), LOG006),
                        )

                    # LOG007
                    elif (
                        isinstance(exc_info.value, ast.Constant)
                        and not exc_info.value.value
                    ):
                        self.errors.append(
                            (*keyword_pos(exc_info), LOG007),
                        )

            # LOG005
            elif node.func.attr == "error" and (
                handler := self._current_except_handler()
            ):
                rewritable = False
                if any((exc_info := kw).arg == "exc_info" for kw in node.keywords):
                    if (
                        isinstance(exc_info.value, ast.Constant)
                        and exc_info.value.value
                    ):
                        rewritable = True
                    elif (
                        isinstance(exc_info.value, ast.Name)
                        and exc_info.value.id == handler.name
                    ):
                        rewritable = True
                else:
                    rewritable = True

                if rewritable:
                    self.errors.append(
                        (node.lineno, node.col_offset, LOG005),
                    )

        self.generic_visit(node)

    def _at_module_level(self):
        return any(
            isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef))
            for parent in self._stack
        )

    def _current_except_handler(self) -> ast.ExceptHandler | None:
        for node in reversed(self._stack):
            if isinstance(node, ast.ExceptHandler):
                return node
            elif isinstance(node, (ast.AsyncFunctionDef, ast.FunctionDef)):
                break
        return None


def keyword_pos(node: ast.keyword) -> tuple[int, int]:
    if sys.version_info >= (3, 9):
        return (node.lineno, node.col_offset)
    else:
        # Educated guess
        return (
            node.value.lineno,
            max(0, node.value.col_offset - 1 - len(node.arg)),
        )
