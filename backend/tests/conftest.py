"""Test fixtures.

The test database is pointed at a throwaway file *before* the app is
imported, so tests never touch the development `smartbasket.db`.
"""

import os
import tempfile
from pathlib import Path

TEST_DB = Path(tempfile.mkdtemp(prefix="smartbasket-test-")) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB.as_posix()}"
# Force the offline assistant: tests must never call a paid API, and must
# not depend on a key being present in the developer's .env.
os.environ["AI_PROVIDER"] = "offline"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["OPENAI_API_KEY"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session, SQLModel  # noqa: E402

import app.models  # noqa: E402,F401  (registers tables on the metadata)
from app.db import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    """A client against a freshly seeded, empty-of-history database."""
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        seed(session)

    # Not used as a context manager on purpose: that would run the app's
    # lifespan, which is unnecessary here since the schema is already created.
    return TestClient(app)


@pytest.fixture
def db() -> Session:
    with Session(engine) as session:
        yield session


def barcode_of(client: TestClient, name: str) -> str:
    """Find a seeded product's barcode by its exact display name."""
    products = client.get("/api/products").json()
    for product in products:
        if product["name"] == name:
            return product["barcode"]
    raise AssertionError(f"Seed data has no product named {name!r}")
