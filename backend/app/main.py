from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.router import api_router
from app.db.session import engine
from app.services.ticket_service import ResponseGenerationFailed, TicketConflict, TicketNotFound

app = FastAPI(title="Jev Support API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.exception_handler(TicketNotFound)
async def ticket_not_found(request: Request, exc: TicketNotFound):
    return JSONResponse({"detail": "Ticket not found"}, status_code=404)


@app.exception_handler(TicketConflict)
async def ticket_conflict(request: Request, exc: TicketConflict):
    return JSONResponse({"detail": str(exc)}, status_code=409)


@app.exception_handler(ResponseGenerationFailed)
async def generation_failed(request: Request, exc: ResponseGenerationFailed):
    return JSONResponse(
        {"detail": "Reply generation failed; try again or write the reply manually"}, status_code=502
    )


@app.get("/health")
async def health() -> dict:
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
