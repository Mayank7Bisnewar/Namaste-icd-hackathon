"""
Database Models and Operations

This module provides database models and operations for storing FHIR resources,
mappings, users, and audit logs using SQLAlchemy.
"""

import os
import sys
from datetime import datetime
from typing import List, Optional, Dict, Any
import json

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, DateTime, 
    Boolean, Float, ForeignKey, JSON, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON

# Database configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(DATA_DIR, 'fhir_mapping.db')}")
engine = create_engine(DATABASE_URL, echo=os.getenv("DATABASE_ECHO", "false").lower() == "true")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """User model for authentication and authorization"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    abha_id = Column(String(50), unique=True, index=True)
    full_name = Column(String(100))
    hashed_password = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    role = Column(String(20), default="user")  # user, admin, clinician
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    
    # Relationships
    audit_logs = relationship("AuditLog", back_populates="user")
    consents = relationship("ConsentRecord", back_populates="user")


class TerminologyCode(Base):
    """Model for storing terminology codes from various systems"""
    __tablename__ = "terminology_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    system = Column(String(200), index=True, nullable=False)  # NAMASTE, ICD-11, etc.
    code = Column(String(100), index=True, nullable=False)
    display = Column(Text)
    definition = Column(Text)
    properties = Column(JSON)
    version = Column(String(20), default="1.0.0")
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    source_mappings = relationship("CodeMapping", foreign_keys="[CodeMapping.source_code_id]", back_populates="source_code")
    target_mappings = relationship("CodeMapping", foreign_keys="[CodeMapping.target_code_id]", back_populates="target_code")
    
    __table_args__ = (
        Index('ix_system_code', 'system', 'code'),
    )


class CodeMapping(Base):
    """Model for storing code mappings between terminology systems"""
    __tablename__ = "code_mappings"
    
    id = Column(Integer, primary_key=True, index=True)
    source_code_id = Column(Integer, ForeignKey("terminology_codes.id"), nullable=False)
    target_code_id = Column(Integer, ForeignKey("terminology_codes.id"), nullable=False)
    equivalence = Column(String(20), default="equivalent")  # FHIR equivalence values
    confidence = Column(Float, default=1.0)
    mapping_method = Column(String(50))  # manual, automatic, nlp, etc.
    mapped_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime)
    verified_by = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    source_code = relationship("TerminologyCode", foreign_keys=[source_code_id])
    target_code = relationship("TerminologyCode", foreign_keys=[target_code_id])
    mapper = relationship("User", foreign_keys=[mapped_by])
    verifier = relationship("User", foreign_keys=[verified_by])


class FHIRResource(Base):
    """Model for storing serialized FHIR resources"""
    __tablename__ = "fhir_resources"
    
    id = Column(Integer, primary_key=True, index=True)
    resource_id = Column(String(100), unique=True, index=True, nullable=False)
    resource_type = Column(String(50), index=True, nullable=False)
    version_id = Column(String(20), default="1")
    content = Column(Text, nullable=False)  # JSON serialized FHIR resource
    meta_last_updated = Column(DateTime, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    
    __table_args__ = (
        Index('ix_resource_type_id', 'resource_type', 'resource_id'),
    )


class AuditLog(Base):
    """Model for audit logging"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    abha_id = Column(String(50), index=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50))
    resource_id = Column(String(100))
    details = Column(JSON)
    ip_address = Column(String(45))  # Support IPv6
    user_agent = Column(Text)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")


class ConsentRecord(Base):
    """Model for tracking user consent"""
    __tablename__ = "consent_records"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    abha_id = Column(String(50), index=True)
    consent_type = Column(String(50), nullable=False)  # data_sharing, analytics, etc.
    status = Column(String(20), default="granted")  # granted, revoked, expired
    granted_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    revoked_at = Column(DateTime)
    details = Column(JSON)
    
    # Relationships
    user = relationship("User", back_populates="consents")


