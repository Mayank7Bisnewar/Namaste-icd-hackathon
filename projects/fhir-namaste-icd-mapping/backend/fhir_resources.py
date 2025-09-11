"""
FHIR R4 Resource Models and Utilities

This module provides FHIR-compliant resource models for healthcare terminology
mapping between NAMASTE and ICD-11 TM2 systems.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from enum import Enum
import uuid

from fhir.resources.codesystem import CodeSystem, CodeSystemConcept
from fhir.resources.conceptmap import ConceptMap, ConceptMapGroup, ConceptMapGroupElement, ConceptMapGroupElementTarget
from fhir.resources.patient import Patient
from fhir.resources.encounter import Encounter, EncounterDiagnosis
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.identifier import Identifier
from fhir.resources.humanname import HumanName
from fhir.resources.meta import Meta
from fhir.resources.narrative import Narrative
from fhir.resources.reference import Reference

from pydantic import BaseModel, Field


class TerminologySystem(str, Enum):
    """Supported terminology systems"""
    NAMASTE = "http://terminology.ayush.gov.in/namaste"
    ICD11_TM2 = "http://id.who.int/icd/release/11/tm2"
    SNOMED_CT = "http://snomed.info/sct"
    LOINC = "http://loinc.org"


class MappingEquivalence(str, Enum):
    """FHIR ConceptMap equivalence types"""
    RELATEDTO = "relatedto"
    EQUIVALENT = "equivalent"
    EQUAL = "equal"
    WIDER = "wider"
    SUBSUMES = "subsumes"
    NARROWER = "narrower"
    SPECIALIZES = "specializes"
    INEXACT = "inexact"
    UNMATCHED = "unmatched"
    DISJOINT = "disjoint"


class FHIRResourceBuilder:
    """Builder class for creating FHIR resources"""

    @staticmethod
    def create_codesystem(
        system_uri: str,
        name: str,
        title: str,
        description: str,
        concepts: List[Dict[str, Any]],
        version: str = "1.0.0"
    ) -> CodeSystem:
        """Create a FHIR CodeSystem resource"""
        
        # Create concepts
        fhir_concepts = []
        for concept in concepts:
            fhir_concept = CodeSystemConcept(
                code=concept["code"],
                display=concept.get("display", ""),
                definition=concept.get("definition", "")
            )
            
            # Add properties if available - simplified for now
            # Properties will be stored in extensions or custom fields
            
            fhir_concepts.append(fhir_concept)
        
        # Create CodeSystem
        codesystem = CodeSystem(
            id=str(uuid.uuid4()),
            url=system_uri,
            identifier=[
                Identifier(
                    system="urn:ietf:rfc:3986",
                    value=system_uri
                )
            ],
            version=version,
            name=name.replace(" ", ""),
            title=title,
            status="active",
            experimental=False,
            date=datetime.now().isoformat(),
            publisher="FHIR NAMASTE-ICD Mapping Service",
            description=description,
            content="complete",
            concept=fhir_concepts,
            meta=Meta(
                lastUpdated=datetime.now().isoformat(),
                versionId="1"
            )
        )
        
        return codesystem

    @staticmethod
    def create_conceptmap(
        source_system: str,
        target_system: str,
        mappings: List[Dict[str, Any]],
        name: str,
        title: str,
        description: str,
        version: str = "1.0.0"
    ) -> ConceptMap:
        """Create a FHIR ConceptMap resource"""
        
        # Group mappings by source system
        groups = {}
        
        for mapping in mappings:
            source_code = mapping["source_code"]
            target_code = mapping["target_code"]
            equivalence = mapping.get("equivalence", MappingEquivalence.EQUIVALENT)
            
            if source_system not in groups:
                groups[source_system] = {
                    "source": source_system,
                    "target": target_system,
                    "elements": []
                }
            
            # Create target mapping
            target = ConceptMapGroupElementTarget(
                code=target_code,
                display=mapping.get("target_display", ""),
                equivalence=equivalence
            )
            
            # Find or create element
            element_found = False
            for element in groups[source_system]["elements"]:
                if element.code == source_code:
                    element.target.append(target)
                    element_found = True
                    break
            
            if not element_found:
                element = ConceptMapGroupElement(
                    code=source_code,
                    display=mapping.get("source_display", ""),
                    target=[target]
                )
                groups[source_system]["elements"].append(element)
        
        # Convert to FHIR groups
        fhir_groups = []
        for group_data in groups.values():
            group = ConceptMapGroup(
                source=group_data["source"],
                target=group_data["target"],
                element=group_data["elements"]
            )
            fhir_groups.append(group)
        
        # Create ConceptMap
        conceptmap = ConceptMap(
            id=str(uuid.uuid4()),
            url=f"http://fhir.namaste-icd.org/ConceptMap/{name.lower()}",
            identifier=[
                Identifier(
                    system="urn:ietf:rfc:3986",
                    value=f"urn:uuid:{uuid.uuid4()}"
                )
            ],
            version=version,
            name=name.replace(" ", ""),
            title=title,
            status="active",
            experimental=False,
            date=datetime.now().isoformat(),
            publisher="FHIR NAMASTE-ICD Mapping Service",
            description=description,
            sourceUri=source_system,
            targetUri=target_system,
            group=fhir_groups,
            meta=Meta(
                lastUpdated=datetime.now().isoformat(),
                versionId="1"
            )
        )
        
        return conceptmap

    @staticmethod
    def create_patient_with_abha(
        abha_id: str,
        given_name: str,
        family_name: str,
        gender: str = "unknown",
        birth_date: Optional[str] = None
    ) -> Patient:
        """Create a FHIR Patient resource with ABHA ID"""
        
        # Create ABHA identifier
        abha_identifier = Identifier(
            use="usual",
            type=CodeableConcept(
                coding=[
                    Coding(
                        system="http://terminology.hl7.org/CodeSystem/v2-0203",
                        code="NI",
                        display="National unique individual identifier"
                    )
                ],
                text="ABHA ID"
            ),
            system="https://healthid.ndhm.gov.in",
            value=abha_id
        )
        
        # Create human name
        name = HumanName(
            use="official",
            given=[given_name],
            family=family_name
        )
        
        # Create Patient
        patient = Patient(
            id=str(uuid.uuid4()),
            identifier=[abha_identifier],
            active=True,
            name=[name],
            gender=gender,
            meta=Meta(
                lastUpdated=datetime.now().isoformat(),
                versionId="1"
            )
        )
        
        if birth_date:
            patient.birthDate = birth_date
        
        return patient

    @staticmethod
    def create_encounter_with_diagnosis(
        patient_id: str,
        diagnosis_codes: List[Dict[str, str]],
        encounter_class: str = "AMB",
        status: str = "finished"
    ) -> Encounter:
        """Create a FHIR Encounter with dual-coded diagnoses"""
        
        # Create diagnoses
        diagnoses = []
        for i, diagnosis in enumerate(diagnosis_codes):
            # Create coding for the diagnosis
            codings = []
            
            if "namaste_code" in diagnosis:
                namaste_coding = Coding(
                    system=TerminologySystem.NAMASTE,
                    code=diagnosis["namaste_code"],
                    display=diagnosis.get("namaste_display", "")
                )
                codings.append(namaste_coding)
            
            if "icd_code" in diagnosis:
                icd_coding = Coding(
                    system=TerminologySystem.ICD11_TM2,
                    code=diagnosis["icd_code"],
                    display=diagnosis.get("icd_display", "")
                )
                codings.append(icd_coding)
            
            # Create CodeableConcept
            condition = CodeableConcept(
                coding=codings,
                text=diagnosis.get("text", "")
            )
            
            # Create diagnosis
            encounter_diagnosis = EncounterDiagnosis(
                condition=Reference(
                    display=diagnosis.get("text", "")
                ),
                use=CodeableConcept(
                    coding=[
                        Coding(
                            system="http://terminology.hl7.org/CodeSystem/diagnosis-role",
                            code="AD",
                            display="Admission diagnosis"
                        )
                    ]
                ),
                rank=i + 1
            )
            diagnoses.append(encounter_diagnosis)
        
        # Create Encounter
        encounter = Encounter(
            id=str(uuid.uuid4()),
            status=status,  # Use string directly
            class_=Coding(
                system="http://terminology.hl7.org/CodeSystem/v3-ActCode",
                code=encounter_class,
                display="ambulatory" if encounter_class == "AMB" else "inpatient encounter"
            ),
            subject=Reference(reference=f"Patient/{patient_id}"),
            diagnosis=diagnoses if diagnoses else None,
            meta=Meta(
                lastUpdated=datetime.now().isoformat(),
                versionId="1"
            )
        )
        
        return encounter


class SearchResult(BaseModel):
    """Search result model for terminology searches"""
    code: str = Field(..., description="The terminology code")
    display: str = Field(..., description="Display name for the code")
    system: TerminologySystem = Field(..., description="Terminology system URI")
    definition: Optional[str] = Field(None, description="Definition of the code")
    properties: Optional[Dict[str, Any]] = Field(None, description="Additional properties")


class TranslationResult(BaseModel):
    """Translation result model for code mapping"""
    source_code: str = Field(..., description="Source terminology code")
    source_system: TerminologySystem = Field(..., description="Source terminology system")
    target_code: str = Field(..., description="Target terminology code")
    target_system: TerminologySystem = Field(..., description="Target terminology system")
    equivalence: MappingEquivalence = Field(..., description="Mapping equivalence")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Mapping confidence score")


class AuditLogEntry(BaseModel):
    """Audit log entry for tracking system operations"""
    timestamp: datetime = Field(default_factory=datetime.now)
    user_id: Optional[str] = Field(None, description="User identifier")
    abha_id: Optional[str] = Field(None, description="ABHA ID if applicable")
    action: str = Field(..., description="Action performed")
    resource_type: str = Field(..., description="FHIR resource type")
    resource_id: Optional[str] = Field(None, description="Resource ID")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")


def create_narrative(content: str, status: str = "generated") -> Narrative:
    """Create a FHIR Narrative"""
    return Narrative(
        status=status,
        div=f'<div xmlns="http://www.w3.org/1999/xhtml">{content}</div>'
    )


def validate_fhir_resource(resource: Any) -> bool:
    """Validate a FHIR resource"""
    try:
        # Use the resource's validation method
        resource.dict()
        return True
    except Exception as e:
        print(f"Validation error: {e}")
        return False
