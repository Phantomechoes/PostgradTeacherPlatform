import ast
import inspect
from pathlib import Path

from sqlalchemy.orm import Session

from app.repositories.master_data import (
    AdmissionCatalogRepository,
    SchoolRepository,
)

REPO_PATH = (
    Path(__file__).resolve().parents[1] / "app" / "repositories" / "master_data.py"
)
SERVICE_PATH = Path(__file__).resolve().parents[1] / "app" / "services" / "master_data.py"


def _imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names.add(module)
            for alias in node.names:
                names.add(f"{module}.{alias.name}" if module else alias.name)
                names.add(alias.name)
    return names


def test_school_repository_constructor_accepts_session() -> None:
    signature = inspect.signature(SchoolRepository.__init__)
    assert list(signature.parameters) == ["self", "session"]
    assert signature.parameters["session"].annotation is Session
    SchoolRepository(session=object())  # type: ignore[arg-type]


def test_catalog_repository_constructor_accepts_session() -> None:
    signature = inspect.signature(AdmissionCatalogRepository.__init__)
    assert list(signature.parameters) == ["self", "session"]
    AdmissionCatalogRepository(session=object())  # type: ignore[arg-type]


def test_repository_does_not_import_session_local_or_engine() -> None:
    names = _imported_names(REPO_PATH)
    source = REPO_PATH.read_text(encoding="utf-8")
    assert "SessionLocal" not in names
    assert "create_engine" not in names
    assert "SessionLocal" not in source
    assert "create_engine" not in source
    assert "app.core.database" not in names


def test_repository_does_not_import_pydantic() -> None:
    names = _imported_names(REPO_PATH)
    assert "pydantic" not in names
    assert not any(name.startswith("pydantic") for name in names)
    assert "BaseModel" not in names


def test_repository_does_not_import_fastapi() -> None:
    names = _imported_names(REPO_PATH)
    assert "fastapi" not in names
    assert not any(name.startswith("fastapi") for name in names)


def test_service_does_not_import_fastapi() -> None:
    names = _imported_names(SERVICE_PATH)
    assert "fastapi" not in names
    assert "HTTPException" not in names
