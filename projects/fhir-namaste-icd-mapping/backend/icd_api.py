"""
ICD-11 API Integration

This module provides integration with the WHO ICD-11 API to fetch
Traditional Medicine 2 (TM2) codes and create mappings.
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
import httpx
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .database import DatabaseOperations, TerminologyCode
from .fhir_resources import TerminologySystem, FHIRResourceBuilder


class ICDAPIClient:
    """Client for WHO ICD-11 API"""
    
    def __init__(self):
        self.base_url = os.getenv("ICD_API_BASE_URL", "https://id.who.int/icd")
        self.client_id = os.getenv("ICD_CLIENT_ID", "mock_client_id")
        self.client_secret = os.getenv("ICD_CLIENT_SECRET", "mock_client_secret")
        self.token_url = os.getenv("ICD_TOKEN_URL", "https://icdaccessmanagement.who.int/connect/token")
        
        self._access_token = None
        self._token_expires = None
        
        # Mock TM2 data for demonstration
        self.mock_tm2_data = {
            "TM-E11": {
                "code": "TM-E11",
                "display": "Diabetes mellitus",
                "definition": "A group of metabolic diseases characterized by high blood sugar levels",
                "category": "Endocrine, nutritional and metabolic diseases",
                "parent": "TM-E10-E14"
            },
            "TM-R50": {
                "code": "TM-R50",
                "display": "Fever, unspecified", 
                "definition": "Elevation of body temperature above normal range",
                "category": "Symptoms, signs and abnormal clinical findings",
                "parent": "TM-R50-R69"
            },
            "TM-R05": {
                "code": "TM-R05",
                "display": "Cough",
                "definition": "A sudden, forceful expulsion of air from the lungs",
                "category": "Symptoms, signs and abnormal clinical findings",
                "parent": "TM-R00-R09"
            },
            "TM-K59": {
                "code": "TM-K59",
                "display": "Other functional intestinal disorders",
                "definition": "Functional disorders of the intestine not elsewhere classified",
                "category": "Diseases of the digestive system",
                "parent": "TM-K55-K63"
            },
            "TM-G43": {
                "code": "TM-G43",
                "display": "Migraine",
                "definition": "A neurological condition characterized by recurrent headaches",
                "category": "Diseases of the nervous system",
                "parent": "TM-G43-G47"
            },
            "TM-I25": {
                "code": "TM-I25",
                "display": "Chronic ischaemic heart disease",
                "definition": "Long-term condition affecting blood supply to the heart",
                "category": "Diseases of the circulatory system",
                "parent": "TM-I20-I25"
            },
            "TM-E10": {
                "code": "TM-E10",
                "display": "Type 1 diabetes mellitus",
                "definition": "Diabetes mellitus due to autoimmune pancreatic islet beta-cell destruction",
                "category": "Endocrine, nutritional and metabolic diseases",
                "parent": "TM-E10-E14"
            },
            "TM-K21": {
                "code": "TM-K21",
                "display": "Gastro-oesophageal reflux disease",
                "definition": "A digestive disorder affecting the ring of muscle between esophagus and stomach",
                "category": "Diseases of the digestive system",
                "parent": "TM-K20-K31"
            },
            "TM-M15": {
                "code": "TM-M15",
                "display": "Polyarthrosis",
                "definition": "Arthritis affecting multiple joints",
                "category": "Diseases of the musculoskeletal system",
                "parent": "TM-M15-M19"
            },
            "TM-K70": {
                "code": "TM-K70",
                "display": "Alcoholic liver disease",
                "definition": "Liver damage caused by alcohol consumption",
                "category": "Diseases of the digestive system",
                "parent": "TM-K70-K77"
            }
        }
    
    async def get_access_token(self) -> str:
        """Get OAuth 2.0 access token for ICD API"""
        
        # Check if token is still valid
        if (self._access_token and 
            self._token_expires and 
            datetime.now() < self._token_expires):
            return self._access_token
        
        # For mock implementation, return a mock token
        self._access_token = f"mock_icd_token_{datetime.now().timestamp()}"
        self._token_expires = datetime.now() + timedelta(hours=1)
        
        return self._access_token
    
    async def search_tm2_codes(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Search ICD-11 TM2 codes"""
        
        try:
            # Mock implementation - search in mock data
            results = []
            query_lower = query.lower()
            
            for code_data in self.mock_tm2_data.values():
                if (query_lower in code_data["display"].lower() or
                    query_lower in code_data["definition"].lower() or
                    query_lower in code_data["code"].lower()):
                    
                    results.append({
                        "code": code_data["code"],
                        "display": code_data["display"],
                        "definition": code_data["definition"],
                        "system": TerminologySystem.ICD11_TM2,
                        "properties": {
                            "category": code_data["category"],
                            "parent": code_data["parent"]
                        }
                    })
                    
                    if len(results) >= limit:
                        break
            
            return results
            
        except Exception as e:
            print(f"Error searching ICD-11 TM2 codes: {e}")
            return []
    
    async def get_tm2_code(self, code: str) -> Optional[Dict[str, Any]]:
        """Get specific ICD-11 TM2 code"""
        
        try:
            # Mock implementation
            if code in self.mock_tm2_data:
                code_data = self.mock_tm2_data[code]
                return {
                    "code": code_data["code"],
                    "display": code_data["display"],
                    "definition": code_data["definition"],
                    "system": TerminologySystem.ICD11_TM2,
                    "properties": {
                        "category": code_data["category"],
                        "parent": code_data["parent"]
                    }
                }
            
            return None
            
        except Exception as e:
            print(f"Error getting ICD-11 TM2 code {code}: {e}")
            return None
    
    async def get_linearization_codes(self, entity_id: str) -> List[Dict[str, Any]]:
        """Get linearization codes for an entity"""
        
        # Mock implementation for TM2 linearization
        try:
            # In real implementation, this would call:
            # GET {base_url}/release/11/tm2/{entity_id}/linearization
            
            return [
                {
                    "code": f"TM-{entity_id}",
                    "display": f"Traditional Medicine Code {entity_id}",
                    "linearizationName": "TM2",
                    "isIncludedInLinearization": True
                }
            ]
            
        except Exception as e:
            print(f"Error getting linearization codes: {e}")
            return []


