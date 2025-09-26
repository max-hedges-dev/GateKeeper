from .probe import scan_once

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

# Import our schemas and loader
from .models import ChecksConfig, RulesConfig
from .utils import load_and_validate


app = FastAPI()

ALLOWED_ORIGINS = [
    "http://localhost:5173"
    "http://127.0.0.1:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(status_code=204)

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/configs/checks")
def get_checks_config():
    """
    Load backend/configs/checks.yaml, validate against ChecksConfig,
    and return the validated data (as JSON).
    """
    try:
        cfg = load_and_validate("checks.yaml", ChecksConfig)
        return cfg.model_dump()  # serialize Pydantic model -> dict -> JSON
    except (FileNotFoundError, ValueError) as e:
        # 500 because it’s a server/config error, not a client request issue
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/configs/rules")
def get_rules_config():
    """
    Load backend/configs/rules.yaml, validate against RulesConfig,
    and return the validated data (as JSON).
    """
    try:
        cfg = load_and_validate("rules.yaml", RulesConfig)
        return cfg.model_dump()
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    # dev-only scan endpoint to exercise Step 4
@app.get("/api/scan")
def api_scan():
    """
    Run a single local scan and return the raw snapshot.
    (Rule engine will consume this in Step 5.)
    """
    try:
        return scan_once()
    except Exception as e:
        # Surface failures clearly
        raise HTTPException(status_code=500, detail=str(e))