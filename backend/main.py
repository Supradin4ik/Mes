from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models
from backend.database import engine, get_db
from backend.services.excel_parser import parse_spec_to_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/ping")
async def ping() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/projects/upload-spec/")
async def upload_spec(
    file: UploadFile = File(...),
    project_name: str = Form(...),
    db: AsyncSession = Depends(get_db),
) -> dict[str, int]:
    file_bytes = await file.read()
    result = await parse_spec_to_db(file_bytes=file_bytes, project_name=project_name, db=db)
    return result
