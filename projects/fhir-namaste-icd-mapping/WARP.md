# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

This is a FHIR R4-compliant healthcare interoperability service that enables dual-coding between NAMASTE (Ayush terminology) and ICD-11 TM2 systems, with ABHA authentication integration. The service provides terminology mapping, search, translation, and FHIR resource generation capabilities.

## Common Commands

### Initial Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Initialize project and database
python init_project.py

# Set up environment variables
cp .env.example .env
```

### Development Commands
```bash
# Start backend API server
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Alternative: Use startup script
./start_backend.sh

# Start frontend GUI
cd frontend
streamlit run app.py --server.port 8501 --server.address 0.0.0.0

# Alternative: Use startup script
./start_frontend.sh

# Start both services
./start_services.sh
```

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_api.py -v

# Run tests with coverage
pytest tests/ --cov=backend --cov-report=html
```

### Database Operations
```bash
# Initialize database directly
python -c "from backend.database import init_db; init_db()"

# Access database directly (SQLite)
sqlite3 data/fhir_mapping.db

# Reset database (careful - destructive)
rm data/fhir_mapping.db && python init_project.py
```

### API Development
```bash
# View API documentation
# Open http://localhost:8000/docs (Swagger UI)
# Open http://localhost:8000/redoc (ReDoc)

# Test API endpoints
curl -X GET "http://localhost:8000/health"

# Get authentication token
curl -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

### Code Quality
```bash
# Format code
black backend/ frontend/ tests/

# Check code style
flake8 backend/ frontend/ tests/

# Type checking
mypy backend/
```

## Architecture

### Core Components

**Backend (FastAPI)**:
- `main.py` - FastAPI application entry point with all endpoints
- `auth.py` - JWT authentication with ABHA integration
- `database.py` - SQLAlchemy models and database operations
- `fhir_resources.py` - FHIR R4 resource builders and models
- `namaste_loader.py` - NAMASTE CSV data processing
- `icd_api.py` - ICD-11 API integration and mapping services

**Frontend (Streamlit)**:
- `app.py` - Complete web interface with authentication, search, translate, upload, and analytics tabs

### Authentication Flow

1. **Traditional Login**: Username/password → JWT token
2. **ABHA Login**: ABHA ID + OTP → Mock ABHA service → JWT token
3. **Token Usage**: All authenticated endpoints require `Authorization: Bearer <token>` header

### Database Architecture

**Core Tables**:
- `users` - User accounts with ABHA integration
- `terminology_codes` - All terminology codes (NAMASTE, ICD-11, etc.)
- `code_mappings` - Mappings between different terminology systems
- `fhir_resources` - Generated FHIR resources (CodeSystem, ConceptMap)
- `audit_logs` - Comprehensive audit trail
- `consent_records` - GDPR/consent management

### FHIR Resource Generation

The service generates FHIR R4 resources:
- **CodeSystem**: For NAMASTE and ICD-11 terminologies
- **ConceptMap**: For mappings between systems
- **Patient**: With ABHA ID integration
- **Encounter**: For clinical encounter coding

### Key Terminology Systems

- **NAMASTE**: `http://terminology.ayush.gov.in/namaste`
- **ICD-11 TM2**: `http://id.who.int/icd/release/11/tm2`
- **SNOMED CT**: `http://snomed.info/sct`
- **LOINC**: `http://loinc.org`

## Development Patterns

### API Endpoint Structure
All endpoints follow this pattern:
1. Authentication check (except public endpoints)
2. Input validation
3. Business logic execution
4. Audit logging
5. Response formatting
6. Error handling

### Database Operations
Use the `DatabaseOperations` class for consistent database interactions:
```python
from database import DatabaseOperations
db_ops = DatabaseOperations(db)
results = db_ops.search_terminology_codes(term, system)
```

### FHIR Resource Creation
Use the `FHIRResourceBuilder` for creating FHIR resources:
```python
from fhir_resources import FHIRResourceBuilder
codesystem = FHIRResourceBuilder.create_codesystem(
    system_uri, name, title, description, concepts
)
```

### Authentication Dependencies
Use FastAPI dependencies for authentication:
```python
def protected_endpoint(current_user: User = Depends(get_current_active_user)):
    # Endpoint logic here
```

## Service URLs

- **Backend API**: http://localhost:8000
- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative API Docs**: http://localhost:8000/redoc
- **Frontend GUI**: http://localhost:8501

## Demo Data

**Default Admin User**:
- Username: `admin`
- Password: `admin123`

**Sample ABHA IDs**:
- `14-1234-5678-9012`
- `14-5678-9012-3456`
- `14-9012-3456-7890`
- OTP: Any 6 digits (mock implementation)

**Sample NAMASTE Codes**:
- `PRAM001` - Prameha (diabetes-related condition)
- `JWARA001` - Jwara (fever)
- `MADHUMEHA001` - Madhumeha (diabetes mellitus)
- `SANDHIVATA001` - Sandhivata (arthritis)

## Error Handling Patterns

The application uses consistent error handling:
- HTTP 401 for authentication failures
- HTTP 403 for authorization failures  
- HTTP 400 for validation errors
- HTTP 404 for resource not found
- HTTP 500 for internal server errors

All errors are logged to the audit trail with contextual information.

## Key Configuration

Environment variables are defined in `.env.example`:
- Database URL and configuration
- JWT secret and expiration
- ABHA service endpoints (mock)
- ICD API credentials
- Feature flags for NLP, audit logging, consent management
