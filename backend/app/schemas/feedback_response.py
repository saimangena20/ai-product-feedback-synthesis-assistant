from pydantic import BaseModel


class IngestResponse(BaseModel):
    ingest_id: str
    status: str
    job_status: str
    total_rows: int
    valid_rows: int
    preview: list[dict[str, object]]
