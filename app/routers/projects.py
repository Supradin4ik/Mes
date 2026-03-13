import sqlite3

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from app.database.db import get_connection
from app.routers.view_data import STATUS_LABELS

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


class ProjectCreate(BaseModel):
    name: str
    client: str
    deadline: str
    status: str


@router.get("/api/projects")
def get_projects_api() -> list[dict[str, str | int]]:
    connection = get_connection()
    try:
        cursor = connection.execute("SELECT id, name, client, deadline, status FROM projects")
        rows = cursor.fetchall()
        return [
            {
                "id": row[0],
                "name": row[1],
                "client": row[2],
                "deadline": row[3],
                "status": row[4],
            }
            for row in rows
        ]
    finally:
        connection.close()


@router.get("/projects", response_class=HTMLResponse)
def get_projects_page(request: Request) -> HTMLResponse:
    connection = get_connection()
    connection.row_factory = sqlite3.Row
    try:
        projects = connection.execute(
            """
            SELECT p.id, p.name, p.client, p.deadline, p.status, COUNT(t.id) AS type_count
            FROM projects p
            LEFT JOIN types t ON t.project_id = p.id
            GROUP BY p.id
            ORDER BY p.id
            """
        ).fetchall()

        payload = [
            {
                **dict(row),
                "status_class": (row["status"] or "pending").lower(),
                "status_label": STATUS_LABELS.get((row["status"] or "pending").lower(), row["status"]),
            }
            for row in projects
        ]

        return templates.TemplateResponse(
            "projects.html",
            {
                "request": request,
                "page_title": "Projects",
                "active_page": "projects",
                "projects": payload,
            },
        )
    finally:
        connection.close()


@router.get("/projects/{project_id}", response_class=HTMLResponse)
def get_project_page(project_id: int, request: Request) -> HTMLResponse:
    connection = get_connection()
    connection.row_factory = sqlite3.Row
    try:
        project = connection.execute(
            "SELECT id, name, client, deadline FROM projects WHERE id = ?",
            (project_id,),
        ).fetchone()
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        types_rows = connection.execute(
            """
            SELECT t.id, t.type_name, t.quantity_plan, t.stage_size, COUNT(tb.id) AS batch_count
            FROM types t
            LEFT JOIN type_batches tb ON tb.type_id = t.id
            WHERE t.project_id = ?
            GROUP BY t.id
            ORDER BY t.id
            """,
            (project_id,),
        ).fetchall()

        return templates.TemplateResponse(
            "project.html",
            {
                "request": request,
                "page_title": project["name"],
                "active_page": "projects",
                "project": dict(project),
                "types": [dict(row) for row in types_rows],
                "breadcrumbs": [
                    {"label": "Projects", "href": "/projects"},
                    {"label": project["name"], "href": None},
                ],
            },
        )
    finally:
        connection.close()


@router.post("/projects")
def create_project(payload: ProjectCreate) -> dict[str, str | int]:
    connection = get_connection()
    try:
        cursor = connection.execute(
            """
            INSERT INTO projects (name, client, deadline, status)
            VALUES (?, ?, ?, ?)
            """,
            (payload.name, payload.client, payload.deadline, payload.status),
        )
        connection.commit()

        return {
            "id": cursor.lastrowid,
            "name": payload.name,
            "client": payload.client,
            "deadline": payload.deadline,
            "status": payload.status,
        }
    finally:
        connection.close()
