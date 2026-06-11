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

class BulkValidateRequest(BaseModel):
    items: list[str]

class BulkValidateResponse(BaseModel):
    results: list[dict]
    total: int
    successful: int

# Helper function for validation logic (extracted from single-item endpoint)
def _validate_uuid_logic(uuid_str: str):
    """Core validation logic - returns dict result."""
    clean_uuid = uuid_str.lower()
    if clean_uuid.startswith("urn:uuid:"):
        clean_uuid = clean_uuid[9:]
    clean_uuid = re.sub(r"[{}-]", "", clean_uuid)
    
    try:
        parsed = uuid.UUID(clean_uuid)
    except ValueError as e:
        return {"valid": False, "version": None, "variant": None, "uuid_type": None, "formatted": None, "error": str(e)}
    
    variant_map = {
        uuid.RFC_4122: "RFC 4122",
        uuid.DCE: "DCE security",
        uuid.Microsoft: "Microsoft COM",
        uuid.Reserved_NCS: "Reserved NCS"
    }
    variant = variant_map.get(parsed.variant, "Unknown")
    formatted = str(parsed)
    
    return {
        "valid": True,
        "version": parsed.version,
        "variant": variant,
        "uuid_type": f"UUID{parsed.version}",
        "formatted": formatted,
        "error": None
    }

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/validate", response_model=ValidateResponse)
def validate_uuid(request: ValidateRequest, api_key: str = Depends(verify_api_key)):
    """Validate a UUID and return its version, variant, and type info."""
    uuid_str = request.uuid.strip()
    result = _validate_uuid_logic(uuid_str)
    return ValidateResponse(**result)

@app.post("/bulk/validate", response_model=BulkValidateResponse)
def validate_uuids_bulk(request: BulkValidateRequest, api_key: str = Depends(verify_api_key)):
    """Validate multiple UUIDs in a single request (up to 1000 items)."""
    if len(request.items) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 items per request")
    
    results = []
    successful = 0
    
    for item in request.items:
        result = _validate_uuid_logic(item)
        results.append({"input": item, "output": result, "error": result.get("error")})
        if result["valid"]:
            successful += 1
    
    return BulkValidateResponse(results=results, total=len(request.items), successful=successful)

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
            uuids.append(str(uuid.uuid4()))
    
    return GenerateResponse(uuids=uuids)

class BulkGenerateRequest(BaseModel):
    items: list[dict]

@app.post("/bulk/generate", response_model=BulkValidateResponse)
def generate_uuids_bulk(request: BulkGenerateRequest, api_key: str = Depends(verify_api_key)):
    """Generate multiple UUIDs in bulk. Each item: {"version": 4}."""
    if len(request.items) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 items per request")
    
    results = []
    successful = 0
    
    for item in request.items:
        version = item.get("version", 4) if isinstance(item, dict) else 4
        
        valid_versions = [1, 3, 4, 5, 6, 7]
        if version not in valid_versions:
            results.append({
                "input": item,
                "output": {"valid": False, "uuid": None, "error": f"Version must be one of {valid_versions}"},
                "error": f"Version must be one of {valid_versions}"
            })
            continue
        
        try:
            if version == 4:
                gen_uuid = str(uuid.uuid4())
            elif version == 1:
                gen_uuid = str(uuid.uuid1())
            elif version == 7:
                gen_uuid = str(uuid.uuid7())
            else:
                gen_uuid = str(uuid.uuid4())
            results.append({"input": item, "output": {"valid": True, "uuid": gen_uuid, "error": None}, "error": None})
            successful += 1
        except Exception as e:
            results.append({"input": item, "output": {"valid": False, "uuid": None, "error": str(e)}, "error": str(e)})
    
    return BulkValidateResponse(results=results, total=len(request.items), successful=successful)

@app.get("/validate/{uuid_str}", response_model=ValidateResponse)
def validate_uuid_path(uuid_str: str, api_key: str = Depends(verify_api_key)):
    """Validate a UUID via path parameter."""
    return validate_uuid(ValidateRequest(uuid=uuid_str), api_key=api_key)

@app.get("/random")
def random_uuid(api_key: str =Depends(verify_api_key)):
    """Generate a single random UUID v4."""
    return {"uuid": str(uuid.uuid4())}

handler = Mangum(app)