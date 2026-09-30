from fastapi import APIRouter

from app.api.routes import customers, tickets

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(tickets.router)
api_router.include_router(customers.router)
