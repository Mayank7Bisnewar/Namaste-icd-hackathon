"""
Advanced Features Module

This module provides enhanced functionality including fuzzy search,
NLP auto-suggestions, consent management, and advanced error handling.
"""

import os
import re
import json
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .database import DatabaseOperations, TerminologyCode, ConsentRecord, User
from .fhir_resources import TerminologySystem


class FuzzySearchService:
    """Enhanced search service with fuzzy matching capabilities"""
    
    def __init__(self, db: Session):
        self.db = db
        self.db_ops = DatabaseOperations(db)
    
    def fuzzy_search_codes(
        self, 
        search_term: str, 
        system: Optional[str] = None,
        threshold: float = 0.6,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Perform fuzzy search with similarity scoring"""
        
        try:
            from fuzzywuzzy import fuzz, process
            
            # Get all codes from specified system or all systems
            query = self.db.query(TerminologyCode)
            if system:
                query = query.filter(TerminologyCode.system == system)
            
            all_codes = query.all()
            
            # Create search choices
            choices = {}
            for code in all_codes:
                # Create searchable string
                search_string = f"{code.display} {code.definition or ''} {code.code}"
                choices[search_string] = code
            
            # Perform fuzzy matching
            matches = process.extract(
                search_term,
                choices.keys(),
                scorer=fuzz.token_sort_ratio,
                limit=limit * 2  # Get more to filter by threshold
            )
            
            # Filter by threshold and format results
            results = []
            for match_text, score in matches:
                if score >= (threshold * 100):
                    code = choices[match_text]
                    result = {
                        "code": code.code,
                        "display": code.display,
                        "definition": code.definition,
                        "system": code.system,
                        "properties": json.loads(code.properties) if code.properties else {},
                        "similarity_score": score / 100.0,
                        "search_method": "fuzzy_match"
                    }
                    results.append(result)
            
            # Sort by similarity score
            results.sort(key=lambda x: x["similarity_score"], reverse=True)
            
            return results[:limit]
            
        except ImportError:
            # Fallback to basic search if fuzzywuzzy not available
            print("FuzzyWuzzy not available, using basic search")
            return self._basic_search(search_term, system, limit)
        except Exception as e:
            print(f"Error in fuzzy search: {e}")
            return self._basic_search(search_term, system, limit)
    
    def _basic_search(self, search_term: str, system: Optional[str], limit: int) -> List[Dict[str, Any]]:
        """Fallback basic search"""
        codes = self.db_ops.search_terminology_codes(search_term, system, limit)
        
        results = []
        for code in codes:
            result = {
                "code": code.code,
                "display": code.display,
                "definition": code.definition,
                "system": code.system,
                "properties": json.loads(code.properties) if code.properties else {},
                "similarity_score": 1.0,  # Default score
                "search_method": "basic_search"
            }
            results.append(result)
        
        return results


class NLPSuggestionService:
    """NLP-based auto-suggestion service"""
    
    def __init__(self, db: Session):
        self.db = db
        self.db_ops = DatabaseOperations(db)
        
        # Common medical terms and their potential mappings
        self.medical_keywords = {
            "diabetes": ["prameha", "madhumeha", "diabetes", "blood sugar"],
            "fever": ["jwara", "fever", "temperature", "pyrexia"],
            "cough": ["kasa", "cough", "respiratory", "throat"],
            "headache": ["shirahshool", "headache", "cephalgia", "migraine"],
            "arthritis": ["sandhivata", "arthritis", "joint", "inflammation"],
            "liver": ["yakridvikara", "liver", "hepatic", "hepatitis"],
            "gastritis": ["amlapitta", "gastritis", "acidity", "stomach"],
            "diarrhea": ["atisara", "diarrhea", "loose motions", "bowel"]
        }
    
    def suggest_codes(
        self, 
        clinical_text: str, 
        target_system: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Suggest codes based on clinical text input"""
        
        try:
            # Normalize text
            normalized_text = clinical_text.lower().strip()
            
            suggestions = []
            
            # Keyword-based suggestions
            for condition, keywords in self.medical_keywords.items():
                for keyword in keywords:
                    if keyword in normalized_text:
                        # Search for related codes
                        codes = self.db_ops.search_terminology_codes(
                            search_term=keyword,
                            system=target_system,
                            limit=5
                        )
                        
                        for code in codes:
                            suggestion = {
                                "code": code.code,
                                "display": code.display,
                                "definition": code.definition,
                                "system": code.system,
                                "confidence": self._calculate_nlp_confidence(normalized_text, keyword),
                                "matched_keyword": keyword,
                                "suggestion_method": "keyword_match"
                            }
                            
                            # Avoid duplicates
                            if not any(s["code"] == suggestion["code"] for s in suggestions):
                                suggestions.append(suggestion)
            
            # Sort by confidence
            suggestions.sort(key=lambda x: x["confidence"], reverse=True)
            
            return suggestions[:limit]
            
        except Exception as e:
            print(f"Error in NLP suggestions: {e}")
            return []
    
    def _calculate_nlp_confidence(self, text: str, keyword: str) -> float:
        """Calculate confidence score for NLP match"""
        
        # Simple confidence calculation based on keyword presence and context
        base_score = 0.7
        
        # Boost if exact keyword match
        if keyword in text:
            base_score += 0.2
        
        # Boost if multiple related keywords
        keyword_count = sum(1 for kw in self.medical_keywords.get(keyword, []) if kw in text)
        base_score += min(keyword_count * 0.1, 0.1)
        
        return min(base_score, 1.0)


class ConsentManagementService:
    """Consent management for ABHA and data sharing compliance"""
    
    def __init__(self, db: Session):
        self.db = db
        self.db_ops = DatabaseOperations(db)
    
    def grant_consent(
        self,
        user_id: int,
        consent_type: str,
        duration_days: int = 365,
        details: Optional[Dict[str, Any]] = None
    ) -> ConsentRecord:
        """Grant consent for specific purpose"""
        
        try:
            # Check if consent already exists
            existing = self.db.query(ConsentRecord).filter(
                ConsentRecord.user_id == user_id,
                ConsentRecord.consent_type == consent_type,
                ConsentRecord.status == "granted"
            ).first()
            
            if existing:
                return existing
            
            # Create new consent record
            consent = ConsentRecord(
                user_id=user_id,
                consent_type=consent_type,
                status="granted",
                granted_at=datetime.utcnow(),
                expires_at=datetime.utcnow() + timedelta(days=duration_days),
                details=json.dumps(details) if details else None
            )
            
            self.db.add(consent)
            self.db.commit()
            self.db.refresh(consent)
            
            # Log consent event
            self.db_ops.log_audit_event(
                action="consent_granted",
                user_id=user_id,
                details={
                    "consent_type": consent_type,
                    "duration_days": duration_days,
                    "expires_at": consent.expires_at.isoformat()
                }
            )
            
            return consent
            
        except Exception as e:
            print(f"Error granting consent: {e}")
            raise
    
    def revoke_consent(self, user_id: int, consent_type: str) -> bool:
        """Revoke consent"""
        
        try:
            consent = self.db.query(ConsentRecord).filter(
                ConsentRecord.user_id == user_id,
                ConsentRecord.consent_type == consent_type,
                ConsentRecord.status == "granted"
            ).first()
            
            if not consent:
                return False
            
            consent.status = "revoked"
            consent.revoked_at = datetime.utcnow()
            
            self.db.commit()
            
            # Log consent revocation
            self.db_ops.log_audit_event(
                action="consent_revoked",
                user_id=user_id,
                details={
                    "consent_type": consent_type,
                    "revoked_at": consent.revoked_at.isoformat()
                }
            )
            
            return True
            
        except Exception as e:
            print(f"Error revoking consent: {e}")
            return False
    
    def check_consent(self, user_id: int, consent_type: str) -> bool:
        """Check if user has valid consent for specific purpose"""
        
        try:
            consent = self.db.query(ConsentRecord).filter(
                ConsentRecord.user_id == user_id,
                ConsentRecord.consent_type == consent_type,
                ConsentRecord.status == "granted",
                ConsentRecord.expires_at > datetime.utcnow()
            ).first()
            
            return consent is not None
            
        except Exception as e:
            print(f"Error checking consent: {e}")
            return False
    
    def get_user_consents(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all consents for a user"""
        
        try:
            consents = self.db.query(ConsentRecord).filter(
                ConsentRecord.user_id == user_id
            ).order_by(ConsentRecord.granted_at.desc()).all()
            
            results = []
            for consent in consents:
                result = {
                    "id": consent.id,
                    "consent_type": consent.consent_type,
                    "status": consent.status,
                    "granted_at": consent.granted_at.isoformat(),
                    "expires_at": consent.expires_at.isoformat() if consent.expires_at else None,
                    "revoked_at": consent.revoked_at.isoformat() if consent.revoked_at else None,
                    "is_active": (consent.status == "granted" and 
                                (not consent.expires_at or consent.expires_at > datetime.utcnow())),
                    "details": json.loads(consent.details) if consent.details else {}
                }
                results.append(result)
            
            return results
            
        except Exception as e:
            print(f"Error getting user consents: {e}")
            return []


class ErrorHandlingService:
    """Comprehensive error handling and validation service"""
    
    @staticmethod
    def validate_terminology_system(system_uri: str) -> bool:
        """Validate terminology system URI"""
        valid_systems = [
            TerminologySystem.NAMASTE,
            TerminologySystem.ICD11_TM2,
            TerminologySystem.SNOMED_CT,
            TerminologySystem.LOINC
        ]
        return system_uri in valid_systems
    
    @staticmethod
    def validate_code_format(code: str, system: str) -> Tuple[bool, Optional[str]]:
        """Validate code format for specific systems"""
        
        if system == TerminologySystem.NAMASTE:
            # NAMASTE codes should follow pattern: [A-Z]+[0-9]+
            if not re.match(r'^[A-Z]+[0-9]+$', code):
                return False, "NAMASTE codes should be uppercase letters followed by numbers (e.g., PRAM001)"
        
        elif system == TerminologySystem.ICD11_TM2:
            # ICD-11 TM2 codes should follow pattern: TM-[A-Z][0-9]+
            if not re.match(r'^TM-[A-Z][0-9]+$', code):
                return False, "ICD-11 TM2 codes should follow format TM-X99 (e.g., TM-E11)"
        
        return True, None
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 500) -> str:
        """Sanitize user input"""
        if not text:
            return ""
        
        # Remove potentially dangerous characters
        sanitized = re.sub(r'[<>"\';(){}[\]]', '', str(text))
        
        # Limit length
        sanitized = sanitized[:max_length]
        
        # Trim whitespace
        sanitized = sanitized.strip()
        
        return sanitized
    
    @staticmethod
    def validate_abha_id(abha_id: str) -> Tuple[bool, Optional[str]]:
        """Validate ABHA ID format"""
        
        # ABHA ID format: 14-XXXX-XXXX-XXXX
        pattern = r'^14-\d{4}-\d{4}-\d{4}$'
        
        if not re.match(pattern, abha_id):
            return False, "ABHA ID should be in format: 14-XXXX-XXXX-XXXX"
        
        return True, None
    
    @staticmethod
    def handle_api_error(error: Exception) -> Dict[str, Any]:
        """Standardize API error responses"""
        
        error_type = type(error).__name__
        error_message = str(error)
        
        # Map common errors to user-friendly messages
        if "database" in error_message.lower():
            user_message = "Database operation failed. Please try again later."
        elif "network" in error_message.lower() or "connection" in error_message.lower():
            user_message = "Network connection failed. Please check your internet connection."
        elif "permission" in error_message.lower() or "unauthorized" in error_message.lower():
            user_message = "Access denied. Please check your permissions."
        elif "validation" in error_message.lower():
            user_message = "Data validation failed. Please check your input."
        else:
            user_message = "An unexpected error occurred. Please try again."
        
        return {
            "error": True,
            "error_type": error_type,
            "message": user_message,
            "technical_details": error_message,
            "timestamp": datetime.now().isoformat(),
            "support_info": "If this problem persists, please contact support with the error details."
        }


class CacheService:
    """Simple in-memory caching for frequently accessed data"""
    
    def __init__(self):
        self._cache = {}
        self._cache_timestamps = {}
        self.default_ttl = 300  # 5 minutes
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        
        if key not in self._cache:
            return None
        
        # Check if expired
        if key in self._cache_timestamps:
            if datetime.now() > self._cache_timestamps[key]:
                del self._cache[key]
                del self._cache_timestamps[key]
                return None
        
        return self._cache[key]
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value"""
        
        self._cache[key] = value
        
        if ttl is None:
            ttl = self.default_ttl
        
        self._cache_timestamps[key] = datetime.now() + timedelta(seconds=ttl)
    
    def delete(self, key: str) -> None:
        """Delete cached value"""
        
        if key in self._cache:
            del self._cache[key]
        
        if key in self._cache_timestamps:
            del self._cache_timestamps[key]
    
    def clear(self) -> None:
        """Clear all cached values"""
        
        self._cache.clear()
        self._cache_timestamps.clear()
    
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        
        active_keys = 0
        expired_keys = 0
        
        for key in self._cache.keys():
            if key in self._cache_timestamps:
                if datetime.now() <= self._cache_timestamps[key]:
                    active_keys += 1
                else:
                    expired_keys += 1
            else:
                active_keys += 1
        
        return {
            "total_keys": len(self._cache),
            "active_keys": active_keys,
            "expired_keys": expired_keys,
            "cache_hit_potential": active_keys / max(len(self._cache), 1)
        }


class AdvancedSearchService:
    """Advanced search combining multiple techniques"""
    
    def __init__(self, db: Session):
        self.db = db
        self.fuzzy_service = FuzzySearchService(db)
        self.nlp_service = NLPSuggestionService(db)
        self.cache_service = CacheService()
        self.error_handler = ErrorHandlingService()
    
    def comprehensive_search(
        self,
        search_term: str,
        system: Optional[str] = None,
        include_suggestions: bool = True,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Perform comprehensive search with multiple techniques"""
        
        try:
            # Sanitize input
            clean_search_term = self.error_handler.sanitize_input(search_term)
            
            if not clean_search_term:
                return {
                    "results": [],
                    "suggestions": [],
                    "message": "Please enter a valid search term"
                }
            
            # Check cache first
            cache_key = f"search:{system}:{clean_search_term}:{limit}"
            cached_result = self.cache_service.get(cache_key)
            if cached_result:
                cached_result["cached"] = True
                return cached_result
            
            # Perform fuzzy search
            fuzzy_results = self.fuzzy_service.fuzzy_search_codes(
                clean_search_term, system, threshold=0.6, limit=limit
            )
            
            # Get NLP suggestions if enabled
            suggestions = []
            if include_suggestions:
                suggestions = self.nlp_service.suggest_codes(
                    clean_search_term, system, limit=10
                )
            
            # Combine results
            result = {
                "search_term": clean_search_term,
                "system_filter": system,
                "results": fuzzy_results,
                "suggestions": suggestions,
                "total_results": len(fuzzy_results),
                "search_techniques": ["fuzzy_match"],
                "cached": False,
                "timestamp": datetime.now().isoformat()
            }
            
            if include_suggestions:
                result["search_techniques"].append("nlp_suggestions")
            
            # Cache result
            self.cache_service.set(cache_key, result, ttl=300)
            
            return result
            
        except Exception as e:
            return self.error_handler.handle_api_error(e)


class DataQualityService:
    """Data quality assessment and improvement service"""
    
    def __init__(self, db: Session):
        self.db = db
        self.db_ops = DatabaseOperations(db)
    
    def assess_code_quality(self, system: str) -> Dict[str, Any]:
        """Assess quality of codes in a terminology system"""
        
        try:
            codes = self.db.query(TerminologyCode).filter(
                TerminologyCode.system == system
            ).all()
            
            if not codes:
                return {
                    "system": system,
                    "total_codes": 0,
                    "quality_score": 0,
                    "issues": ["No codes found in system"]
                }
            
            # Quality metrics
            total_codes = len(codes)
            codes_with_display = sum(1 for c in codes if c.display and c.display.strip())
            codes_with_definition = sum(1 for c in codes if c.definition and c.definition.strip())
            codes_with_properties = sum(1 for c in codes if c.properties)
            
            # Calculate quality score
            display_score = codes_with_display / total_codes
            definition_score = codes_with_definition / total_codes
            properties_score = codes_with_properties / total_codes
            
            overall_quality = (display_score * 0.5 + definition_score * 0.3 + properties_score * 0.2)
            
            # Identify issues
            issues = []
            if display_score < 0.9:
                issues.append(f"{total_codes - codes_with_display} codes missing display names")
            
            if definition_score < 0.7:
                issues.append(f"{total_codes - codes_with_definition} codes missing definitions")
            
            if properties_score < 0.5:
                issues.append(f"{total_codes - codes_with_properties} codes missing additional properties")
            
            return {
                "system": system,
                "total_codes": total_codes,
                "quality_score": round(overall_quality, 2),
                "metrics": {
                    "display_coverage": round(display_score, 2),
                    "definition_coverage": round(definition_score, 2),
                    "properties_coverage": round(properties_score, 2)
                },
                "issues": issues,
                "assessment_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            return self.error_handler.handle_api_error(e)
    
    def assess_mapping_quality(self) -> Dict[str, Any]:
        """Assess quality of code mappings"""
        
        try:
            from .database import CodeMapping
            
            mappings = self.db.query(CodeMapping).all()
            
            if not mappings:
                return {
                    "total_mappings": 0,
                    "quality_score": 0,
                    "issues": ["No mappings found"]
                }
            
            # Quality metrics
            total_mappings = len(mappings)
            high_confidence = sum(1 for m in mappings if m.confidence >= 0.8)
            verified_mappings = sum(1 for m in mappings if m.verified_at is not None)
            
            # Calculate quality score
            confidence_score = high_confidence / total_mappings
            verification_score = verified_mappings / total_mappings
            
            overall_quality = (confidence_score * 0.6 + verification_score * 0.4)
            
            # Identify issues
            issues = []
            if confidence_score < 0.7:
                issues.append(f"{total_mappings - high_confidence} mappings have low confidence (<80%)")
            
            if verification_score < 0.5:
                issues.append(f"{total_mappings - verified_mappings} mappings are unverified")
            
            return {
                "total_mappings": total_mappings,
                "quality_score": round(overall_quality, 2),
                "metrics": {
                    "high_confidence_percentage": round(confidence_score * 100, 1),
                    "verified_percentage": round(verification_score * 100, 1)
                },
                "issues": issues,
                "assessment_date": datetime.now().isoformat()
            }
            
        except Exception as e:
            return self.error_handler.handle_api_error(e)


class ConfigurationService:
    """Service for managing application configuration"""
    
    def __init__(self):
        self.config = self._load_default_config()
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration"""
        
        return {
            "search": {
                "fuzzy_threshold": 0.6,
                "max_results": 50,
                "enable_caching": True,
                "cache_ttl_seconds": 300
            },
            "nlp": {
                "enable_suggestions": True,
                "min_confidence": 0.5,
                "max_suggestions": 10
            },
            "consent": {
                "default_duration_days": 365,
                "require_explicit_consent": True,
                "consent_types": [
                    "data_sharing",
                    "analytics",
                    "mapping_creation",
                    "research_participation"
                ]
            },
            "security": {
                "require_abha_verification": False,
                "max_login_attempts": 5,
                "session_timeout_minutes": 30
            },
            "api": {
                "rate_limit_requests_per_minute": 100,
                "max_upload_size_mb": 10,
                "allowed_file_types": [".csv", ".xlsx", ".json"]
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        
        keys = key.split('.')
        value = self.config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def update(self, key: str, value: Any) -> None:
        """Update configuration value"""
        
        keys = key.split('.')
        config = self.config
        
        # Navigate to the parent dictionary
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value


# Global instances
cache_service = CacheService()
config_service = ConfigurationService()


def get_advanced_search_service(db: Session) -> AdvancedSearchService:
    """Get advanced search service instance"""
    return AdvancedSearchService(db)


def get_consent_service(db: Session) -> ConsentManagementService:
    """Get consent management service instance"""
    return ConsentManagementService(db)


def get_data_quality_service(db: Session) -> DataQualityService:
    """Get data quality service instance"""
    return DataQualityService(db)
