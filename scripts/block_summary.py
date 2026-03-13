import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent.parent / "production.db"


def main() -> None:
    if not DB_PATH.exists():
        print(f"Файл базы данных не найден: {DB_PATH}")
        return

    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        active_blocks = connection.execute(
            """
            SELECT object_type, object_id, reason, comment, status
            FROM blocks
            WHERE status = 'active'
            ORDER BY id
            """
        ).fetchall()

    if not active_blocks:
        print("Активных блокировок нет.")
        return

    for block in active_blocks:
        print("BLOCK")
        print(f"- object_type: {block['object_type']}")
        print(f"- object_id: {block['object_id']}")
        print(f"- reason: {block['reason']}")
        print(f"- comment: {block['comment']}")
        print(f"- status: {block['status']}")
        print()


if __name__ == "__main__":
    main()
