import sqlite3

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.database.db import get_connection
from app.routers.view_data import collect_batch_details, quantity_expr

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/batch/{batch_id}", response_class=HTMLResponse)
def get_batch_page(batch_id: int, request: Request) -> HTMLResponse:
    connection = get_connection()
    connection.row_factory = sqlite3.Row

    try:
        batch = connection.execute(
            f"""
            SELECT tb.id, tb.batch_number, {quantity_expr(connection)} AS quantity,
                   t.id AS type_id, t.type_name, p.id AS project_id, p.name AS project_name
            FROM type_batches tb
            JOIN types t ON t.id = tb.type_id
            JOIN projects p ON p.id = t.project_id
            WHERE tb.id = ?
            """,
            (batch_id,),
        ).fetchone()
        if batch is None:
            raise HTTPException(status_code=404, detail="Batch not found")

        details = collect_batch_details(connection, [batch_id]).get(batch_id, {})
        raw_stages = details.get("raw_stages", [])

        route_stages = []
        current_found = False
        for stage in raw_stages:
            stage_status = (stage["status"] or "").lower()
            if stage_status == "done":
                state = "done"
                symbol = "✓"
            elif not current_found and stage_status == "pending":
                state = "current"
                symbol = "→"
                current_found = True
            else:
                state = "pending"
                symbol = "○"
            route_stages.append({"stage_name": stage["stage_name"], "state": state, "symbol": symbol})

        locations = connection.execute(
            """
            SELECT id, name
            FROM locations
            WHERE name IN ('Laser Zone', 'Bend Zone', 'Weld Zone', 'Shelf A', 'Finished Zone')
            ORDER BY id
            """
        ).fetchall()
        if not locations:
            locations = connection.execute("SELECT id, name FROM locations ORDER BY id").fetchall()

        return templates.TemplateResponse(
            "batch.html",
            {
                "request": request,
                "page_title": f"Batch {batch['batch_number']}",
                "active_page": "board",
                "batch": {**dict(batch), **details},
                "route_stages": route_stages,
                "locations": [dict(row) for row in locations],
                "breadcrumbs": [
                    {"label": "Projects", "href": "/projects"},
                    {"label": batch["project_name"], "href": f"/projects/{batch['project_id']}"},
                    {"label": batch["type_name"], "href": f"/types/{batch['type_id']}"},
                    {"label": f"Batch {batch['batch_number']}", "href": None},
                ],
            },
        )
    finally:
        connection.close()
