# backend/tests/test_db.py
import pytest
from app.core.db import Base, make_engine, make_session_factory, session_scope
from sqlalchemy import Column, Integer, String


class ScratchRow(Base):
    __tablename__ = "scratch_row"
    id = Column(Integer, primary_key=True)
    name = Column(String(32), nullable=False)


def _fresh_session_factory():
    engine = make_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return make_session_factory(engine)


def test_session_scope_commits_on_success():
    session_factory = _fresh_session_factory()
    with session_scope(session_factory) as session:
        session.add(ScratchRow(name="ok"))
    with session_scope(session_factory) as session:
        assert session.query(ScratchRow).count() == 1


def test_session_scope_rolls_back_on_error():
    session_factory = _fresh_session_factory()
    with pytest.raises(ValueError):
        with session_scope(session_factory) as session:
            session.add(ScratchRow(name="a"))
            raise ValueError("boom")
    with session_scope(session_factory) as session:
        assert session.query(ScratchRow).count() == 0