class ICDDataService:
    """Service for managing ICD-11 data and operations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.db_ops = DatabaseOperations(db)
        self.api_client = ICDAPIClient()
        self.system_uri = TerminologySystem.ICD11_TM2
    
    async def sync_tm2_codes(self, search_terms: Optional[List[str]] = None) -> Dict[str, Any]:
        """Synchronize ICD-11 TM2 codes with local database"""
        
        try:
            synced_codes = []
            
            if search_terms:
                # Sync specific terms
                for term in search_terms:
                    codes = await self.api_client.search_tm2_codes(term, limit=100)
                    for code_data in codes:
                        terminology_code = self.db_ops.create_terminology_code(
                            system=self.system_uri,
                            code=code_data["code"],
                            display=code_data["display"],
                            definition=code_data["definition"],
                            properties=code_data.get("properties", {})
                        )
                        synced_codes.append(terminology_code)
            else:
                # Sync all mock TM2 codes
                for code_data in self.api_client.mock_tm2_data.values():
                    terminology_code = self.db_ops.create_terminology_code(
                        system=self.system_uri,
                        code=code_data["code"],
                        display=code_data["display"],
                        definition=code_data["definition"],
                        properties={
                            "category": code_data["category"],
                            "parent": code_data["parent"]
                        }
                    )
                    synced_codes.append(terminology_code)
            
            return {
                "success": True,
                "message": f"Successfully synced {len(synced_codes)} ICD-11 TM2 codes",
                "codes_synced": len(synced_codes),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error syncing ICD-11 TM2 codes: {str(e)}",
                "error": str(e)
            }
    
    async def search_codes(
        self, 
        search_term: str, 
        limit: int = 50,
        use_api: bool = True
    ) -> List[Dict[str, Any]]:
        """Search ICD-11 TM2 codes"""
        
        results = []
        
        try:
            if use_api:
                # Search via API first
                api_results = await self.api_client.search_tm2_codes(search_term, limit)
                results.extend(api_results)
            
            # Also search local database
            local_codes = self.db_ops.search_terminology_codes(
                search_term=search_term,
                system=self.system_uri,
                limit=limit
            )
            
            for code in local_codes:
                # Avoid duplicates
                if not any(r["code"] == code.code for r in results):
                    result = {
                        "code": code.code,
                        "display": code.display,
                        "definition": code.definition,
                        "system": code.system,
                        "properties": code.properties or {}
                    }
                    results.append(result)
            
            return results[:limit]
            
        except Exception as e:
            print(f"Error searching ICD-11 TM2 codes: {e}")
            return []
    
    def create_fhir_codesystem(self) -> str:
        """Create FHIR CodeSystem for ICD-11 TM2 codes"""
        
        try:
            # Get all TM2 codes from database
            codes = self.db.query(TerminologyCode).filter(
                TerminologyCode.system == TerminologySystem.ICD11_TM2
            ).all()
            
            # Convert to FHIR concepts
            fhir_concepts = []
            for code in codes:
                concept = {
                    "code": code.code,
                    "display": code.display,
                    "definition": code.definition,
                    "properties": code.properties or {}
                }
                fhir_concepts.append(concept)
            
            # Create FHIR CodeSystem
            codesystem = FHIRResourceBuilder.create_codesystem(
                system_uri=self.system_uri,
                name="ICD11TM2",
                title="ICD-11 Traditional Medicine 2",
                description="WHO ICD-11 Traditional Medicine 2 codes",
                concepts=fhir_concepts,
                version="1.0.0"
            )
            
            # Store in database
            self.db_ops.store_fhir_resource(
                resource_id=codesystem.id,
                resource_type="CodeSystem",
                content=codesystem.json()
            )
            
            return codesystem.json()
            
        except Exception as e:
            print(f"Error creating ICD-11 TM2 CodeSystem: {e}")
            raise


class MappingService:
    """Service for creating and managing code mappings"""
    
    def __init__(self, db: Session):
        self.db = db
        self.db_ops = DatabaseOperations(db)
    
    async def create_automatic_mappings(
        self,
        source_system: str,
        target_system: str,
        mapping_algorithm: str = "fuzzy_match"
    ) -> Dict[str, Any]:
        """Create automatic mappings between terminology systems"""
        
        try:
            from fuzzywuzzy import fuzz, process
            
            # Get source codes
            source_codes = self.db.query(TerminologyCode).filter(
                TerminologyCode.system == source_system
            ).all()
            
            # Get target codes
            target_codes = self.db.query(TerminologyCode).filter(
                TerminologyCode.system == target_system
            ).all()
            
            # Create mapping choices for fuzzy matching
            target_choices = {
                f"{code.display} {code.definition}": code
                for code in target_codes
                if code.display
            }
            
            mappings_created = []
            
            for source_code in source_codes:
                try:
                    # Create search string
                    search_string = f"{source_code.display} {source_code.definition or ''}"
                    
                    # Find best match
                    best_match = process.extractOne(
                        search_string,
                        target_choices.keys(),
                        scorer=fuzz.token_sort_ratio
                    )
                    
                    if best_match and best_match[1] >= 70:  # 70% similarity threshold
                        target_code = target_choices[best_match[0]]
                        confidence = best_match[1] / 100.0
                        
                        # Determine equivalence based on confidence
                        if confidence >= 0.9:
                            equivalence = "equivalent"
                        elif confidence >= 0.8:
                            equivalence = "relatedto"
                        else:
                            equivalence = "inexact"
                        
                        # Create mapping
                        mapping = self.db_ops.create_code_mapping(
                            source_code_id=source_code.id,
                            target_code_id=target_code.id,
                            equivalence=equivalence,
                            confidence=confidence,
                            mapping_method=mapping_algorithm
                        )
                        
                        mappings_created.append({
                            "source_code": source_code.code,
                            "source_display": source_code.display,
                            "target_code": target_code.code,
                            "target_display": target_code.display,
                            "equivalence": equivalence,
                            "confidence": confidence
                        })
                
                except Exception as e:
                    print(f"Error mapping code {source_code.code}: {e}")
                    continue
            
            return {
                "success": True,
                "message": f"Created {len(mappings_created)} automatic mappings",
                "mappings_created": len(mappings_created),
                "mappings": mappings_created[:10],  # Return first 10 for preview
                "total_source_codes": len(source_codes),
                "total_target_codes": len(target_codes)
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error creating automatic mappings: {str(e)}",
                "error": str(e)
            }
    
    def translate_code(
        self,
        source_code: str,
        source_system: str,
        target_system: str
    ) -> Optional[Dict[str, Any]]:
        """Translate a code from source to target system"""
        
        try:
            # Find source code
            source_terminology_code = self.db.query(TerminologyCode).filter(
                TerminologyCode.system == source_system,
                TerminologyCode.code == source_code
            ).first()
            
            if not source_terminology_code:
                return None
            
            # Find mapping
            from .database import CodeMapping
            mapping = self.db.query(CodeMapping).join(
                TerminologyCode, CodeMapping.source_code_id == TerminologyCode.id
            ).filter(
                TerminologyCode.system == source_system,
                TerminologyCode.code == source_code
            ).first()
            
            if not mapping:
                return None
            
            # Get target code
            target_code = mapping.target_code
            
            return {
                "source_code": source_code,
                "source_system": source_system,
                "source_display": source_terminology_code.display,
                "target_code": target_code.code,
                "target_system": target_code.system,
                "target_display": target_code.display,
                "equivalence": mapping.equivalence,
                "confidence": mapping.confidence,
                "mapping_method": mapping.mapping_method
            }
            
        except Exception as e:
            print(f"Error translating code {source_code}: {e}")
            return None
    
    def create_fhir_conceptmap(
        self,
        source_system: str,
        target_system: str,
        name: str = None
    ) -> str:
        """Create FHIR ConceptMap from stored mappings"""
        
        try:
            from .database import CodeMapping
            
            # Get all mappings between systems
            mappings = self.db.query(CodeMapping).join(
                TerminologyCode, CodeMapping.source_code_id == TerminologyCode.id
            ).join(
                TerminologyCode, CodeMapping.target_code_id == TerminologyCode.id,
                aliased=True
            ).filter(
                TerminologyCode.system == source_system
            ).all()
            
            # Convert to mapping format
            mapping_data = []
            for mapping in mappings:
                mapping_data.append({
                    "source_code": mapping.source_code.code,
                    "source_display": mapping.source_code.display,
                    "target_code": mapping.target_code.code,
                    "target_display": mapping.target_code.display,
                    "equivalence": mapping.equivalence
                })
            
            # Create FHIR ConceptMap
            if not name:
                name = f"Mapping-{source_system.split('/')[-1]}-to-{target_system.split('/')[-1]}"
            
            conceptmap = FHIRResourceBuilder.create_conceptmap(
                source_system=source_system,
                target_system=target_system,
                mappings=mapping_data,
                name=name,
                title=f"Code mappings from {source_system} to {target_system}",
                description=f"Terminology mappings between {source_system} and {target_system}"
            )
            
            # Store in database
            self.db_ops.store_fhir_resource(
                resource_id=conceptmap.id,
                resource_type="ConceptMap",
                content=conceptmap.json()
            )
            
            return conceptmap.json()
            
        except Exception as e:
            print(f"Error creating ConceptMap: {e}")
            raise
    
    def get_mapping_statistics(self) -> Dict[str, Any]:
        """Get mapping statistics"""
        
        try:
            from .database import CodeMapping
            
            # Count mappings by system pairs
            mappings = self.db.query(CodeMapping).join(
                TerminologyCode, CodeMapping.source_code_id == TerminologyCode.id
            ).join(
                TerminologyCode, CodeMapping.target_code_id == TerminologyCode.id,
                aliased=True
            ).all()
            
            system_pairs = {}
            confidence_distribution = {"high": 0, "medium": 0, "low": 0}
            method_distribution = {}
            
            for mapping in mappings:
                # System pairs
                source_system = mapping.source_code.system
                target_system = mapping.target_code.system
                pair = f"{source_system} -> {target_system}"
                
                system_pairs[pair] = system_pairs.get(pair, 0) + 1
                
                # Confidence distribution
                if mapping.confidence >= 0.8:
                    confidence_distribution["high"] += 1
                elif mapping.confidence >= 0.6:
                    confidence_distribution["medium"] += 1
                else:
                    confidence_distribution["low"] += 1
                
                # Method distribution
                method = mapping.mapping_method or "unknown"
                method_distribution[method] = method_distribution.get(method, 0) + 1
            
            return {
                "total_mappings": len(mappings),
                "system_pairs": system_pairs,
                "confidence_distribution": confidence_distribution,
                "method_distribution": method_distribution,
                "last_updated": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "total_mappings": 0
            }


# Utility functions
def create_sample_icd_data(db: Session):
    """Create sample ICD-11 TM2 data for testing"""
    
    service = ICDDataService(db)
    
    # Sync mock TM2 codes
    asyncio.run(service.sync_tm2_codes())
    
    print("Sample ICD-11 TM2 data created")


if __name__ == "__main__":
    from .database import SessionLocal
    
    db = SessionLocal()
    try:
        create_sample_icd_data(db)
    finally:
        db.close()
