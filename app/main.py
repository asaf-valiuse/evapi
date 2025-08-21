from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import telemetry

# Disable docs in production for security
app = FastAPI(
    title="Direct Link API", 
    version="1.0.0",
    docs_url=None,      # Disables /docs
    redoc_url=None,     # Disables /redoc
    openapi_url=None    # Disables /openapi.json
)

# ——— Global CORS ———
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # truly global
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,   # must be False when allow_origins=["*"]
)

app.include_router(telemetry.router)

@app.get("/healthz")
def healthz():
    return {"ok": True}
