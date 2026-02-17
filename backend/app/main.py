import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.db.base import Base
from app.db.session import engine
from app.workers.dispatcher import process_pending_messages

app = FastAPI(title="WhatsApp Compliance CRM")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")


@app.on_event("startup")
async def startup_event():
    Base.metadata.create_all(bind=engine)
    asyncio.create_task(process_pending_messages())


@app.get("/")
def root():
    return {"app": "WhatsApp Compliance CRM", "compliance": "opt-in enforced"}
