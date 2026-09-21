from collections.abc import Generator
from unittest.mock import MagicMock

import pytest

from app.core import database
from app.core.database import get_db, get_write_db


def _run(gen: Generator) -> None:
    try:
        next(gen)
        next(gen)
    except StopIteration:
        return


def test_get_db_does_not_commit_or_rollback(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    monkeypatch.setattr(database, "SessionLocal", lambda: session)

    _run(get_db())

    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.close.assert_called_once()


def test_get_write_db_commits_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    monkeypatch.setattr(database, "SessionLocal", lambda: session)

    _run(get_write_db())

    session.commit.assert_called_once()
    session.rollback.assert_not_called()
    session.close.assert_called_once()


def test_get_write_db_rollbacks_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    session = MagicMock()
    monkeypatch.setattr(database, "SessionLocal", lambda: session)
    gen = get_write_db()
    next(gen)

    with pytest.raises(RuntimeError, match="boom"):
        gen.throw(RuntimeError("boom"))

    session.commit.assert_not_called()
    session.rollback.assert_called_once()
    session.close.assert_called_once()
