import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BASE_DIR / "schema.sql"
DB_PATH = BASE_DIR.parent / "production.db"

TARGET_TABLES = {
    "projects",
    "types",
    "items",
    "routes",
    "type_batches",
    "batch_items",
    "batch_item_stages",
    "transfers",
    "locations",
}


def table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    cursor = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    )
    return cursor.fetchone() is not None


def get_table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    cursor = connection.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def prepare_schema(connection: sqlite3.Connection) -> None:
    # Удаляем таблицы, которые больше не используются в batch-модели v1.
    for table_name in ("stages", "history"):
        connection.execute(f"DROP TABLE IF EXISTS {table_name}")

    # Проверяем transfers на соответствие новой структуре.
    if table_exists(connection, "transfers"):
        transfer_columns = get_table_columns(connection, "transfers")
        expected_columns = {"id", "batch_id", "date", "location_id", "comment"}
        if transfer_columns != expected_columns:
            connection.execute("DROP TABLE IF EXISTS transfers")

    # Удаляем любые лишние пользовательские таблицы, чтобы итоговая схема была целевой.
    cursor = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        """
    )
    existing_tables = {row[0] for row in cursor.fetchall()}
    extra_tables = sorted(existing_tables - TARGET_TABLES)
    for table_name in extra_tables:
        connection.execute(f"DROP TABLE IF EXISTS {table_name}")


def init_db() -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        prepare_schema(connection)
        connection.executescript(schema_sql)

        cursor = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        )
        tables = [row[0] for row in cursor.fetchall()]

    print("База production.db успешно инициализирована.")
    print("Актуальные таблицы:")
    for table_name in tables:
        print(f"- {table_name}")


if __name__ == "__main__":
    init_db()
