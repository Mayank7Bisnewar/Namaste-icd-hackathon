"""
FastAPI Main Application

FHIR R4-compliant REST API for healthcare terminology mapping between
NAMASTE and ICD-11 TM2 systems with ABHA authentication.
"""

import os
import time
import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import uvicorn

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, init_db, DatabaseOperations, User, TerminologyCode
from auth import (
    authenticate_user, create_token_response, get_current_active_user,
    abha_service, UserCreate, UserService, Token, ABHATokenRequest
)
from fhir_resources import (
    SearchResult, TranslationResult, TerminologySystem, MappingEquivalence,
    FHIRResourceBuilder, validate_fhir_resource
)
from missing_classes import (
    DatabaseOperations, NAMASTEDataService, NAMASTELoader, 
    ICDDataService, MappingService, create_token_response, abha_service
)

# Initialize FastAPI app
app = FastAPI(
    title="FHIR NAMASTE-ICD Mapping Service",
    description="Healthcare terminology mapping service with FHIR R4 compliance",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],  # Streamlit frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    try:
        init_db()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")


# Middleware for request logging and timing
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and measure execution time"""
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate execution time
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log request (in production, use proper logging)
    print(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    
    return response


# Health check endpoints
@app.get("/", tags=["Health"])
async def root():
    """Root endpoint for health check"""
    return {
        "message": "FHIR NAMASTE-ICD Mapping Service",
        "version": "1.0.0",
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/health", tags=["Health"])
async def health_check(db: Session = Depends(get_db)):
    """Detailed health check"""
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"
    
    return {
        "service": "FHIR NAMASTE-ICD Mapping Service",
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.now().isoformat(),
        "components": {
            "fhir": "ready",
            "authentication": "ready",
            "terminology_services": "ready"
        }
    }


# Authentication endpoints
@app.post("/auth/token", response_model=Token, tags=["Authentication"])
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Authenticate user and return JWT token"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Log authentication
    db_ops = DatabaseOperations(db)
    db_ops.log_audit_event(
        action="user_login",
        user_id=user.id,
        abha_id=user.abha_id,
        details={"username": user.username}
    )
    
    return create_token_response(user)


@app.post("/auth/register", response_model=Dict[str, Any], tags=["Authentication"])
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user"""
    try:
        user_service = UserService(db)
        user = user_service.create_user(user_data)
        
        # Log registration
        db_ops = DatabaseOperations(db)
        db_ops.log_audit_event(
            action="user_registration",
            user_id=user.id,
            abha_id=user.abha_id,
            details={"username": user.username}
        )
        
        return {
            "message": "User registered successfully",
            "user_id": user.id,
            "username": user.username
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@app.post("/auth/abha", response_model=Token, tags=["Authentication"])
async def authenticate_with_abha(
    abha_request: ABHATokenRequest,
    db: Session = Depends(get_db)
):
    """Authenticate user with ABHA ID and OTP"""
    try:
        # Authenticate with ABHA service
        abha_token_data = await abha_service.authenticate_with_otp(
            abha_request.abha_id, 
            abha_request.otp or "123456"  # Default OTP for demo
        )
        
        # Get or create user with ABHA ID
        user_service = UserService(db)
        user = user_service.get_user_by_abha_id(abha_request.abha_id)
        
        if not user:
            # Get ABHA user info
            abha_user_info = await abha_service.get_user_info(abha_token_data["access_token"])
            
            # Create new user
            user = user_service.create_user(UserCreate(
                username=abha_user_info.abha_id.replace("-", "_"),
                email=abha_user_info.email or f"{abha_user_info.abha_id}@example.com",
                full_name=abha_user_info.name,
                password="abha_authenticated",  # Temporary password
                abha_id=abha_user_info.abha_id
            ))
        
        # Log ABHA authentication
        db_ops = DatabaseOperations(db)
        db_ops.log_audit_event(
            action="abha_authentication",
            user_id=user.id,
            abha_id=user.abha_id,
            details={"auth_method": abha_request.auth_method}
        )
        
        return create_token_response(user)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ABHA authentication failed: {str(e)}"
        )


