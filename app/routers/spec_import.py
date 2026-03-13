import sqlite3

from fastapi import APIRouter, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database.db import get_connection
from app.services.spec_import_service import import_specification, parse_spec_excel

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


@router.get("/types/{type_id}/import-spec", response_class=HTMLResponse)
def import_spec_page(type_id: int, request: Request, message: str | None = None) -> HTMLResponse:
    connection = get_connection()
    connection.row_factory = sqlite3.Row

    try:
        type_row = connection.execute(
            """
            SELECT t.id, t.project_id, t.type_name, p.name AS project_name
            FROM types t
            JOIN projects p ON p.id = t.project_id
            WHERE t.id = ?
            """,
            (type_id,),
        ).fetchone()
        if type_row is None:
            raise HTTPException(status_code=404, detail="Type not found")

        return templates.TemplateResponse(
            "import_spec.html",
            {
                "request": request,
                "page_title": "Upload Specification",
                "active_page": "projects",
                "type_item": dict(type_row),
                "message": message,
                "breadcrumbs": [
                    {"label": "Projects", "href": "/projects"},
                    {"label": type_row["project_name"], "href": f"/projects/{type_row['project_id']}"},
                    {"label": type_row["type_name"], "href": f"/types/{type_id}"},
                    {"label": "Import Specification", "href": None},
                ],
            },
        )
    finally:
        connection.close()


@router.post("/types/{type_id}/import-spec")
async def import_spec(type_id: int, file: UploadFile) -> RedirectResponse:
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        return RedirectResponse(
            url=f"/types/{type_id}/import-spec?message=Only+.xlsx+files+are+supported",
            status_code=303,
        )

    content = await file.read()
    connection = get_connection()
    connection.row_factory = sqlite3.Row

    try:
        type_row = connection.execute(
            "SELECT id, quantity_plan FROM types WHERE id = ?",
            (type_id,),
        ).fetchone()
        if type_row is None:
            raise HTTPException(status_code=404, detail="Type not found")

        items = parse_spec_excel(content)
        summary = import_specification(
            connection,
            type_id=type_id,
            type_quantity_plan=type_row["quantity_plan"] or 0,
            items=items,
        )
        connection.commit()

        return RedirectResponse(
            url=(
                f"/types/{type_id}/import-spec?message="
                f"Imported+items%3A+{summary.created_items}%2C+routes%3A+{summary.created_routes}"
            ),
            status_code=303,
        )
    except KeyError:
        connection.rollback()
        return RedirectResponse(
            url=f"/types/{type_id}/import-spec?message=Sheet+%D0%9B%D0%B8%D1%81%D1%821+not+found",
            status_code=303,
        )
    finally:
        connection.close()
