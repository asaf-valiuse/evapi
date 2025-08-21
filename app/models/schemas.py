from pydantic import BaseModel
from typing import List, Optional

class Telemetry(BaseModel):
    id: int
    cpu_percent: int
    memory_mb: int
    ts_utc: str

class TelemetryResponse(BaseModel):
    account_id: int
    items: List[Telemetry]
