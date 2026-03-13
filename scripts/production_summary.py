import sqlite3
from collections import defaultdict
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent.parent / "production.db"


def fetch_all(connection: sqlite3.Connection, query: str) -> list[sqlite3.Row]:
    cursor = connection.execute(query)
    return cursor.fetchall()


def build_latest_transfers(
    transfers: list[sqlite3.Row],
    location_names: dict[int, str],
) -> dict[int, dict[str, str]]:
    latest_by_batch: dict[int, sqlite3.Row] = {}

    for transfer in transfers:
        batch_id = transfer["batch_id"]
        if batch_id is None:
            continue

        current_latest = latest_by_batch.get(batch_id)
        if current_latest is None or transfer["id"] > current_latest["id"]:
            latest_by_batch[batch_id] = transfer

    result: dict[int, dict[str, str]] = {}
    for batch_id, transfer in latest_by_batch.items():
        location_name = location_names.get(transfer["location_id"], "нет")
        comment = transfer["comment"] or "нет"

        result[batch_id] = {
            "location": location_name,
            "comment": comment,
        }

    return result


def print_summary(connection: sqlite3.Connection) -> None:
    projects = fetch_all(connection, "SELECT id, name FROM projects ORDER BY id")
    types_rows = fetch_all(
        connection,
        "SELECT id, project_id, type_name FROM types ORDER BY project_id, id",
    )
    batches = fetch_all(
        connection,
        "SELECT id, type_id, batch_number, qty_planned FROM type_batches ORDER BY type_id, id",
    )
    batch_items = fetch_all(
        connection,
        "SELECT id, batch_id FROM batch_items ORDER BY batch_id, id",
    )
    stages = fetch_all(
        connection,
        "SELECT id, batch_item_id, stage_name, status FROM batch_item_stages "
        "ORDER BY batch_item_id, id",
    )
    transfers = fetch_all(
        connection,
        "SELECT id, batch_id, location_id, comment FROM transfers ORDER BY id",
    )
    locations = fetch_all(connection, "SELECT id, name FROM locations ORDER BY id")

    if not projects:
        print("Проекты не найдены. Таблица projects пуста.")
        return

    types_by_project: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for type_row in types_rows:
        types_by_project[type_row["project_id"]].append(type_row)

    batches_by_type: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for batch in batches:
        batches_by_type[batch["type_id"]].append(batch)

    batch_item_ids_by_batch: dict[int, list[int]] = defaultdict(list)
    for item in batch_items:
        batch_item_ids_by_batch[item["batch_id"]].append(item["id"])

    stages_by_batch_item: dict[int, list[sqlite3.Row]] = defaultdict(list)
    for stage in stages:
        stages_by_batch_item[stage["batch_item_id"]].append(stage)

    location_names = {row["id"]: row["name"] for row in locations}
    latest_transfer_by_batch = build_latest_transfers(transfers, location_names)

    for project in projects:
        project_name = project["name"] or "(без названия)"
        print(f"PROJECT: {project_name}")

        project_types = types_by_project.get(project["id"], [])
        if not project_types:
            print("  Нет типов для этого проекта.")
            print()
            continue

        for type_row in project_types:
            type_name = type_row["type_name"] or "(без названия type)"
            print(f"  TYPE: {type_name}")

            type_batches = batches_by_type.get(type_row["id"], [])
            if not type_batches:
                print("    Нет batch для этого type.")
                print()
                continue

            for batch in type_batches:
                quantity = batch["qty_planned"]
                quantity_text = str(quantity) if quantity is not None else "нет"

                print(f"    BATCH {batch['batch_number']}")
                print(f"      Quantity: {quantity_text}")
                print("      Stages:")

                batch_item_ids = batch_item_ids_by_batch.get(batch["id"], [])
                batch_stages: list[sqlite3.Row] = []
                for batch_item_id in batch_item_ids:
                    batch_stages.extend(stages_by_batch_item.get(batch_item_id, []))

                if not batch_stages:
                    print("        - нет этапов")
                else:
                    for stage in batch_stages:
                        stage_name = stage["stage_name"] or "(без названия)"
                        stage_status = stage["status"] or "нет статуса"
                        print(f"        - {stage_name}: {stage_status}")

                transfer_data = latest_transfer_by_batch.get(batch["id"])
                if transfer_data is None:
                    print("      Location: нет")
                    print("      Comment: нет")
                else:
                    print(f"      Location: {transfer_data['location']}")
                    print(f"      Comment: {transfer_data['comment']}")

                print()


def main() -> None:
    if not DB_PATH.exists():
        print(f"Файл базы данных не найден: {DB_PATH}")
        return

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    try:
        print_summary(connection)
    finally:
        connection.close()


if __name__ == "__main__":
    main()
