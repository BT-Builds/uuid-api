# UUID Validator and Generator API

A simple API for validating UUID formats and generating UUIDs without installing heavy libraries.

## Endpoints

### `GET /health`
Health check endpoint (no auth required).

### `POST /validate`
Validate a UUID string.

**Request:**
```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Response:**
```json
{
  "valid": true,
  "version": 4,
  "variant": "RFC 4122",
  "uuid_type": "UUID4",
  "formatted": "550e8400-e29b-41d4-a716-446655440000",
  "error": null
}
```

### `GET /validate/{uuid}`
Same as POST /validate but via path parameter.

### `POST /generate`
Generate one or more UUIDs.

**Request:**
```json
{
  "version": 4,
  "count": 5
}
```

**Response:**
```json
{
  "uuids": ["...", "..."]
}
```

### `GET /random`
Generate a single random UUID v4.

## Authentication
All endpoints except `/health` require `X-API-Key` header with value `demo-key-change-in-production`.

## Postman
[![Run in Postman](https://run.pstmn.io/button.svg)](https://raw.githubusercontent.com/BT-Builds/uuid-api/main/postman_collection.json)
