from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AIResponseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    generated_text: str | None
    final_text: str | None
    model: str | None
    approved: bool
    approved_by: int | None
    created_at: datetime
    sent_at: datetime | None
