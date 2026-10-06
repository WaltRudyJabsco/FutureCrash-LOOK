#!/usr/bin/env python3
"""Dependency-free structural health report for Future Crash + LOOK.

This is intentionally not a style linter.  It answers the questions that matter
for this codebase: where is cognitive load concentrated, are definitions being
shadowed, and how much of the regression suite is coupled to source spelling.

Usage:
    python3 tools/code_health.py
    python3 tools/code_health.py --json
    python3 tools/code_health.py --check
"""
from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
IGNORED_DIRS = {".git", ".pytest_cache", "__pycache__", ".mypy_cache", ".ruff_cache", "node_modules", ".venv", "venv", "env"}


@dataclass(frozen=True)
class FunctionMetric:
    path: str
    qualname: str
    line: int
    lines: int
    complexity: int


@dataclass(frozen=True)
class FileMetric:
    path: str
    lines: int
    code_lines: int
    functions: int
    classes: int


def _ignored(path: Path) -> bool:
    return any(part in IGNORED_DIRS for part in path.parts)


def _is_python_source(path: Path) -> bool:
    if path.suffix == ".py":
        return True
    if path.suffix or not path.is_file():
        return False
    try:
        with path.open("rb") as handle:
            first=handle.readline(160)
        return first.startswith(b"#!") and b"python" in first
    except OSError:
        return False


def production_files() -> list[Path]:
    out = []
    for path in ROOT.rglob("*"):
        if _ignored(path.relative_to(ROOT)) or "tests" in path.relative_to(ROOT).parts:
            continue
        if path.is_file() and _is_python_source(path):
            out.append(path)
    return sorted(out)


def test_files() -> list[Path]:
    root = ROOT / "tests"
    return sorted(p for p in root.rglob("test_*.py") if not _ignored(p.relative_to(ROOT))) if root.exists() else []


class Complexity(ast.NodeVisitor):
    """Small McCabe-like counter, deliberately conservative and dependency-free."""
    def __init__(self) -> None:
        self.value = 1

    def generic_visit(self, node: ast.AST) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            return
        if isinstance(node, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.IfExp, ast.comprehension)):
            self.value += 1
        elif isinstance(node, ast.BoolOp):
            self.value += max(1, len(node.values) - 1)
        elif isinstance(node, ast.Try):
            self.value += len(node.handlers) + bool(node.orelse) + bool(node.finalbody)
        elif isinstance(node, ast.Match):
            self.value += len(node.cases)
        super().generic_visit(node)


def _function_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    visitor = Complexity()
    for child in node.body:
        visitor.visit(child)
    return visitor.value


