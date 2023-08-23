from __future__ import annotations

import ast
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


L001 = "L001 use logging.getLogger() to instantiate loggers"
L002 = "L002 use __name__ with getLogger()"
L002_names = frozenset(
    (
        "__cached__",
        "__file__",
    )
)


class Visitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.errors: list[tuple[int, int, str]] = []
        self._logging_name: str | None = None
        self._from_imports: dict[str, str] = {}

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
            self._logging_name
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "Logger"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == self._logging_name
        ) or (
            isinstance(node.func, ast.Name)
            and node.func.id == "Logger"
            and self._from_imports.get("Logger") == "logging"
        ):
            self.errors.append((node.lineno, node.col_offset, L001))

        if (
            (
                self._logging_name
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "getLogger"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == self._logging_name
            )
            or (
                isinstance(node.func, ast.Name)
                and node.func.id == "getLogger"
                and self._from_imports.get("getLogger") == "logging"
            )
        ) and (
            node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id in L002_names
        ):
            self.errors.append((node.args[0].lineno, node.args[0].col_offset, L002))

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Avoid descending into a new scope
        return None

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        # Avoid descending into a new scope
        return None
