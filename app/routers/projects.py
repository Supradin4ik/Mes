from fastapi import APIRouter
from pydantic import BaseModel

from app.database.db import get_connection

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    client: str
    deadline: str
    status: str


@router.get("/projects")
def get_projects() -> list[dict[str, str | int]]:
    connection = get_connection()
    try:
        cursor = connection.execute(
            "SELECT id, name, client, deadline, status FROM projects"
        )
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
