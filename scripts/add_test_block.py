import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent.parent / "production.db"


def main() -> None:
    if not DB_PATH.exists():
        print(f"Файл базы данных не найден: {DB_PATH}")
        return

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        cursor = connection.execute(
            """
            INSERT INTO blocks (object_type, object_id, reason, comment, status)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("type_batch", 2, "no_metal", "Нет металла на laser", "active"),
        )
        connection.commit()

        block_id = cursor.lastrowid
        block_row = connection.execute(
            """
            SELECT id, object_type, object_id, reason, comment, status
            FROM blocks
            WHERE id = ?
            """,
            (block_id,),
        ).fetchone()

    if block_row is None:
        print("Не удалось прочитать созданную блокировку.")
        return

    print("Создана тестовая блокировка:")
    print(f"- id: {block_row['id']}")
    print(f"- object_type: {block_row['object_type']}")
    print(f"- object_id: {block_row['object_id']}")
    print(f"- reason: {block_row['reason']}")
    print(f"- comment: {block_row['comment']}")
    print(f"- status: {block_row['status']}")


if __name__ == "__main__":
    main()