# Search endpoints
@app.get("/search", response_model=List[SearchResult], tags=["Search"])
async def search_terminology_codes(
    term: str,
    system: Optional[str] = None,
    limit: int = 50,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Search for terminology codes across systems"""
    try:
        start_time = time.time()
        
        db_ops = DatabaseOperations(db)
        results = []
        
        # Search in specified system or all systems
        if system:
            codes = db_ops.search_terminology_codes(term, system, limit)
        else:
            # Search across all systems
            codes = db_ops.search_terminology_codes(term, limit=limit)
        
        # Convert to SearchResult format
        for code in codes:
            result = SearchResult(
                code=code.code,
                display=code.display,
                system=code.system,
                definition=code.definition,
                properties=code.properties
            )
            results.append(result)
        
        # Log search activity
        execution_time = (time.time() - start_time) * 1000
        db_ops.log_audit_event(
            action="terminology_search",
            user_id=current_user.id,
            abha_id=current_user.abha_id,
            details={
                "search_term": term,
                "system": system,
                "results_count": len(results),
                "execution_time_ms": execution_time
            }
        )
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@app.get("/translate", response_model=Optional[TranslationResult], tags=["Translation"])
async def translate_code(
    source: str,
    target: str,
    code: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Translate code between terminology systems"""
    try:
        mapping_service = MappingService(db)
        
        # Translate code
        translation = mapping_service.translate_code(code, source, target)
        
        if not translation:
            # Log failed translation
            db_ops = DatabaseOperations(db)
            db_ops.log_audit_event(
                action="code_translation_failed",
                user_id=current_user.id,
                abha_id=current_user.abha_id,
                details={
                    "source_system": source,
                    "target_system": target,
                    "code": code
                }
            )
            return None
        
        # Convert to TranslationResult
        result = TranslationResult(
            source_code=translation["source_code"],
            source_system=translation["source_system"],
            target_code=translation["target_code"],
            target_system=translation["target_system"],
            equivalence=translation["equivalence"],
            confidence=translation["confidence"]
        )
        
        # Log successful translation
        db_ops = DatabaseOperations(db)
        db_ops.log_audit_event(
            action="code_translation_success",
            user_id=current_user.id,
            abha_id=current_user.abha_id,
            details={
                "source_system": source,
                "target_system": target,
                "source_code": code,
                "target_code": translation["target_code"],
                "confidence": translation["confidence"]
            }
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Translation failed: {str(e)}"
        )


# Data upload endpoints
@app.post("/upload/namaste", tags=["Data Upload"])
async def upload_namaste_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload NAMASTE CSV file and process codes"""
    try:
        if not file.filename.endswith('.csv'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be a CSV file"
            )
        
        # Read file content
        file_content = await file.read()
        
        # Process with NAMASTE service
        namaste_service = NAMASTEDataService(db)
        result = namaste_service.upload_csv_file(file_content, file.filename)
        
        # Log upload activity
        db_ops = DatabaseOperations(db)
        db_ops.log_audit_event(
            action="namaste_csv_upload",
            user_id=current_user.id,
            abha_id=current_user.abha_id,
            details={
                "filename": file.filename,
                "file_size": len(file_content),
                "success": result["success"],
                "codes_loaded": result.get("codes_loaded", 0)
            }
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}"
        )


@app.post("/sync/icd11", tags=["Data Sync"])
async def sync_icd11_codes(
    search_terms: Optional[List[str]] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Synchronize ICD-11 TM2 codes"""
    try:
        icd_service = ICDDataService(db)
        result = await icd_service.sync_tm2_codes(search_terms)
        
        # Log sync activity
        db_ops = DatabaseOperations(db)
        db_ops.log_audit_event(
            action="icd11_sync",
            user_id=current_user.id,
            abha_id=current_user.abha_id,
            details={
                "search_terms": search_terms,
                "codes_synced": result.get("codes_synced", 0),
                "success": result["success"]
            }
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sync failed: {str(e)}"
        )


# Mapping endpoints
@app.post("/mappings/create", tags=["Mappings"])
async def create_automatic_mappings(
    source_system: str = TerminologySystem.NAMASTE,
    target_system: str = TerminologySystem.ICD11_TM2,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create automatic mappings between terminology systems"""
    try:
        mapping_service = MappingService(db)
        result = await mapping_service.create_automatic_mappings(source_system, target_system)
        
        # Log mapping creation
        db_ops = DatabaseOperations(db)
        db_ops.log_audit_event(
            action="automatic_mapping_creation",
            user_id=current_user.id,
            abha_id=current_user.abha_id,
            details={
                "source_system": source_system,
                "target_system": target_system,
                "mappings_created": result.get("mappings_created", 0)
            }
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Mapping creation failed: {str(e)}"
        )


@app.get("/mappings/statistics", tags=["Mappings"])
async def get_mapping_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get mapping statistics"""
    try:
        mapping_service = MappingService(db)
        stats = mapping_service.get_mapping_statistics()
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


# FHIR endpoints
@app.get("/fhir/CodeSystem", tags=["FHIR"])
async def get_code_systems(
    system: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get FHIR CodeSystem resources"""
    try:
        from database import FHIRResource
        
        query = db.query(FHIRResource).filter(FHIRResource.resource_type == "CodeSystem")
        
        if system:
            # Filter by system URI (this would require parsing the content)
            resources = query.all()
            filtered_resources = []
            
            for resource in resources:
                try:
                    import json
                    content = json.loads(resource.content)
                    if content.get("url") == system:
                        filtered_resources.append(resource)
                except:
                    continue
            
            resources = filtered_resources
        else:
            resources = query.all()
        
        # Return FHIR resources
        result = {
            "resourceType": "Bundle",
            "id": f"codesystems-{datetime.now().timestamp()}",
            "type": "collection",
            "total": len(resources),
            "entry": []
        }
        
        for resource in resources:
            try:
                import json
                content = json.loads(resource.content)
                result["entry"].append({
                    "resource": content
                })
            except Exception as e:
                print(f"Error parsing FHIR resource: {e}")
                continue
        
        # Log FHIR access
        db_ops = DatabaseOperations(db)
        db_ops.log_audit_event(
            action="fhir_codesystem_access",
            user_id=current_user.id,
            abha_id=current_user.abha_id,
            resource_type="CodeSystem",
            details={"system_filter": system, "results_count": len(resources)}
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get CodeSystems: {str(e)}"
        )


@app.get("/fhir/ConceptMap", tags=["FHIR"])
async def get_concept_maps(
    source: Optional[str] = None,
    target: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get FHIR ConceptMap resources"""
    try:
        from database import FHIRResource
        
        query = db.query(FHIRResource).filter(FHIRResource.resource_type == "ConceptMap")
        resources = query.all()
        
        # Filter by source/target if provided
        if source or target:
            filtered_resources = []
            for resource in resources:
                try:
                    import json
                    content = json.loads(resource.content)
                    if ((source and content.get("sourceUri") == source) or
                        (target and content.get("targetUri") == target) or
                        (not source and not target)):
                        filtered_resources.append(resource)
                except:
                    continue
            resources = filtered_resources
        
        # Return FHIR Bundle
        result = {
            "resourceType": "Bundle",
            "id": f"conceptmaps-{datetime.now().timestamp()}",
            "type": "collection",
            "total": len(resources),
            "entry": []
        }
        
        for resource in resources:
            try:
                import json
                content = json.loads(resource.content)
                result["entry"].append({
                    "resource": content
                })
            except Exception as e:
                print(f"Error parsing FHIR resource: {e}")
                continue
        
        # Log FHIR access
        db_ops = DatabaseOperations(db)
        db_ops.log_audit_event(
            action="fhir_conceptmap_access",
            user_id=current_user.id,
            abha_id=current_user.abha_id,
            resource_type="ConceptMap",
            details={
                "source_filter": source,
                "target_filter": target,
                "results_count": len(resources)
            }
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get ConceptMaps: {str(e)}"
        )


@app.post("/fhir/generate/CodeSystem", tags=["FHIR"])
async def generate_codesystem(
    system: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate FHIR CodeSystem for specified terminology system"""
    try:
        if system == TerminologySystem.NAMASTE:
            namaste_service = NAMASTEDataService(db)
            codes = db.query(TerminologyCode).filter(
                TerminologyCode.system == TerminologySystem.NAMASTE
            ).all()
            
            if not codes:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No NAMASTE codes found. Upload CSV data first."
                )
            
            loader = NAMASTELoader(db)
            fhir_json = loader.create_fhir_codesystem(codes)
            
        elif system == TerminologySystem.ICD11_TM2:
            icd_service = ICDDataService(db)
            fhir_json = icd_service.create_fhir_codesystem()
            
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported terminology system: {system}"
            )
        
        # Log CodeSystem generation
        db_ops = DatabaseOperations(db)
        db_ops.log_audit_event(
            action="fhir_codesystem_generation",
            user_id=current_user.id,
            abha_id=current_user.abha_id,
            resource_type="CodeSystem",
            details={"system": system}
        )
        
        return JSONResponse(content=json.loads(fhir_json))
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"CodeSystem generation failed: {str(e)}"
        )


@app.post("/fhir/generate/ConceptMap", tags=["FHIR"])
async def generate_conceptmap(
    source_system: str = TerminologySystem.NAMASTE,
    target_system: str = TerminologySystem.ICD11_TM2,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate FHIR ConceptMap between terminology systems"""
    try:
        mapping_service = MappingService(db)
        fhir_json = mapping_service.create_fhir_conceptmap(source_system, target_system)
        
        # Log ConceptMap generation
        db_ops = DatabaseOperations(db)
        db_ops.log_audit_event(
            action="fhir_conceptmap_generation",
            user_id=current_user.id,
            abha_id=current_user.abha_id,
            resource_type="ConceptMap",
            details={
                "source_system": source_system,
                "target_system": target_system
            }
        )
        
        return JSONResponse(content=json.loads(fhir_json))
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ConceptMap generation failed: {str(e)}"
        )


# Analytics and reporting endpoints
@app.get("/analytics/dashboard", tags=["Analytics"])
async def get_dashboard_data(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get dashboard analytics data"""
    try:
        # Get various statistics
        mapping_service = MappingService(db)
        namaste_service = NAMASTEDataService(db)
        
        mapping_stats = mapping_service.get_mapping_statistics()
        namaste_stats = namaste_service.get_statistics()
        
        # Count ICD codes
        icd_count = db.query(TerminologyCode).filter(
            TerminologyCode.system == TerminologySystem.ICD11_TM2
        ).count()
        
        # Get recent activity
        from database import AuditLog
        recent_activity = db.query(AuditLog).filter(
            AuditLog.timestamp >= datetime.now() - timedelta(days=7)
        ).order_by(AuditLog.timestamp.desc()).limit(10).all()
        
        dashboard_data = {
            "summary": {
                "namaste_codes": namaste_stats.get("total_codes", 0),
                "icd11_codes": icd_count,
                "total_mappings": mapping_stats.get("total_mappings", 0),
                "active_users": db.query(User).filter(User.is_active == True).count()
            },
            "mapping_statistics": mapping_stats,
            "namaste_statistics": namaste_stats,
            "recent_activity": [
                {
                    "timestamp": log.timestamp.isoformat(),
                    "action": log.action,
                    "user": log.user.username if log.user else "System",
                    "details": log.details
                }
                for log in recent_activity
            ],
            "generated_at": datetime.now().isoformat()
        }
        
        return dashboard_data
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard data: {str(e)}"
        )


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """Handle 404 errors"""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "message": "The requested resource was not found",
            "path": str(request.url.path)
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    """Handle 500 errors"""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An internal server error occurred",
            "path": str(request.url.path)
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "localhost"),
        port=int(os.getenv("PORT", "8000")),
        reload=True
    )
