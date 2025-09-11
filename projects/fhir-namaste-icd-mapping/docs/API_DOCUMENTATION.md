# FHIR NAMASTE-ICD Mapping Service API Documentation

## Overview

The FHIR NAMASTE-ICD Mapping Service provides a comprehensive REST API for healthcare terminology mapping between NAMASTE (Ayush terminology) and ICD-11 TM2 systems, with full FHIR R4 compliance.

**Base URL**: `http://localhost:8000`  
**API Version**: `1.0.0`  
**Documentation**: `http://localhost:8000/docs` (Interactive Swagger UI)  
**Alternative Documentation**: `http://localhost:8000/redoc` (ReDoc)

## Authentication

The API uses JWT (JSON Web Token) based authentication with OAuth 2.0 flow.

### Authentication Methods

1. **Username/Password**: Traditional login with username and password
2. **ABHA Authentication**: Authentication using ABHA ID and OTP (mock implementation)

### Getting Access Token

```bash
POST /auth/token
Content-Type: application/x-www-form-urlencoded

username=admin&password=admin123
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "abha_id": null,
  "user_id": 1
}
```

### Using Access Token

Include the token in the Authorization header for all authenticated endpoints:

```bash
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Endpoints

### 1. Health & Status

#### GET /
**Description**: Root endpoint providing service information  
**Authentication**: None required

**Response:**
```json
{
  "message": "FHIR NAMASTE-ICD Mapping Service",
  "version": "1.0.0",
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### GET /health
**Description**: Detailed health check  
**Authentication**: None required

**Response:**
```json
{
  "service": "FHIR NAMASTE-ICD Mapping Service",
  "status": "healthy",
  "database": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "components": {
    "fhir": "ready",
    "authentication": "ready",
    "terminology_services": "ready"
  }
}
```

### 2. Authentication

#### POST /auth/token
**Description**: Authenticate with username/password  
**Authentication**: None required

**Request Body:**
```
username=admin&password=admin123
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "abha_id": null,
  "user_id": 1
}
```

#### POST /auth/register
**Description**: Register new user  
**Authentication**: None required

**Request Body:**
```json
{
  "username": "newuser",
  "email": "user@example.com",
  "full_name": "New User",
  "password": "securepassword123",
  "abha_id": "14-1234-5678-9012"
}
```

**Response:**
```json
{
  "message": "User registered successfully",
  "user_id": 2,
  "username": "newuser"
}
```

#### POST /auth/abha
**Description**: Authenticate with ABHA ID and OTP  
**Authentication**: None required

**Request Body:**
```json
{
  "abha_id": "14-1234-5678-9012",
  "auth_method": "otp",
  "otp": "123456"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "abha_id": "14-1234-5678-9012",
  "user_id": 3
}
```

### 3. Search

#### GET /search
**Description**: Search terminology codes across systems  
**Authentication**: Required

**Parameters:**
- `term` (required): Search term
- `system` (optional): Filter by terminology system URI
- `limit` (optional): Maximum results (default: 50)

**Example:**
```bash
GET /search?term=diabetes&system=http://terminology.ayush.gov.in/namaste&limit=10
```

**Response:**
```json
[
  {
    "code": "PRAM001",
    "display": "Prameha",
    "system": "http://terminology.ayush.gov.in/namaste",
    "definition": "A condition characterized by excessive urination and thirst",
    "properties": {
      "category": "Metabolic Disorders",
      "system_name": "Ayurveda"
    }
  },
  {
    "code": "MADHUMEHA001",
    "display": "Madhumeha",
    "system": "http://terminology.ayush.gov.in/namaste",
    "definition": "Diabetes mellitus in Ayurvedic terminology",
    "properties": {
      "category": "Metabolic Disorders",
      "system_name": "Ayurveda"
    }
  }
]
```

### 4. Translation

#### GET /translate
**Description**: Translate codes between terminology systems  
**Authentication**: Required

**Parameters:**
- `source` (required): Source terminology system URI
- `target` (required): Target terminology system URI
- `code` (required): Code to translate

**Example:**
```bash
GET /translate?source=http://terminology.ayush.gov.in/namaste&target=http://id.who.int/icd/release/11/tm2&code=PRAM001
```

**Response:**
```json
{
  "source_code": "PRAM001",
  "source_system": "http://terminology.ayush.gov.in/namaste",
  "target_code": "TM-E11",
  "target_system": "http://id.who.int/icd/release/11/tm2",
  "equivalence": "equivalent",
  "confidence": 0.9
}
```

**Response (No mapping found):**
```json
null
```

### 5. Data Upload

#### POST /upload/namaste
**Description**: Upload NAMASTE CSV file  
**Authentication**: Required  
**Content-Type**: multipart/form-data

**Request:**
```bash
POST /upload/namaste
Content-Type: multipart/form-data

file: [CSV file with columns: code, display, definition, ...]
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully loaded 25 codes",
  "codes_loaded": 25,
  "validation": {
    "valid": true,
    "total_rows": 25,
    "valid_rows": 25,
    "columns": ["code", "display", "definition", "category"],
    "warnings": []
  }
}
```

### 6. Data Synchronization

#### POST /sync/icd11
**Description**: Synchronize ICD-11 TM2 codes  
**Authentication**: Required

**Request Body (optional):**
```json
{
  "search_terms": ["diabetes", "fever", "cough"]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully synced 10 ICD-11 TM2 codes",
  "codes_synced": 10,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 7. Mappings

#### POST /mappings/create
**Description**: Create automatic mappings between terminology systems  
**Authentication**: Required

**Parameters:**
- `source_system` (optional): Source system URI (default: NAMASTE)
- `target_system` (optional): Target system URI (default: ICD-11 TM2)

**Response:**
```json
{
  "success": true,
  "message": "Created 15 automatic mappings",
  "mappings_created": 15,
  "mappings": [
    {
      "source_code": "PRAM001",
      "source_display": "Prameha",
      "target_code": "TM-E11",
      "target_display": "Diabetes mellitus",
      "equivalence": "equivalent",
      "confidence": 0.9
    }
  ],
  "total_source_codes": 20,
  "total_target_codes": 25
}
```

#### GET /mappings/statistics
**Description**: Get mapping statistics  
**Authentication**: Required

**Response:**
```json
{
  "total_mappings": 15,
  "system_pairs": {
    "http://terminology.ayush.gov.in/namaste -> http://id.who.int/icd/release/11/tm2": 15
  },
  "confidence_distribution": {
    "high": 12,
    "medium": 2,
    "low": 1
  },
  "method_distribution": {
    "fuzzy_match": 10,
    "manual": 5
  },
  "last_updated": "2024-01-15T10:30:00Z"
}
```

### 8. FHIR Resources

#### GET /fhir/CodeSystem
**Description**: Get FHIR CodeSystem resources  
**Authentication**: Required

**Parameters:**
- `system` (optional): Filter by system URI

**Response:**
```json
{
  "resourceType": "Bundle",
  "id": "codesystems-1705312200",
  "type": "collection",
  "total": 2,
  "entry": [
    {
      "resource": {
        "resourceType": "CodeSystem",
        "id": "namaste-codesystem",
        "url": "http://terminology.ayush.gov.in/namaste",
        "version": "1.0.0",
        "name": "NAMASTE",
        "title": "National Ayush Morbidity and Standardized Terminologies Electronic",
        "status": "active",
        "concept": [
          {
            "code": "PRAM001",
            "display": "Prameha",
            "definition": "A condition characterized by excessive urination and thirst"
          }
        ]
      }
    }
  ]
}
```

#### GET /fhir/ConceptMap
**Description**: Get FHIR ConceptMap resources  
**Authentication**: Required

**Parameters:**
- `source` (optional): Filter by source system URI
- `target` (optional): Filter by target system URI

**Response:**
```json
{
  "resourceType": "Bundle",
  "id": "conceptmaps-1705312200",
  "type": "collection",
  "total": 1,
  "entry": [
    {
      "resource": {
        "resourceType": "ConceptMap",
        "id": "namaste-to-icd11-map",
        "url": "http://fhir.namaste-icd.org/ConceptMap/namaste-to-icd11",
        "version": "1.0.0",
        "name": "NAMASTEToICD11Map",
        "title": "Code mappings from NAMASTE to ICD-11 TM2",
        "status": "active",
        "sourceUri": "http://terminology.ayush.gov.in/namaste",
        "targetUri": "http://id.who.int/icd/release/11/tm2",
        "group": [
          {
            "source": "http://terminology.ayush.gov.in/namaste",
            "target": "http://id.who.int/icd/release/11/tm2",
            "element": [
              {
                "code": "PRAM001",
                "display": "Prameha",
                "target": [
                  {
                    "code": "TM-E11",
                    "display": "Diabetes mellitus",
                    "equivalence": "equivalent"
                  }
                ]
              }
            ]
          }
        ]
      }
    }
  ]
}
```

#### POST /fhir/generate/CodeSystem
**Description**: Generate FHIR CodeSystem for specified terminology system  
**Authentication**: Required

**Parameters:**
- `system` (required): Terminology system URI

**Example:**
```bash
POST /fhir/generate/CodeSystem?system=http://terminology.ayush.gov.in/namaste
```

**Response:** Returns complete FHIR CodeSystem JSON

#### POST /fhir/generate/ConceptMap
**Description**: Generate FHIR ConceptMap between terminology systems  
**Authentication**: Required

**Parameters:**
- `source_system` (optional): Source system URI (default: NAMASTE)
- `target_system` (optional): Target system URI (default: ICD-11 TM2)

**Response:** Returns complete FHIR ConceptMap JSON

### 9. Analytics

#### GET /analytics/dashboard
**Description**: Get dashboard analytics data  
**Authentication**: Required

**Response:**
```json
{
  "summary": {
    "namaste_codes": 25,
    "icd11_codes": 15,
    "total_mappings": 18,
    "active_users": 3
  },
  "mapping_statistics": {
    "total_mappings": 18,
    "confidence_distribution": {
      "high": 15,
      "medium": 2,
      "low": 1
    },
    "method_distribution": {
      "fuzzy_match": 12,
      "manual": 6
    }
  },
  "namaste_statistics": {
    "total_codes": 25,
    "categories": ["Metabolic Disorders", "Infectious Diseases", "Respiratory Disorders"],
    "systems": ["Ayurveda"]
  },
  "recent_activity": [
    {
      "timestamp": "2024-01-15T10:25:00Z",
      "action": "terminology_search",
      "user": "admin",
      "details": {"search_term": "diabetes"}
    }
  ],
  "generated_at": "2024-01-15T10:30:00Z"
}
```

## Error Responses

The API uses standard HTTP status codes and returns consistent error responses:

### 400 Bad Request
```json
{
  "detail": "Validation error: Invalid input data"
}
```

### 401 Unauthorized
```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden
```json
{
  "detail": "Required role: admin"
}
```

### 404 Not Found
```json
{
  "error": "Not Found",
  "message": "The requested resource was not found",
  "path": "/nonexistent"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "username"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal Server Error",
  "message": "An internal server error occurred",
  "path": "/endpoint"
}
```

## Rate Limits

- **Search endpoints**: 100 requests per minute per user
- **Upload endpoints**: 10 requests per minute per user
- **Authentication endpoints**: 20 requests per minute per IP

## Data Formats

### Terminology Systems

The API supports the following terminology systems:

- **NAMASTE**: `http://terminology.ayush.gov.in/namaste`
- **ICD-11 TM2**: `http://id.who.int/icd/release/11/tm2`
- **SNOMED CT**: `http://snomed.info/sct` (future)
- **LOINC**: `http://loinc.org` (future)

### ABHA ID Format

ABHA IDs must follow the format: `14-XXXX-XXXX-XXXX`

Examples:
- `14-1234-5678-9012`
- `14-5678-9012-3456`
- `14-9012-3456-7890`

### CSV Upload Format

NAMASTE CSV files must contain the following columns:

**Required columns:**
- `code`: Unique terminology code
- `display`: Human-readable display name

**Optional columns:**
- `definition`: Detailed definition
- `category`: Category classification
- `subcategory`: Subcategory classification
- `system_name`: Source system name
- `severity`: Severity level
- Any other custom properties

**Example CSV:**
```csv
code,display,definition,category,system_name
PRAM001,Prameha,A condition characterized by excessive urination and thirst,Metabolic Disorders,Ayurveda
JWARA001,Jwara,Fever or elevated body temperature,Infectious Diseases,Ayurveda
```

## SDK Examples

### Python

```python
import requests

# Authentication
auth_response = requests.post("http://localhost:8000/auth/token", data={
    "username": "admin",
    "password": "admin123"
})
token = auth_response.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Search
search_response = requests.get(
    "http://localhost:8000/search?term=diabetes",
    headers=headers
)
results = search_response.json()

# Translate
translate_response = requests.get(
    "http://localhost:8000/translate?source=http://terminology.ayush.gov.in/namaste&target=http://id.who.int/icd/release/11/tm2&code=PRAM001",
    headers=headers
)
translation = translate_response.json()
```

### JavaScript

```javascript
// Authentication
const authResponse = await fetch("http://localhost:8000/auth/token", {
  method: "POST",
  headers: {"Content-Type": "application/x-www-form-urlencoded"},
  body: "username=admin&password=admin123"
});
const {access_token} = await authResponse.json();

// Search
const searchResponse = await fetch("http://localhost:8000/search?term=diabetes", {
  headers: {"Authorization": `Bearer ${access_token}`}
});
const results = await searchResponse.json();

// Upload CSV
const formData = new FormData();
formData.append("file", csvFile);
const uploadResponse = await fetch("http://localhost:8000/upload/namaste", {
  method: "POST",
  headers: {"Authorization": `Bearer ${access_token}`},
  body: formData
});
```

### cURL

```bash
# Authentication
TOKEN=$(curl -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123" | jq -r '.access_token')

# Search
curl -X GET "http://localhost:8000/search?term=diabetes" \
  -H "Authorization: Bearer $TOKEN"

# Upload CSV
curl -X POST "http://localhost:8000/upload/namaste" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@namaste_codes.csv"

# Generate FHIR CodeSystem
curl -X POST "http://localhost:8000/fhir/generate/CodeSystem?system=http://terminology.ayush.gov.in/namaste" \
  -H "Authorization: Bearer $TOKEN"
```

## Versioning

The API uses URL versioning. The current version is `v1` (implicit in base URL).

Future versions will use the pattern: `http://localhost:8000/v2/...`

## Support

For API support and questions:
- **Documentation**: http://localhost:8000/docs
- **GitHub Issues**: [Project Repository]
- **Email**: support@example.com

## Changelog

### v1.0.0 (2024-01-15)
- Initial API release
- FHIR R4 compliance
- NAMASTE and ICD-11 TM2 support
- ABHA authentication integration
- Search and translation endpoints
- File upload functionality
- Analytics dashboard
