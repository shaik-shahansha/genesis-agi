"""Migration-chain guards.

These exist because of a real, repeated authoring mistake: a column declared
`index=True` inside `op.create_table(...)` already emits `CREATE INDEX
ix_<table>_<column>`, and a following explicit `op.create_index(...)` with the
same name raised "index ... already exists". Three migrations had it, so
`alembic upgrade head` could not complete on a fresh database at all — every
later revision was unreachable through the documented migration path, which is
exactly how the governance tables would have failed to appear on a new install.

`tests/governance/test_migrations.py`-style AST guards are used elsewhere in this
repo (see `tests/security/test_sandbox_boundary.py`); this is the same idea
applied to migrations.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

VERSIONS_DIR = Path(__file__).resolve().parents[1] / "alembic" / "versions"


def _migration_files() -> list[Path]:
    return sorted(path for path in VERSIONS_DIR.glob("*.py") if path.name != "__init__.py")


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))


def test_migration_directory_is_not_empty():
    assert _migration_files()


def _create_index_names(tree: ast.Module) -> set[str]:
    """Every index name passed to ``op.create_index`` in this module."""
    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "create_index":
            continue
        if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            names.add(node.args[0].value)
    return names


def _indexed_columns(tree: ast.Module) -> list[tuple[str, str, str]]:
    """(table, column, implied_index_name) for every ``index=True`` column."""
    found: list[tuple[str, str, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "create_table":
            continue
        if not node.args or not isinstance(node.args[0], ast.Constant):
            continue
        table = node.args[0].value
        if not isinstance(table, str):
            continue
        for argument in node.args[1:]:
            if not isinstance(argument, ast.Call):
                continue
            column_func = argument.func
            if not isinstance(column_func, ast.Attribute) or column_func.attr != "Column":
                continue
            if not argument.args or not isinstance(argument.args[0], ast.Constant):
                continue
            column = argument.args[0].value
            indexed = any(
                keyword.arg == "index"
                and isinstance(keyword.value, ast.Constant)
                and keyword.value.value is True
                for keyword in argument.keywords
            )
            if indexed and isinstance(column, str):
                found.append((table, column, f"ix_{table}_{column}"))
    return found


@pytest.mark.parametrize("path", _migration_files(), ids=lambda p: p.name)
def test_no_duplicate_index_creation(path: Path):
    """A column-level index must not also be created explicitly.

    SQLAlchemy derives the index name as ``ix_<table>_<column>`` for
    ``index=True``, so an explicit ``create_index`` with that same name is a
    duplicate that fails at upgrade time rather than at review time.
    """
    tree = _parse(path)
    explicit = _create_index_names(tree)
    duplicates = [
        (table, column, name)
        for table, column, name in _indexed_columns(tree)
        if name in explicit
    ]
    assert not duplicates, (
        f"{path.name} creates the same index twice: {duplicates}. "
        "Remove the explicit op.create_index call (index=True already creates it), "
        "or rename the explicit index if a differently named one is intended."
    )


@pytest.mark.parametrize("path", _migration_files(), ids=lambda p: p.name)
def test_every_migration_has_a_revision_and_down_revision(path: Path):
    """A revision chain with a missing down_revision silently orphans migrations."""
    source = path.read_text(encoding="utf-8-sig")
    assert "revision: str" in source or "revision = " in source, f"{path.name} has no revision id"
    assert "down_revision" in source, f"{path.name} has no down_revision"


@pytest.mark.parametrize("path", _migration_files(), ids=lambda p: p.name)
def test_every_migration_has_a_downgrade(path: Path):
    """Every upgrade must be reversible, or a rollback leaves a half-migrated DB."""
    tree = _parse(path)
    functions = {
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    assert "upgrade" in functions, f"{path.name} defines no upgrade()"
    assert "downgrade" in functions, f"{path.name} defines no downgrade()"


def _module_constants(tree: ast.Module) -> dict[str, ast.expr]:
    """Top-level ``revision`` / ``down_revision`` assignments.

    Handles both plain assignment and annotated assignment: alembic's template
    emits ``revision: str = '...'`` and ``down_revision: Union[str, None] = ...``,
    which are ``AnnAssign`` nodes.
    """
    values: dict[str, ast.expr] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            target = node.targets[0] if node.targets else None
            if isinstance(target, ast.Name):
                values[target.id] = node.value
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.value is not None:
                values[node.target.id] = node.value
    return values


def _revision_graph() -> dict[str, object]:
    graph: dict[str, object] = {}
    for path in _migration_files():
        tree = _parse(path)
        values = _module_constants(tree)
        revision_node = values.get("revision")
        if not isinstance(revision_node, ast.Constant) or not isinstance(revision_node.value, str):
            continue
        down_node = values.get("down_revision")
        if isinstance(down_node, ast.Constant):
            down: object = down_node.value
        elif isinstance(down_node, (ast.Tuple, ast.List)):
            down = tuple(
                element.value
                for element in down_node.elts
                if isinstance(element, ast.Constant)
            )
        else:
            down = None
        graph[revision_node.value] = down
    return graph


def test_revision_graph_is_a_single_linear_chain():
    """One head, or `alembic upgrade head` is ambiguous."""
    revisions = _revision_graph()

    assert revisions, "no revisions found"
    parents = {
        down for down in revisions.values() if isinstance(down, str)
    }
    heads = [revision for revision in revisions if revision not in parents]
    assert len(heads) == 1, f"expected exactly one head, found {sorted(heads)}"
    assert None in revisions.values(), "no root revision (down_revision = None)"


def test_every_down_revision_resolves():
    """A typo in a down_revision silently orphans the rest of the chain."""
    revisions = _revision_graph()
    for revision, down in revisions.items():
        if down is None:
            continue
        for parent in down if isinstance(down, tuple) else (down,):
            assert parent in revisions, (
                f"revision {revision} points at unknown down_revision {parent!r}"
            )


def test_governance_revision_is_reachable_from_the_head():
    """The governance plane must be reachable, not orphaned behind a broken chain.

    Asserting the *chain reaches it* rather than that it *is* the head: pinning
    the head by name means every later revision fails this test and has to edit
    it, which trains people to update the assertion instead of reading it. What
    actually matters is that `alembic upgrade head` applies the governance
    tables.
    """
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config(str(VERSIONS_DIR.parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(VERSIONS_DIR.parent))
    script = ScriptDirectory.from_config(config)

    heads = script.get_heads()
    assert len(heads) == 1, f"expected exactly one head, found {heads}"

    # Walk down from the head and confirm the governance revision is an ancestor.
    ancestry = [rev.revision for rev in script.walk_revisions(base="base", head="heads")]
    assert "008_governance_plane" in ancestry, (
        "008_governance_plane is no longer reachable from head; the governance "
        "tables will not be created on a fresh database"
    )
