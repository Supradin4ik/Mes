import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "production.db"

TABLES_TO_CLEAR = [
    "blocks",
    "transfers",
    "batch_item_stages",
    "batch_items",
    "type_batches",
    "routes",
    "items",
    "types",
    "projects",
    "locations",
]

REQUIRED_TABLES = set(TABLES_TO_CLEAR)


def get_table_columns(cursor: sqlite3.Cursor, table_name: str) -> set[str]:
    cursor.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def ensure_required_tables(cursor: sqlite3.Cursor) -> None:
    cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    existing_tables = {row[0] for row in cursor.fetchall()}
    missing_tables = sorted(REQUIRED_TABLES - existing_tables)

    if missing_tables:
        missing = ", ".join(missing_tables)
        raise RuntimeError(
            "Отсутствуют обязательные таблицы в production.db: "
            f"{missing}. Проверьте, что схема базы данных применена."
        )


def clear_demo_data(cursor: sqlite3.Cursor) -> None:
    for table_name in TABLES_TO_CLEAR:
        cursor.execute(f"DELETE FROM {table_name}")


def create_demo_data(cursor: sqlite3.Cursor) -> dict[str, int]:
    cursor.execute(
        """
        INSERT INTO projects (name, client, deadline, status)
        VALUES (?, ?, ?, ?)
        """,
        ("Project A", "Client X", "2026-03-20", "active"),
    )
    project_id = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO types (project_id, type_name, quantity_plan, stage_size)
        VALUES (?, ?, ?, ?)
        """,
        (project_id, "TYPE-A", 50, 20),
    )
    type_id = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO items (
            type_id, part_number, name, metal, thickness, qty_per_product, total_qty
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (type_id, "PART-001", "Дверь", "steel", 1.0, 1, 50),
    )
    item_id = cursor.lastrowid

    routes = [("laser", 1), ("bend", 2), ("weld", 3)]
    for stage_name, order_index in routes:
        cursor.execute(
            """
            INSERT INTO routes (item_id, stage_name, order_index)
            VALUES (?, ?, ?)
            """,
            (item_id, stage_name, order_index),
        )

    batches = [(1, 20, "pending"), (2, 20, "pending"), (3, 10, "pending")]
    batch_ids: dict[int, int] = {}
    for batch_number, qty_planned, status in batches:
        cursor.execute(
            """
            INSERT INTO type_batches (type_id, batch_number, qty_planned, status)
            VALUES (?, ?, ?, ?)
            """,
            (type_id, batch_number, qty_planned, status),
        )
        batch_ids[batch_number] = cursor.lastrowid

    batch_item_columns = get_table_columns(cursor, "batch_items")
    has_batch_item_qty_completed = "qty_completed" in batch_item_columns

    batch_item_ids: dict[int, int] = {}
    batch_qty_required: dict[int, int] = {}
    qty_per_product = 1
    for batch_number, qty_planned, _ in batches:
        qty_required = qty_planned * qty_per_product
        batch_qty_required[batch_number] = qty_required

        if has_batch_item_qty_completed:
            cursor.execute(
                """
                INSERT INTO batch_items (batch_id, item_id, qty_required, qty_completed)
                VALUES (?, ?, ?, ?)
                """,
                (batch_ids[batch_number], item_id, qty_required, 0),
            )
        else:
            cursor.execute(
                """
                INSERT INTO batch_items (batch_id, item_id, qty_required)
                VALUES (?, ?, ?)
                """,
                (batch_ids[batch_number], item_id, qty_required),
            )

        batch_item_ids[batch_number] = cursor.lastrowid

    batch_stage_columns = get_table_columns(cursor, "batch_item_stages")
    has_qty_done = "qty_done" in batch_stage_columns
    has_qty_in_progress = "qty_in_progress" in batch_stage_columns
    has_stage_qty_completed = "qty_completed" in batch_stage_columns

    for batch_number in (1, 2, 3):
        for stage_name, _ in routes:
            insert_columns = ["batch_item_id", "stage_name", "status"]
            insert_values = [batch_item_ids[batch_number], stage_name, "pending"]

            if has_qty_done:
                insert_columns.append("qty_done")
                insert_values.append(0)
            if has_qty_in_progress:
                insert_columns.append("qty_in_progress")
                insert_values.append(0)
            if has_stage_qty_completed:
                insert_columns.append("qty_completed")
                insert_values.append(0)

            cursor.execute(
                f"""
                INSERT INTO batch_item_stages ({', '.join(insert_columns)})
                VALUES ({', '.join(['?'] * len(insert_values))})
                """,
                insert_values,
            )

    locations = [
        ("Laser Zone", "production"),
        ("Bend Zone", "production"),
        ("Weld Zone", "production"),
        ("Shelf A", "storage"),
        ("Finished Zone", "storage"),
    ]

    location_ids: dict[str, int] = {}
    for name, zone_type in locations:
        cursor.execute(
            """
            INSERT INTO locations (name, zone_type)
            VALUES (?, ?)
            """,
            (name, zone_type),
        )
        location_ids[name] = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO transfers (batch_id, date, location_id, comment)
        VALUES (?, ?, ?, ?)
        """,
        (
            batch_ids[1],
            datetime.now().isoformat(sep=" ", timespec="seconds"),
            location_ids["Bend Zone"],
            "Передано после laser",
        ),
    )

    laser_update_fields = ["status = ?"]
    laser_update_values: list[object] = ["done"]
    if has_qty_done:
        laser_update_fields.append("qty_done = ?")
        laser_update_values.append(batch_qty_required[1])
    if has_stage_qty_completed:
        laser_update_fields.append("qty_completed = ?")
        laser_update_values.append(batch_qty_required[1])
    if has_qty_in_progress:
        laser_update_fields.append("qty_in_progress = ?")
        laser_update_values.append(0)

    laser_update_values.extend([batch_item_ids[1], "laser"])
    cursor.execute(
        f"""
        UPDATE batch_item_stages
        SET {', '.join(laser_update_fields)}
        WHERE batch_item_id = ? AND stage_name = ?
        """,
        laser_update_values,
    )

    if has_batch_item_qty_completed:
        cursor.execute(
            """
            UPDATE batch_items
            SET qty_completed = ?
            WHERE id = ?
            """,
            (batch_qty_required[1], batch_item_ids[1]),
        )

    cursor.execute(
        """
        INSERT INTO blocks (object_type, object_id, reason, comment, status)
        VALUES (?, ?, ?, ?, ?)
        """,
        ("type_batch", batch_ids[2], "no_metal", "Нет металла на laser", "active"),
    )

    return {
        "projects": count_rows(cursor, "projects"),
        "types": count_rows(cursor, "types"),
        "items": count_rows(cursor, "items"),
        "routes": count_rows(cursor, "routes"),
        "type_batches": count_rows(cursor, "type_batches"),
        "batch_items": count_rows(cursor, "batch_items"),
        "batch_item_stages": count_rows(cursor, "batch_item_stages"),
        "locations": count_rows(cursor, "locations"),
        "transfers": count_rows(cursor, "transfers"),
        "active_blocks": count_rows(
            cursor, "blocks", where_clause="WHERE status = 'active'"
        ),
    }


