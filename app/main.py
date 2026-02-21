"""FastAPI app: mount routes, middleware for /performance timing."""

import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import performance, returns, transactions

app = FastAPI(title="Retirement Auto-Savings API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_timing(request, call_next):
    request.state.start_time = time.perf_counter()
    response = await call_next(request)
    request.state.request_duration_ms = (time.perf_counter() - request.state.start_time) * 1000
    return response


BASE = "/blackrock/challenge/v1"
app.include_router(transactions.router, prefix=BASE, tags=["transactions"])
app.include_router(returns.router, prefix=BASE, tags=["returns"])
app.include_router(performance.router, prefix=BASE, tags=["performance"])


@app.get("/health")
def health():
    return {"status": "ok"}
