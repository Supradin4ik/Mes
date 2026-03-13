from __future__ import annotations

import sqlite3


def _build_batches(quantity_plan: int, stage_size: int) -> list[int]:
    if quantity_plan <= 0 or stage_size <= 0:
        return []

    batches: list[int] = []
    remaining = quantity_plan
    while remaining > 0:
        current = stage_size if remaining >= stage_size else remaining
        batches.append(current)
        remaining -= current
    return batches


def recreate_type_plan(
    connection: sqlite3.Connection,
    *,
    type_id: int,
    quantity_plan: int,
    stage_size: int,
) -> dict[str, int]:
    batch_ids = [
        row[0]
        for row in connection.execute(
            "SELECT id FROM type_batches WHERE type_id = ? ORDER BY id", (type_id,)
        ).fetchall()
    ]

    if batch_ids:
        placeholders = ",".join("?" for _ in batch_ids)
        batch_item_ids = [
            row[0]
            for row in connection.execute(
                f"SELECT id FROM batch_items WHERE batch_id IN ({placeholders})",
                batch_ids,
            ).fetchall()
        ]

        if batch_item_ids:
            stage_placeholders = ",".join("?" for _ in batch_item_ids)
            connection.execute(
                f"DELETE FROM batch_item_stages WHERE batch_item_id IN ({stage_placeholders})",
                batch_item_ids,
            )

        connection.execute(
            f"DELETE FROM batch_items WHERE batch_id IN ({placeholders})",
            batch_ids,
        )
        connection.execute("DELETE FROM type_batches WHERE type_id = ?", (type_id,))

    items = connection.execute(
        """
        SELECT id, qty_per_product
        FROM items
        WHERE type_id = ?
        ORDER BY id
        """,
        (type_id,),
    ).fetchall()

    batches = _build_batches(quantity_plan=quantity_plan, stage_size=stage_size)

    created_batch_count = 0
    created_batch_items = 0
    created_batch_stages = 0

    for idx, batch_qty in enumerate(batches, start=1):
        batch_cursor = connection.execute(
            """
            INSERT INTO type_batches (type_id, batch_number, qty_planned, status)
            VALUES (?, ?, ?, 'pending')
            """,
            (type_id, idx, batch_qty),
        )
        batch_id = batch_cursor.lastrowid
        created_batch_count += 1

        for item_id, qty_per_product in items:
            qty_required = (qty_per_product or 0) * batch_qty
            batch_item_cursor = connection.execute(
                """
                INSERT INTO batch_items (batch_id, item_id, qty_required, qty_completed)
                VALUES (?, ?, ?, 0)
                """,
                (batch_id, item_id, qty_required),
            )
            batch_item_id = batch_item_cursor.lastrowid
            created_batch_items += 1

            routes = connection.execute(
                """
                SELECT stage_name
                FROM routes
                WHERE item_id = ?
                ORDER BY order_index, id
                """,
                (item_id,),
            ).fetchall()

            for route in routes:
                connection.execute(
                    """
                    INSERT INTO batch_item_stages (batch_item_id, stage_name, status)
                    VALUES (?, ?, 'pending')
                    """,
                    (batch_item_id, route[0]),
                )
                created_batch_stages += 1

    return {
        "created_batches": created_batch_count,
        "created_batch_items": created_batch_items,
        "created_batch_item_stages": created_batch_stages,
    }
