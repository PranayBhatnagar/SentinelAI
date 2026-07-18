from fastapi import FastAPI

from app.api.routes import router

app = FastAPI(title="Sentinel AI", version="0.1.0", description="From Alert to Resolution — Powered by Autonomous AI Agents.")
app.include_router(router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
