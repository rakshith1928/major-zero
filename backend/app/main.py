from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, analytics, auth, booking, guardian, metrics, notifications, passkeys, passengers, payments, tickets, tracking, warnings
from app.config import settings
from app.services import passenger_ref


@asynccontextmanager
async def lifespan(_: FastAPI):
    model_path = (
        Path(__file__).resolve().parent.parent.parent
        / "research"
        / "results"
        / "passenger_ref_model.pkl"
    )
    if model_path.exists():
        passenger_ref.load_trained_classifier(str(model_path))
    yield


app = FastAPI(title="ZeroBus", version="0.1.0", lifespan=lifespan)

# Browser apps (Vite dev on 5173, preview) must reach the API cross-origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(passkeys.router)
app.include_router(booking.router)
app.include_router(guardian.router)
app.include_router(payments.router)
app.include_router(tickets.router)
app.include_router(passengers.router)
app.include_router(warnings.router)
app.include_router(analytics.router)
app.include_router(tracking.router)
app.include_router(notifications.router)
app.include_router(admin.router)
app.include_router(metrics.router)


@app.get("/health")
def health():
    return {"status": "ok"}
