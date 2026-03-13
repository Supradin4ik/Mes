import sqlite3
from collections import defaultdict

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.database.db import get_connection
from app.routers.view_data import collect_batch_details, quantity_expr

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/board", response_class=HTMLResponse)
def get_production_board(request: Request) -> HTMLResponse:
    connection = get_connection()
    connection.row_factory = sqlite3.Row

    try:
        rows = connection.execute(
            f"""
            SELECT
                tb.id,
                tb.batch_number,
                {quantity_expr(connection)} AS quantity,
                t.id AS type_id,
                t.type_name,
                p.id AS project_id,
                p.name AS project_name
            FROM type_batches tb
            JOIN types t ON t.id = tb.type_id
            JOIN projects p ON p.id = t.project_id
            ORDER BY p.id, t.id, tb.id
            """
        ).fetchall()

        batch_ids = [row["id"] for row in rows]
        details = collect_batch_details(connection, batch_ids)

        grouped: dict[tuple[int, str], dict[tuple[int, str], list[dict[str, object]]]] = defaultdict(lambda: defaultdict(list))
        for row in rows:
            project_key = (row["project_id"], row["project_name"])
            type_key = (row["type_id"], row["type_name"])
            grouped[project_key][type_key].append(
                {
                    "id": row["id"],
                    "batch_number": row["batch_number"],
                    "quantity": row["quantity"],
                    **details.get(row["id"], {}),
                }
            )

        projects_payload = []
        for (_, project_name), type_map in grouped.items():
            types_payload = []
            for (_, type_name), batches in type_map.items():
                types_payload.append({"type_name": type_name, "batches": batches})
            projects_payload.append({"project_name": project_name, "types": types_payload})

        return templates.TemplateResponse(
            "board.html",
            {
                "request": request,
                "page_title": "Production Board",
                "active_page": "board",
                "projects": projects_payload,
            },
        )
    finally:
        connection.close()