class SearchHistory(Base):
    """Model for tracking search queries and results"""
    __tablename__ = "search_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    search_term = Column(String(500), nullable=False)
    search_type = Column(String(50))  # term_search, code_lookup, translation
    results_count = Column(Integer, default=0)
    execution_time_ms = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])


# Database utility functions
def get_db() -> Session:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    # Create data directory if it doesn't exist
    os.makedirs("./data", exist_ok=True)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create default admin user if doesn't exist
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from auth import get_password_hash
            admin_user = User(
                username="admin",
                email="admin@example.com",
                full_name="System Administrator",
                hashed_password=get_password_hash("admin123"),
                role="admin",
                is_active=True,
                is_verified=True
            )
            db.add(admin_user)
            db.commit()
            print("Default admin user created: admin/admin123")
    except Exception as e:
        print(f"Error creating admin user: {e}")
    finally:
        db.close()


class DatabaseOperations:
    """Database operations class"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_terminology_code(
        self,
        system: str,
        code: str,
        display: str = "",
        definition: str = "",
        properties: Optional[Dict[str, Any]] = None
    ) -> TerminologyCode:
        """Create a new terminology code"""
        
        # Check if code already exists
        existing = self.db.query(TerminologyCode).filter(
            TerminologyCode.system == system,
            TerminologyCode.code == code
        ).first()
        
        if existing:
            return existing
        
        terminology_code = TerminologyCode(
            system=system,
            code=code,
            display=display,
            definition=definition,
            properties=properties or {}
        )
        
        self.db.add(terminology_code)
        self.db.commit()
        self.db.refresh(terminology_code)
        
        return terminology_code
    
    def create_code_mapping(
        self,
        source_code_id: int,
        target_code_id: int,
        equivalence: str = "equivalent",
        confidence: float = 1.0,
        mapping_method: str = "manual",
        mapped_by: Optional[int] = None
    ) -> CodeMapping:
        """Create a new code mapping"""
        
        # Check if mapping already exists
        existing = self.db.query(CodeMapping).filter(
            CodeMapping.source_code_id == source_code_id,
            CodeMapping.target_code_id == target_code_id
        ).first()
        
        if existing:
            return existing
        
        mapping = CodeMapping(
            source_code_id=source_code_id,
            target_code_id=target_code_id,
            equivalence=equivalence,
            confidence=confidence,
            mapping_method=mapping_method,
            mapped_by=mapped_by
        )
        
        self.db.add(mapping)
        self.db.commit()
        self.db.refresh(mapping)
        
        return mapping
    
    def store_fhir_resource(
        self,
        resource_id: str,
        resource_type: str,
        content: str,
        created_by: Optional[int] = None
    ) -> FHIRResource:
        """Store a FHIR resource"""
        
        # Check if resource already exists
        existing = self.db.query(FHIRResource).filter(
            FHIRResource.resource_id == resource_id
        ).first()
        
        if existing:
            # Update existing resource
            existing.content = content
            existing.meta_last_updated = datetime.utcnow()
            self.db.commit()
            return existing
        
        fhir_resource = FHIRResource(
            resource_id=resource_id,
            resource_type=resource_type,
            content=content,
            created_by=created_by
        )
        
        self.db.add(fhir_resource)
        self.db.commit()
        self.db.refresh(fhir_resource)
        
        return fhir_resource
    
    def log_audit_event(
        self,
        action: str,
        user_id: Optional[int] = None,
        abha_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> AuditLog:
        """Log an audit event"""
        
        audit_log = AuditLog(
            user_id=user_id,
            abha_id=abha_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            error_message=error_message
        )
        
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        
        return audit_log
    
    def search_terminology_codes(
        self,
        search_term: str,
        system: Optional[str] = None,
        limit: int = 50
    ) -> List[TerminologyCode]:
        """Search terminology codes"""
        
        query = self.db.query(TerminologyCode)
        
        # Filter by system if provided
        if system:
            query = query.filter(TerminologyCode.system == system)
        
        # Search in code, display, and definition
        search_filter = (
            TerminologyCode.code.contains(search_term) |
            TerminologyCode.display.contains(search_term) |
            TerminologyCode.definition.contains(search_term)
        )
        
        query = query.filter(search_filter)
        query = query.limit(limit)
        
        return query.all()
    
    def get_code_mappings(
        self,
        source_system: Optional[str] = None,
        target_system: Optional[str] = None,
        source_code: Optional[str] = None
    ) -> List[CodeMapping]:
        """Get code mappings with filters"""
        
        query = self.db.query(CodeMapping).join(
            TerminologyCode, CodeMapping.source_code_id == TerminologyCode.id
        ).join(
            TerminologyCode, CodeMapping.target_code_id == TerminologyCode.id
        )
        
        if source_system:
            query = query.filter(TerminologyCode.system == source_system)
        
        if source_code:
            query = query.filter(TerminologyCode.code == source_code)
        
        return query.all()


def create_sample_data():
    """Create sample data for testing"""
    db = SessionLocal()
    db_ops = DatabaseOperations(db)
    
    try:
        # Sample NAMASTE codes
        namaste_codes = [
            {
                "system": "http://terminology.ayush.gov.in/namaste",
                "code": "PRAM001",
                "display": "Prameha",
                "definition": "A condition characterized by excessive urination and thirst"
            },
            {
                "system": "http://terminology.ayush.gov.in/namaste",
                "code": "JWARA001",
                "display": "Jwara",
                "definition": "Fever or elevated body temperature"
            },
            {
                "system": "http://terminology.ayush.gov.in/namaste",
                "code": "KASA001",
                "display": "Kasa",
                "definition": "Cough or respiratory condition"
            }
        ]
        
        # Sample ICD-11 TM2 codes
        icd_codes = [
            {
                "system": "http://id.who.int/icd/release/11/tm2",
                "code": "TM-E11",
                "display": "Diabetes mellitus",
                "definition": "A group of metabolic diseases characterized by high blood sugar"
            },
            {
                "system": "http://id.who.int/icd/release/11/tm2",
                "code": "TM-R50",
                "display": "Fever, unspecified",
                "definition": "Elevation of body temperature above normal"
            },
            {
                "system": "http://id.who.int/icd/release/11/tm2",
                "code": "TM-R05",
                "display": "Cough",
                "definition": "A sudden, forceful expulsion of air from the lungs"
            }
        ]
        
        # Create codes
        created_codes = {}
        
        for code_data in namaste_codes + icd_codes:
            code = db_ops.create_terminology_code(**code_data)
            created_codes[f"{code_data['system']}#{code_data['code']}"] = code
        
        # Create mappings
        mappings = [
            {
                "source": "http://terminology.ayush.gov.in/namaste#PRAM001",
                "target": "http://id.who.int/icd/release/11/tm2#TM-E11",
                "equivalence": "equivalent",
                "confidence": 0.9
            },
            {
                "source": "http://terminology.ayush.gov.in/namaste#JWARA001",
                "target": "http://id.who.int/icd/release/11/tm2#TM-R50",
                "equivalence": "equivalent",
                "confidence": 0.95
            },
            {
                "source": "http://terminology.ayush.gov.in/namaste#KASA001",
                "target": "http://id.who.int/icd/release/11/tm2#TM-R05",
                "equivalence": "equivalent",
                "confidence": 0.85
            }
        ]
        
        for mapping_data in mappings:
            source_code = created_codes[mapping_data["source"]]
            target_code = created_codes[mapping_data["target"]]
            
            db_ops.create_code_mapping(
                source_code_id=source_code.id,
                target_code_id=target_code.id,
                equivalence=mapping_data["equivalence"],
                confidence=mapping_data["confidence"],
                mapping_method="sample_data"
            )
        
        print("Sample data created successfully")
        
    except Exception as e:
        print(f"Error creating sample data: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    create_sample_data()