def count_rows(cursor: sqlite3.Cursor, table_name: str, where_clause: str = "") -> int:
    cursor.execute(f"SELECT COUNT(*) FROM {table_name} {where_clause}")
    return int(cursor.fetchone()[0])


def print_summary(counts: dict[str, int]) -> None:
    print("Demo data reset completed.\n")
    print(f"projects: {counts['projects']}")
    print(f"types: {counts['types']}")
    print(f"items: {counts['items']}")
    print(f"routes: {counts['routes']}")
    print(f"type_batches: {counts['type_batches']}")
    print(f"batch_items: {counts['batch_items']}")
    print(f"batch_item_stages: {counts['batch_item_stages']}")
    print(f"locations: {counts['locations']}")
    print(f"transfers: {counts['transfers']}")
    print(f"active blocks: {counts['active_blocks']}")


def main() -> None:
    connection: sqlite3.Connection | None = None
    try:
        connection = sqlite3.connect(DB_PATH)
        cursor = connection.cursor()
        ensure_required_tables(cursor)

        cursor.execute("BEGIN")
        clear_demo_data(cursor)
        counts = create_demo_data(cursor)
        connection.commit()

        print_summary(counts)
    except (sqlite3.Error, RuntimeError) as error:
        if connection is not None:
            connection.rollback()
        print(f"Ошибка при подготовке demo-данных: {error}")
    finally:
        if connection is not None:
            connection.close()


if __name__ == "__main__":
    main()
