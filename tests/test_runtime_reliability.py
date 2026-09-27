import sys
from threading import Event
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.database import session as session_module
from src.utils.scheduler import BackgroundScheduler


def test_background_scheduler_can_run_first_job_without_blocking_startup():
    completed = Event()
    scheduler = BackgroundScheduler(
        name="test-immediate-job",
        interval_seconds=60,
        job=completed.set,
        run_immediately=True,
    )

    scheduler.start()
    try:
        assert completed.wait(timeout=1)
    finally:
        scheduler.stop()


def test_postgresql_engine_uses_bounded_resilient_pool_options(monkeypatch):
    captured = {}
    expected_engine = object()

    def fake_create_engine(database_url, **kwargs):
        captured["database_url"] = database_url
        captured["kwargs"] = kwargs
        return expected_engine

    monkeypatch.setattr(session_module, "create_engine", fake_create_engine)

    engine = session_module.build_engine(
        "postgresql+psycopg://latent:secret@db.example.com/latent",
        pool_size=2,
        max_overflow=3,
        connect_timeout_seconds=8,
        pool_timeout_seconds=10,
        pool_recycle_seconds=900,
        ssl_mode="require",
    )

    assert engine is expected_engine
    assert captured["kwargs"] == {
        "connect_args": {"sslmode": "require", "connect_timeout": 8},
        "pool_pre_ping": True,
        "pool_size": 2,
        "max_overflow": 3,
        "pool_timeout": 10,
        "pool_recycle": 900,
        "pool_use_lifo": True,
    }
