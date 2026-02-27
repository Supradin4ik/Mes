from io import BytesIO

import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Part, Project


async def parse_spec_to_db(file_bytes, project_name: str, db: AsyncSession) -> dict[str, int]:
    df = pd.read_excel(BytesIO(file_bytes))

    required_columns = ["Наименование", "Материал", "Толщина", "Количество"]
    missing_columns = [column for column in required_columns if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    fasteners = ("Болт", "Гайка", "Шайба")
    parts_df = df[
        ~df["Наименование"].astype(str).str.contains("|".join(fasteners), case=False, na=False)
        & df["Толщина"].notna()
    ]

    project = Project(name=project_name, total_units=1, blocks_count=1)
    db.add(project)
    await db.flush()

    parts_added = 0
    for _, row in parts_df.iterrows():
        part = Part(
            project_id=project.id,
            name=str(row["Наименование"]).strip(),
            material_type=str(row["Материал"]).strip(),
            thickness=float(row["Толщина"]),
            qty_per_unit=int(row["Количество"]),
        )
        db.add(part)
        parts_added += 1

    await db.commit()
    return {"project_id": project.id, "parts_added": parts_added}
