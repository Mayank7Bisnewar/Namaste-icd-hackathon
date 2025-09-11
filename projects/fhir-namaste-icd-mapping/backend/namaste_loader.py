"""
NAMASTE Data Loader

This module provides functionality to load and process NAMASTE terminology
data from CSV files and other sources.
"""

import csv
import io
import os
from typing import List, Dict, Any, Optional
import pandas as pd
import requests
from sqlalchemy.orm import Session

from .database import DatabaseOperations, TerminologyCode
from .fhir_resources import TerminologySystem, FHIRResourceBuilder


class NAMASTELoader:
    """NAMASTE data loader and processor"""
    
    def __init__(self, db: Session):
        self.db = db
        self.db_ops = DatabaseOperations(db)
        self.system_uri = TerminologySystem.NAMASTE
    
    def load_from_csv(self, file_path: str, encoding: str = "utf-8") -> List[TerminologyCode]:
        """Load NAMASTE codes from CSV file"""
        
        loaded_codes = []
        
        try:
            # Read CSV file
            df = pd.read_csv(file_path, encoding=encoding)
            
            # Expected columns: code, display, definition, category, subcategory, system_name
            required_columns = ["code", "display"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Process each row
            for index, row in df.iterrows():
                try:
                    # Extract code information
                    code = str(row["code"]).strip()
                    display = str(row.get("display", "")).strip()
                    definition = str(row.get("definition", "")).strip()
                    
                    # Extract additional properties
                    properties = {}
                    for col in df.columns:
                        if col not in ["code", "display", "definition"]:
                            value = row.get(col)
                            if pd.notna(value):
                                properties[col] = str(value).strip()
                    
                    # Create terminology code
                    terminology_code = self.db_ops.create_terminology_code(
                        system=self.system_uri,
                        code=code,
                        display=display,
                        definition=definition,
                        properties=properties
                    )
                    
                    loaded_codes.append(terminology_code)
                    
                except Exception as e:
                    print(f"Error processing row {index}: {e}")
                    continue
            
            print(f"Successfully loaded {len(loaded_codes)} NAMASTE codes from CSV")
            return loaded_codes
            
        except Exception as e:
            print(f"Error loading NAMASTE CSV file: {e}")
            raise
    
    def load_from_content(self, csv_content: str) -> List[TerminologyCode]:
        """Load NAMASTE codes from CSV content string"""
        
        loaded_codes = []
        
        try:
            # Parse CSV content
            csv_reader = csv.DictReader(io.StringIO(csv_content))
            
            for row in csv_reader:
                try:
                    # Extract code information
                    code = row.get("code", "").strip()
                    display = row.get("display", "").strip()
                    definition = row.get("definition", "").strip()
                    
                    if not code:
                        continue
                    
                    # Extract additional properties
                    properties = {}
                    for key, value in row.items():
                        if key not in ["code", "display", "definition"] and value:
                            properties[key] = value.strip()
                    
                    # Create terminology code
                    terminology_code = self.db_ops.create_terminology_code(
                        system=self.system_uri,
                        code=code,
                        display=display,
                        definition=definition,
                        properties=properties
                    )
                    
                    loaded_codes.append(terminology_code)
                    
                except Exception as e:
                    print(f"Error processing CSV row: {e}")
                    continue
            
            print(f"Successfully loaded {len(loaded_codes)} NAMASTE codes from content")
            return loaded_codes
            
        except Exception as e:
            print(f"Error loading NAMASTE CSV content: {e}")
            raise
    
    def create_fhir_codesystem(self, codes: List[TerminologyCode]) -> str:
        """Create FHIR CodeSystem from NAMASTE codes"""
        
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
            name="NAMASTE",
            title="National Ayush Morbidity and Standardized Terminologies Electronic",
            description="NAMASTE codes for Ayush healthcare terminology",
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
    
    def search_codes(
        self, 
        search_term: str, 
        limit: int = 50,
        include_properties: bool = True
    ) -> List[Dict[str, Any]]:
        """Search NAMASTE codes"""
        
        codes = self.db_ops.search_terminology_codes(
            search_term=search_term,
            system=self.system_uri,
            limit=limit
        )
        
        results = []
        for code in codes:
            result = {
                "code": code.code,
                "display": code.display,
                "definition": code.definition,
                "system": code.system
            }
            
            if include_properties and code.properties:
                result["properties"] = code.properties
            
            results.append(result)
        
        return results
    
    def get_code_by_id(self, code: str) -> Optional[Dict[str, Any]]:
        """Get specific NAMASTE code by ID"""
        
        terminology_code = self.db.query(TerminologyCode).filter(
            TerminologyCode.system == self.system_uri,
            TerminologyCode.code == code
        ).first()
        
        if not terminology_code:
            return None
        
        return {
            "code": terminology_code.code,
            "display": terminology_code.display,
            "definition": terminology_code.definition,
            "system": terminology_code.system,
            "properties": terminology_code.properties or {}
        }
    
    def validate_csv_format(self, file_path: str) -> Dict[str, Any]:
        """Validate CSV file format"""
        
        validation_result = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "total_rows": 0,
            "valid_rows": 0,
            "columns": []
        }
        
        try:
            # Read CSV file
            df = pd.read_csv(file_path, nrows=1000)  # Sample first 1000 rows
            validation_result["columns"] = df.columns.tolist()
            validation_result["total_rows"] = len(df)
            
            # Check required columns
            required_columns = ["code", "display"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                validation_result["errors"].append(f"Missing required columns: {missing_columns}")
            
            # Validate data
            valid_rows = 0
            for index, row in df.iterrows():
                code = str(row.get("code", "")).strip()
                display = str(row.get("display", "")).strip()
                
                if code and display:
                    valid_rows += 1
                else:
                    if index < 10:  # Only show first 10 errors
                        validation_result["warnings"].append(f"Row {index}: Missing code or display")
            
            validation_result["valid_rows"] = valid_rows
            
            # Overall validation
            if not validation_result["errors"] and valid_rows > 0:
                validation_result["valid"] = True
            
        except Exception as e:
            validation_result["errors"].append(f"Error reading CSV file: {str(e)}")
        
        return validation_result


def create_sample_namaste_csv(file_path: str):
    """Create a sample NAMASTE CSV file for testing"""
    
    sample_data = [
        {
            "code": "PRAM001",
            "display": "Prameha",
            "definition": "A condition characterized by excessive urination and thirst",
            "category": "Metabolic Disorders",
            "subcategory": "Diabetes-related",
            "system_name": "Ayurveda",
            "severity": "Moderate"
        },
        {
            "code": "JWARA001",
            "display": "Jwara",
            "definition": "Fever or elevated body temperature",
            "category": "Infectious Diseases",
            "subcategory": "Fever",
            "system_name": "Ayurveda",
            "severity": "Mild"
        },
        {
            "code": "KASA001",
            "display": "Kasa",
            "definition": "Cough or respiratory condition",
            "category": "Respiratory Disorders",
            "subcategory": "Cough",
            "system_name": "Ayurveda",
            "severity": "Mild"
        },
        {
            "code": "ATISARA001",
            "display": "Atisara",
            "definition": "Loose motions or diarrhea",
            "category": "Gastrointestinal Disorders",
            "subcategory": "Diarrhea",
            "system_name": "Ayurveda",
            "severity": "Moderate"
        },
        {
            "code": "SHIRAHSHOOL001",
            "display": "Shirahshool",
            "definition": "Headache or cephalic pain",
            "category": "Neurological Disorders",
            "subcategory": "Headache",
            "system_name": "Ayurveda",
            "severity": "Mild"
        },
        {
            "code": "HRIDROGA001",
            "display": "Hridroga",
            "definition": "Heart disease or cardiac conditions",
            "category": "Cardiovascular Disorders",
            "subcategory": "Heart Disease",
            "system_name": "Ayurveda",
            "severity": "Severe"
        },
        {
            "code": "MADHUMEHA001",
            "display": "Madhumeha",
            "definition": "Diabetes mellitus in Ayurvedic terminology",
            "category": "Metabolic Disorders",
            "subcategory": "Diabetes",
            "system_name": "Ayurveda",
            "severity": "Severe"
        },
        {
            "code": "AMLAPITTA001",
            "display": "Amlapitta",
            "definition": "Hyperacidity or gastritis",
            "category": "Gastrointestinal Disorders",
            "subcategory": "Acidity",
            "system_name": "Ayurveda",
            "severity": "Mild"
        },
        {
            "code": "SANDHIVATA001",
            "display": "Sandhivata",
            "definition": "Joint disorders or arthritis",
            "category": "Musculoskeletal Disorders",
            "subcategory": "Arthritis",
            "system_name": "Ayurveda",
            "severity": "Moderate"
        },
        {
            "code": "YAKRIDVIKARA001",
            "display": "Yakridvikara",
            "definition": "Liver disorders or hepatic conditions",
            "category": "Hepatic Disorders",
            "subcategory": "Liver Disease",
            "system_name": "Ayurveda",
            "severity": "Severe"
        }
    ]
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Write CSV file
    df = pd.DataFrame(sample_data)
    df.to_csv(file_path, index=False, encoding='utf-8')
    
    print(f"Sample NAMASTE CSV file created at: {file_path}")


class NAMASTEDataService:
    """Service class for NAMASTE data operations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.loader = NAMASTELoader(db)
    
    def upload_csv_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Upload and process NAMASTE CSV file"""
        
        try:
            # Decode file content
            csv_content = file_content.decode('utf-8')
            
            # Validate content
            validation_result = self.validate_csv_content(csv_content)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "message": "CSV validation failed",
                    "errors": validation_result["errors"],
                    "warnings": validation_result.get("warnings", [])
                }
            
            # Load codes
            loaded_codes = self.loader.load_from_content(csv_content)
            
            # Create FHIR CodeSystem
            fhir_json = self.loader.create_fhir_codesystem(loaded_codes)
            
            return {
                "success": True,
                "message": f"Successfully loaded {len(loaded_codes)} codes",
                "codes_loaded": len(loaded_codes),
                "fhir_codesystem": fhir_json,
                "validation": validation_result
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Error processing CSV file: {str(e)}",
                "errors": [str(e)]
            }
    
    def validate_csv_content(self, csv_content: str) -> Dict[str, Any]:
        """Validate CSV content"""
        
        validation_result = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "total_rows": 0,
            "valid_rows": 0,
            "columns": []
        }
        
        try:
            # Parse CSV content
            df = pd.read_csv(io.StringIO(csv_content))
            validation_result["columns"] = df.columns.tolist()
            validation_result["total_rows"] = len(df)
            
            # Check required columns
            required_columns = ["code", "display"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                validation_result["errors"].append(f"Missing required columns: {missing_columns}")
            
            # Validate data
            valid_rows = 0
            duplicate_codes = set()
            
            for index, row in df.iterrows():
                code = str(row.get("code", "")).strip()
                display = str(row.get("display", "")).strip()
                
                # Check for valid code and display
                if code and display:
                    valid_rows += 1
                    
                    # Check for duplicates
                    if code in duplicate_codes:
                        validation_result["warnings"].append(f"Duplicate code found: {code}")
                    else:
                        duplicate_codes.add(code)
                else:
                    if len(validation_result["warnings"]) < 10:  # Only show first 10
                        validation_result["warnings"].append(f"Row {index + 1}: Missing code or display")
            
            validation_result["valid_rows"] = valid_rows
            
            # Overall validation
            if not validation_result["errors"] and valid_rows > 0:
                validation_result["valid"] = True
            
        except Exception as e:
            validation_result["errors"].append(f"Error parsing CSV content: {str(e)}")
        
        return validation_result
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get NAMASTE data statistics"""
        
        try:
            # Count total codes
            total_codes = self.db.query(TerminologyCode).filter(
                TerminologyCode.system == TerminologySystem.NAMASTE
            ).count()
            
            # Get categories from properties
            codes_with_props = self.db.query(TerminologyCode).filter(
                TerminologyCode.system == TerminologySystem.NAMASTE,
                TerminologyCode.properties.isnot(None)
            ).all()
            
            categories = set()
            systems = set()
            
            for code in codes_with_props:
                if code.properties:
                    if "category" in code.properties:
                        categories.add(code.properties["category"])
                    if "system_name" in code.properties:
                        systems.add(code.properties["system_name"])
            
            return {
                "total_codes": total_codes,
                "categories": list(categories),
                "systems": list(systems),
                "categories_count": len(categories),
                "systems_count": len(systems)
            }
            
        except Exception as e:
            return {
                "error": str(e),
                "total_codes": 0,
                "categories": [],
                "systems": []
            }


if __name__ == "__main__":
    # Create sample CSV for testing
    create_sample_namaste_csv("./data/sample_namaste.csv")
