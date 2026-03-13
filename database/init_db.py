import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "schema.sql"
DB_PATH = BASE_DIR.parent / "production.db"


def init_db() -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with sqlite3.connect(DB_PATH) as connection:
        connection.executescript(schema_sql)

    print(f"Database created successfully: {DB_PATH}")


if __name__ == "__main__":
    init_db()