def _walk_functions(body: Iterable[ast.stmt], prefix: str = "") -> Iterable[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            qual = f"{prefix}{node.name}"
            yield qual, node
            yield from _walk_functions(node.body, qual + ".<local>.")
        elif isinstance(node, ast.ClassDef):
            yield from _walk_functions(node.body, f"{prefix}{node.name}.")


def _duplicates(body: Iterable[ast.stmt], scope: str = "module") -> list[dict]:
    seen: dict[str, list[int]] = {}
    out: list[dict] = []
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            # property getter/setter pairs intentionally reuse a method name.
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                decorators = {getattr(d, "attr", getattr(d, "id", "")) for d in node.decorator_list}
                if "setter" in decorators:
                    continue
            seen.setdefault(node.name, []).append(node.lineno)
    for name, lines in seen.items():
        if len(lines) > 1:
            out.append({"scope": scope, "name": name, "lines": lines})
    for node in body:
        if isinstance(node, ast.ClassDef):
            out.extend(_duplicates(node.body, f"{scope}.{node.name}"))
    return out


def analyze() -> dict:
    files: list[FileMetric] = []
    functions: list[FunctionMetric] = []
    duplicates: list[dict] = []
    parse_errors: list[dict] = []
    broad_exceptions: dict[str,int] = {}

    for path in production_files():
        rel = str(path.relative_to(ROOT))
        try:
            text = path.read_text(encoding="utf-8")
            tree = ast.parse(text, filename=rel)
        except (OSError, UnicodeError, SyntaxError) as exc:
            parse_errors.append({"path": rel, "error": str(exc)})
            continue
        lines = text.splitlines()
        code_lines = sum(1 for line in lines if line.strip() and not line.lstrip().startswith("#"))
        fn_nodes = list(_walk_functions(tree.body))
        class_count = sum(isinstance(n, ast.ClassDef) for n in ast.walk(tree))
        broad=sum(1 for n in ast.walk(tree) if isinstance(n,ast.ExceptHandler) and isinstance(n.type,ast.Name) and n.type.id=="Exception")
        if broad:
            broad_exceptions[rel]=broad
        files.append(FileMetric(rel, len(lines), code_lines, len(fn_nodes), class_count))
        for qual, node in fn_nodes:
            end = getattr(node, "end_lineno", node.lineno)
            functions.append(FunctionMetric(rel, qual, node.lineno, end - node.lineno + 1, _function_complexity(node)))
        for item in _duplicates(tree.body):
            item["path"] = rel
            duplicates.append(item)

    source_contract_tests = []
    for path in test_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        # Source-spelling tests are useful for release contracts, but a high count
        # predicts churn when internals are simplified.
        if ".read_text(" in text and "assert" in text:
            source_contract_tests.append(str(path.relative_to(ROOT)))

    renderer = (ROOT / "look" / "look_renderer.py").read_text(encoding="utf-8", errors="replace")
    legacy_pager_states = [name for name in ("cursoring", "selecting") if name in renderer]

    return {
        "production_files": len(files),
        "production_lines": sum(f.lines for f in files),
        "production_code_lines": sum(f.code_lines for f in files),
        "functions": sum(f.functions for f in files),
        "classes": sum(f.classes for f in files),
        "tests": len(test_files()),
        "source_contract_tests": len(source_contract_tests),
        "source_contract_test_files": source_contract_tests,
        "parse_errors": parse_errors,
        "duplicate_definitions": duplicates,
        "legacy_pager_states": legacy_pager_states,
        "broad_exception_handlers": sum(broad_exceptions.values()),
        "broad_exception_files": dict(sorted(broad_exceptions.items(), key=lambda item:item[1], reverse=True)),
        "largest_files": [asdict(x) for x in sorted(files, key=lambda x: x.lines, reverse=True)[:15]],
        "largest_functions": [asdict(x) for x in sorted(functions, key=lambda x: x.lines, reverse=True)[:20]],
        "most_complex_functions": [asdict(x) for x in sorted(functions, key=lambda x: (x.complexity, x.lines), reverse=True)[:20]],
    }


def _print(report: dict) -> None:
    print("FUTURE CRASH + LOOK · CODE HEALTH")
    print("=" * 42)
    print(f"production  {report['production_files']} files · {report['production_lines']:,} lines · {report['functions']:,} functions · {report['classes']:,} classes")
    print(f"tests       {report['tests']} files · {report['source_contract_tests']} source-contract files")
    print(f"parsing     {'clean' if not report['parse_errors'] else str(len(report['parse_errors']))+' error(s)'}")
    print(f"duplicates  {len(report['duplicate_definitions'])}")
    print(f"pager       {'Browse ↔ Filter only' if not report['legacy_pager_states'] else 'legacy states: '+', '.join(report['legacy_pager_states'])}")
    print(f"exceptions  {report['broad_exception_handlers']} broad edge catches (informational)")

    print("\nLargest files")
    for row in report["largest_files"][:10]:
        print(f"  {row['lines']:>6}  {row['path']}")

    print("\nLargest functions")
    for row in report["largest_functions"][:12]:
        print(f"  {row['lines']:>6} lines  C={row['complexity']:<4} {row['path']}:{row['line']}  {row['qualname']}")

    print("\nHighest branch complexity")
    for row in report["most_complex_functions"][:12]:
        print(f"  C={row['complexity']:<4} {row['lines']:>6} lines  {row['path']}:{row['line']}  {row['qualname']}")

    if report["duplicate_definitions"]:
        print("\nDuplicate definitions")
        for row in report["duplicate_definitions"]:
            print(f"  {row['path']} · {row['scope']}.{row['name']} · lines {row['lines']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument("--check", action="store_true", help="fail on structural invariants that should always be clean")
    args = parser.parse_args()
    report = analyze()
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        _print(report)
    if args.check and (report["parse_errors"] or report["duplicate_definitions"] or report["legacy_pager_states"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
