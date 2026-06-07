import uuid
import re
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from mangum import Mangum

app = FastAPI(title="UUID Validator and Generator API", version="1.0.0")
# === BT Builds Standard Middleware (auto-injected) ===
from fastapi.middleware.cors import CORSMiddleware as _BTCors
app.add_middleware(_BTCors, allow_origins=["*"], allow_methods=["*"],
    allow_headers=["*"], expose_headers=["X-RateLimit-Limit","X-RateLimit-Remaining","X-RateLimit-Reset"])

@app.middleware("http")
async def _bt_add_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Powered-By"] = "btbuilds"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


# API Key auth
API_KEY="demo-key-change-in-production"

def verify_api_key(x_api_key: str = None):
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return x_api_key

class ValidateRequest(BaseModel):
    uuid: str

class ValidateResponse(BaseModel):
    valid: bool
    version: int | None = None
    variant: str | None = None
    uuid_type: str | None = None
    formatted: str | None = None
    error: str | None = None

class GenerateRequest(BaseModel):
    version: int = 4
    count: int = 1

class GenerateResponse(BaseModel):
    uuids: list[str]

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/validate", response_model=ValidateResponse)
def validate_uuid(request: ValidateRequest, api_key: str = Depends(verify_api_key)):
    """Validate a UUID and return its version, variant, and type info."""
    uuid_str = request.uuid.strip()
    
    # Clean up the input - remove common prefixes and make lowercase
    clean_uuid = uuid_str.lower()
    if clean_uuid.startswith("urn:uuid:"):
        clean_uuid = clean_uuid[9:]
    clean_uuid = re.sub(r"[{}-]", "", clean_uuid)
    
    # Try to validate
    try:
        parsed = uuid.UUID(clean_uuid)
    except ValueError as e:
        return ValidateResponse(valid=False, version=None, variant=None, uuid_type=None, formatted=None, error=str(e))
    
    # Determine variant
    variant_map = {
        uuid.RFC_4122: "RFC 4122",
        uuid.DCE: "DCE security",
        uuid.Microsoft: "Microsoft COM",
        uuid.Reserved_NCS: "Reserved NCS"
    }
    variant = variant_map.get(parsed.variant, "Unknown")
    
    # Format the UUID with proper formatting
    formatted = str(parsed)
    
    return ValidateResponse(
        valid=True,
        version=parsed.version,
        variant=variant,
        uuid_type=f"UUID{parsed.version}",
        formatted=formatted
    )

@app.post("/generate", response_model=GenerateResponse)
def generate_uuid(request: GenerateRequest, api_key: str = Depends(verify_api_key)):
    """Generate one or more UUIDs of specified version."""
    if request.count < 1 or request.count > 100:
        raise HTTPException(status_code=400, detail="Count must be between 1 and 100")
    
    valid_versions = [1, 3, 4, 5, 6, 7]
    if request.version not in valid_versions:
        raise HTTPException(status_code=400, detail=f"Version must be one of {valid_versions}")
    
    uuids = []
    for _ in range(request.count):
        if request.version == 4:
            uuids.append(str(uuid.uuid4()))
        elif request.version == 1:
            uuids.append(str(uuid.uuid1()))
        elif request.version == 7:
            uuids.append(str(uuid.uuid7()))
        else:
            # For versions 3, 5, 6 - use uuid4 as fallback since they need namespace/names
            uuids.append(str(uuid.uuid4()))
    
    return GenerateResponse(uuids=uuids)

@app.get("/validate/{uuid_str}", response_model=ValidateResponse)
def validate_uuid_path(uuid_str: str, api_key: str = Depends(verify_api_key)):
    """Validate a UUID via path parameter."""
    return validate_uuid(ValidateRequest(uuid=uuid_str), api_key=api_key)

@app.get("/random")
def random_uuid(api_key: str = Depends(verify_api_key)):
    """Generate a single random UUID v4."""
    return {"uuid": str(uuid.uuid4())}

handler = Mangum(app)