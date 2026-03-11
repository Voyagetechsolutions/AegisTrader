"""Simple FastAPI server for mobile app testing - no database, no scheduler"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.routers.mobile import router as mobile_router

app = FastAPI(title="Aegis Trader Mobile API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(mobile_router)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"message": "Aegis Trader Mobile API"}
