"""Packaging contract tests.

These guard configuration that is easy to delete by accident and whose absence
is only discovered later, as a broken APK build. If one of these fails, the
Android build is broken even though every other test passes.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:  # Python 3.10 - declared in [project.optional-dependencies].dev
    import tomli as tomllib  # type: ignore[no-redef]

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = PROJECT_ROOT / "pyproject.toml"


def _load_pyproject() -> dict:
    with PYPROJECT.open("rb") as handle:
        return tomllib.load(handle)


def test_pyproject_exists():
    assert PYPROJECT.is_file()


def test_entry_point_points_at_src_main():
    data = _load_pyproject()
    app = data["tool"]["flet"]["app"]
    assert app["path"] == "src"
    assert app["module"] == "main"


def test_entry_point_file_exists():
    assert (PROJECT_ROOT / "src" / "main.py").is_file()


def test_usb_host_feature_is_declared_required():
    """Without this the app advertises itself on devices it cannot use."""
    data = _load_pyproject()
    feature = data["tool"]["flet"]["android"]["feature"]
    assert feature["android.hardware.usb.host"] is True


def test_allow_backup_is_disabled():
    """A repair tool must not restore stale app state onto a new device."""
    data = _load_pyproject()
    manifest = data["tool"]["flet"]["android"]["manifest_application"]
    assert manifest["allowBackup"] == "false"


def test_pyjnius_is_an_android_dependency():
    """pyjnius is the whole reason Python can reach UsbManager."""
    data = _load_pyproject()
    deps = data["tool"]["flet"]["android"]["dependencies"]
    assert "pyjnius" in deps


def test_flet_is_capped_below_1_0():
    """Flet 1.0 removed ft.ElevatedButton; an unpinned range would let a fresh
    `uv sync` (CI, or the APK build script) resolve 1.0 and break the build.

    Guarded on the raw text because the requirement string is data, not a
    parsed structure: tomllib gives it back verbatim, but a rewrite of this
    file could legitimately reformat the table, and the point of the test is
    the cap itself surviving.
    """
    text = PYPROJECT.read_text(encoding="utf-8")
    assert re.search(r'"flet[><=~!^]*[0-9][^"]*,\s*<1(\.0)?[0-9.]*"', text) is not None, (
        "flet must stay capped below 1.0 (e.g. 'flet>=0.85.2,<1.0'); Flet 1.0 "
        "removed the API this app uses"
    )


def _imported_modules(path: Path) -> set[str]:
    """Top-level module names imported by a source file (comments excluded)."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module.split(".")[0])
    return modules


def test_pure_layers_do_not_import_flet():
    """Layering contract: only components/ and views/ may depend on Flet.

    Checked via the AST rather than a text search, so a mention of Flet in a
    docstring does not count as a dependency.
    """
    offenders: list[str] = []
    for layer in ("core", "services", "protocols"):
        for path in sorted((PROJECT_ROOT / "src" / "mobi_tool" / layer).rglob("*.py")):
            if "flet" in _imported_modules(path):
                offenders.append(str(path.relative_to(PROJECT_ROOT)))
    assert offenders == [], f"Flet leaked into a pure layer: {offenders}"


def test_components_and_views_do_import_flet():
    """The UI layers should actually be UI layers."""
    for layer in ("components", "views"):
        modules: set[str] = set()
        for path in sorted((PROJECT_ROOT / "src" / "mobi_tool" / layer).rglob("*.py")):
            modules |= _imported_modules(path)
        assert "flet" in modules, f"{layer}/ does not import flet"


def test_version_is_declared_in_one_place():
    data = _load_pyproject()
    assert data["project"]["version"] == "0.1.0"
