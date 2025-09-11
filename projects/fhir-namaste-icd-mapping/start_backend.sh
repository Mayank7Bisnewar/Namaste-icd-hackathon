#!/bin/bash
echo "Starting FHIR NAMASTE-ICD Backend API..."
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
