import asyncio
from fastapi import FastAPI
from .routers import detections

app = FastAPI(title="SEDIRS API")

app.include_router(detections.router)

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    asyncio.run()
