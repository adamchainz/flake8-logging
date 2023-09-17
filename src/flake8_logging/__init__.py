from __future__ import annotations

import ast
import re
import sys
from functools import lru_cache
from importlib.metadata import version
from typing import Any
from typing import Generator
from typing import Sequence


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


@lru_cache(maxsize=None)
def modpos_placeholder_re() -> re.Pattern[str]:
    # https://docs.python.org/3/library/stdtypes.html#printf-style-string-formatting
    return re.compile(
        r"""
            %
            ([-#0 +]+)?  # conversion flags
            (?P<minwidth>\d+|\*)?  # minimum field width
            (?P<precision>\.\d+|\.\*)?  # precision
            [hlL]?  # length modifier
            [acdeEfFgGiorsuxX]  # conversion type
        """,
        re.VERBOSE,
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
LOG010 = "LOG010 exception() does not take an exception"
LOG011 = "LOG011 avoid pre-formatting log messages"
LOG012 = "LOG012 formatting error: {n} {style} placeholder{ns} but {m} argument{ms}"


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
            extra_keys: Sequence[tuple[str, ast.AST]] = ()
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
                    extra_keys = [
                        (k.arg, k)
                        for k in extra_node.value.keywords
                        if k.arg is not None
                    ]

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

            # LOG010
            if (
                node.func.attr == "exception"
                and len(node.args) >= 1
                and isinstance(node.args[0], ast.Name)
                and (exc_handler := self._current_except_handler()) is not None
                and node.args[0].id == exc_handler.name
            ):
                self.errors.append(
                    (node.args[0].lineno, node.args[0].col_offset, LOG010)
                )

            msg_arg_kwarg = False
            if node.func.attr == "log" and len(node.args) >= 2:
                msg_arg = node.args[1]
            elif node.func.attr != "log" and len(node.args) >= 1:
                msg_arg = node.args[0]
            else:
                try:
                    msg_arg = [k for k in node.keywords if k.arg == "msg"][0].value
                    msg_arg_kwarg = True
                except IndexError:
                    msg_arg = None

            # LOG011
            if (
                isinstance(msg_arg, ast.JoinedStr)
                or (
                    isinstance(msg_arg, ast.Call)
                    and isinstance(msg_arg.func, ast.Attribute)
                    and isinstance(msg_arg.func.value, ast.Constant)
                    and isinstance(msg_arg.func.value.value, str)
                    and msg_arg.func.attr == "format"
                )
                or (
                    isinstance(msg_arg, ast.BinOp)
                    and isinstance(msg_arg.op, ast.Mod)
                    and isinstance(msg_arg.left, ast.Constant)
                    and isinstance(msg_arg.left.value, str)
                )
                or (
                    isinstance(msg_arg, ast.BinOp)
                    and is_add_chain_with_non_str(msg_arg)
                )
            ):
                self.errors.append((msg_arg.lineno, msg_arg.col_offset, LOG011))

            # LOG012
            if (
                msg_arg is not None
                and not msg_arg_kwarg
                and (msg := flatten_str_chain(msg_arg))
            ):
                modpos_count = sum(
                    1 + (m["minwidth"] == "*") + (m["precision"] == ".*")
                    for m in modpos_placeholder_re().finditer(msg)
                )
                arg_count = len(node.args) - 1 - (node.func.attr == "log")

                if modpos_count > 0 and modpos_count != arg_count:
                    self.errors.append(
                        (
                            msg_arg.lineno,
                            msg_arg.col_offset,
                            LOG012.format(
                                n=modpos_count,
                                ns="s" if modpos_count != 1 else "",
                                style="%",
                                m=arg_count,
                                ms="s" if arg_count != 1 else "",
                            ),
                        )
                    )

        self.generic_visit(node)

    def _at_module_level(self) -> bool:
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


def is_add_chain_with_non_str(node: ast.BinOp) -> bool:
    if not isinstance(node.op, ast.Add):
        return False

    for side in (node.left, node.right):
        if isinstance(side, ast.BinOp):
            if is_add_chain_with_non_str(side):
                return True
        elif not (isinstance(side, ast.Constant) and isinstance(side.value, str)):
            return True

    return False


def flatten_str_chain(node: ast.AST) -> str | None:
    parts = []

    def visit(node: ast.AST) -> bool:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            parts.append(node.value)
            return True
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return visit(node.left) and visit(node.right)
        return False

    result = visit(node)
    if not result:
        return None
    if len(parts) == 1:
        return parts[0]
    else:
        return "".join(parts)
