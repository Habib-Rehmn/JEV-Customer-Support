from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class OrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    order_number: str
    total_amount: Decimal
    status: str
    created_at: datetime
    delivered_at: datetime | None
