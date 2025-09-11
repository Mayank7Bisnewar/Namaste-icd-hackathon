#!/usr/bin/env python3
"""
Project Initialization Script

Sets up the database, creates sample data, and prepares the application
for demonstration purposes.
"""

import os
import sys
import sqlite3
from pathlib import Path
import pandas as pd

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def create_database():
    """Create SQLite database and tables"""
    print("Creating database...")
    
    # Ensure data directory exists
    os.makedirs('./data', exist_ok=True)
    
    # Create database connection
    conn = sqlite3.connect('./data/fhir_mapping.db')
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            abha_id TEXT UNIQUE,
            full_name TEXT,
            hashed_password TEXT NOT NULL,
            is_active BOOLEAN DEFAULT 1,
            is_verified BOOLEAN DEFAULT 0,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # Create terminology_codes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS terminology_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            system TEXT NOT NULL,
            code TEXT NOT NULL,
            display TEXT,
            definition TEXT,
            properties TEXT,  -- JSON string
            version TEXT DEFAULT '1.0.0',
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(system, code)
        )
    ''')
    
    # Create code_mappings table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS code_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_code_id INTEGER NOT NULL,
            target_code_id INTEGER NOT NULL,
            equivalence TEXT DEFAULT 'equivalent',
            confidence REAL DEFAULT 1.0,
            mapping_method TEXT DEFAULT 'manual',
            mapped_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            verified_at TIMESTAMP,
            verified_by INTEGER,
            FOREIGN KEY (source_code_id) REFERENCES terminology_codes (id),
            FOREIGN KEY (target_code_id) REFERENCES terminology_codes (id),
            FOREIGN KEY (mapped_by) REFERENCES users (id),
            FOREIGN KEY (verified_by) REFERENCES users (id),
            UNIQUE(source_code_id, target_code_id)
        )
    ''')
    
    # Create fhir_resources table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fhir_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resource_id TEXT UNIQUE NOT NULL,
            resource_type TEXT NOT NULL,
            version_id TEXT DEFAULT '1',
            content TEXT NOT NULL,  -- JSON string
            meta_last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')
    
    # Create audit_logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER,
            abha_id TEXT,
            action TEXT NOT NULL,
            resource_type TEXT,
            resource_id TEXT,
            details TEXT,  -- JSON string
            ip_address TEXT,
            user_agent TEXT,
            success BOOLEAN DEFAULT 1,
            error_message TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create consent_records table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS consent_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            abha_id TEXT,
            consent_type TEXT NOT NULL,
            status TEXT DEFAULT 'granted',
            granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            revoked_at TIMESTAMP,
            details TEXT,  -- JSON string
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # Create search_history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            search_term TEXT NOT NULL,
            search_type TEXT,
            results_count INTEGER DEFAULT 0,
            execution_time_ms REAL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database created successfully!")


def create_admin_user():
    """Create default admin user"""
    print("Creating admin user...")
    
    conn = sqlite3.connect('./data/fhir_mapping.db')
    cursor = conn.cursor()
    
    # Check if admin exists
    cursor.execute("SELECT id FROM users WHERE username = ?", ("admin",))
    if cursor.fetchone():
        print("Admin user already exists")
        conn.close()
        return
    
    # Simple password hash for demo (in production, use proper bcrypt)
    import hashlib
    hashed_password = hashlib.sha256("admin123".encode()).hexdigest()
    
    # Insert admin user
    cursor.execute('''
        INSERT INTO users (username, email, full_name, hashed_password, role, is_active, is_verified)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', ("admin", "admin@example.com", "System Administrator", hashed_password, "admin", True, True))
    
    conn.commit()
    conn.close()
    print("Admin user created: admin/admin123")


def create_sample_namaste_csv():
    """Create sample NAMASTE CSV file"""
    print("Creating sample NAMASTE CSV...")
    
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
    
    df = pd.DataFrame(sample_data)
    df.to_csv('./data/sample_namaste.csv', index=False, encoding='utf-8')
    print(f"Sample NAMASTE CSV created with {len(sample_data)} codes")


def create_sample_data():
    """Create sample terminology codes and mappings"""
    print("Creating sample terminology data...")
    
    conn = sqlite3.connect('./data/fhir_mapping.db')
    cursor = conn.cursor()
    
    # NAMASTE codes
    namaste_codes = [
        ("PRAM001", "Prameha", "A condition characterized by excessive urination and thirst", '{"category": "Metabolic Disorders", "system_name": "Ayurveda"}'),
        ("JWARA001", "Jwara", "Fever or elevated body temperature", '{"category": "Infectious Diseases", "system_name": "Ayurveda"}'),
        ("KASA001", "Kasa", "Cough or respiratory condition", '{"category": "Respiratory Disorders", "system_name": "Ayurveda"}'),
        ("MADHUMEHA001", "Madhumeha", "Diabetes mellitus in Ayurvedic terminology", '{"category": "Metabolic Disorders", "system_name": "Ayurveda"}'),
        ("SANDHIVATA001", "Sandhivata", "Joint disorders or arthritis", '{"category": "Musculoskeletal Disorders", "system_name": "Ayurveda"}')
    ]
    
    namaste_system = "http://terminology.ayush.gov.in/namaste"
    
    for code, display, definition, properties in namaste_codes:
        cursor.execute('''
            INSERT OR REPLACE INTO terminology_codes (system, code, display, definition, properties)
            VALUES (?, ?, ?, ?, ?)
        ''', (namaste_system, code, display, definition, properties))
    
    # ICD-11 TM2 codes
    icd_codes = [
        ("TM-E11", "Diabetes mellitus", "A group of metabolic diseases characterized by high blood sugar", '{"category": "Endocrine, nutritional and metabolic diseases", "parent": "TM-E10-E14"}'),
        ("TM-R50", "Fever, unspecified", "Elevation of body temperature above normal range", '{"category": "Symptoms, signs and abnormal clinical findings", "parent": "TM-R50-R69"}'),
        ("TM-R05", "Cough", "A sudden, forceful expulsion of air from the lungs", '{"category": "Symptoms, signs and abnormal clinical findings", "parent": "TM-R00-R09"}'),
        ("TM-E10", "Type 1 diabetes mellitus", "Diabetes mellitus due to autoimmune pancreatic islet beta-cell destruction", '{"category": "Endocrine, nutritional and metabolic diseases", "parent": "TM-E10-E14"}'),
        ("TM-M15", "Polyarthrosis", "Arthritis affecting multiple joints", '{"category": "Diseases of the musculoskeletal system", "parent": "TM-M15-M19"}')
    ]
    
    icd_system = "http://id.who.int/icd/release/11/tm2"
    
    for code, display, definition, properties in icd_codes:
        cursor.execute('''
            INSERT OR REPLACE INTO terminology_codes (system, code, display, definition, properties)
            VALUES (?, ?, ?, ?, ?)
        ''', (icd_system, code, display, definition, properties))
    
    conn.commit()
    
    # Create mappings
    mappings = [
        ("PRAM001", "TM-E11", "equivalent", 0.9),
        ("JWARA001", "TM-R50", "equivalent", 0.95),
        ("KASA001", "TM-R05", "equivalent", 0.85),
        ("MADHUMEHA001", "TM-E10", "equivalent", 0.92),
        ("SANDHIVATA001", "TM-M15", "equivalent", 0.88)
    ]
    
    for namaste_code, icd_code, equivalence, confidence in mappings:
        # Get source and target code IDs
        cursor.execute("SELECT id FROM terminology_codes WHERE system = ? AND code = ?", (namaste_system, namaste_code))
        source_id = cursor.fetchone()[0]
        
        cursor.execute("SELECT id FROM terminology_codes WHERE system = ? AND code = ?", (icd_system, icd_code))
        target_id = cursor.fetchone()[0]
        
        # Insert mapping
        cursor.execute('''
            INSERT OR REPLACE INTO code_mappings (source_code_id, target_code_id, equivalence, confidence, mapping_method)
            VALUES (?, ?, ?, ?, ?)
        ''', (source_id, target_id, equivalence, confidence, "sample_data"))
    
    conn.commit()
    conn.close()
    
    print(f"Created {len(namaste_codes)} NAMASTE codes, {len(icd_codes)} ICD codes, and {len(mappings)} mappings")


def create_startup_scripts():
    """Create convenient startup scripts"""
    print("Creating startup scripts...")
    
    # Backend startup script
    backend_script = """#!/bin/bash
echo "Starting FHIR NAMASTE-ICD Backend API..."
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""
    
    with open('./start_backend.sh', 'w') as f:
        f.write(backend_script)
    os.chmod('./start_backend.sh', 0o755)
    
    # Frontend startup script
    frontend_script = """#!/bin/bash
echo "Starting Streamlit Frontend..."
cd frontend
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
"""
    
    with open('./start_frontend.sh', 'w') as f:
        f.write(frontend_script)
    os.chmod('./start_frontend.sh', 0o755)
    
    # Combined startup script
    combined_script = """#!/bin/bash
echo "Starting FHIR NAMASTE-ICD Mapping Service..."
echo "This will start both backend and frontend services."
echo "Backend API: http://localhost:8000"
echo "Frontend GUI: http://localhost:8501"
echo ""

# Start backend in background
echo "Starting backend..."
cd backend && python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait a moment for backend to start
sleep 3

# Start frontend
echo "Starting frontend..."
cd frontend && streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &
FRONTEND_PID=$!

echo "Services started!"
echo "Backend PID: $BACKEND_PID"
echo "Frontend PID: $FRONTEND_PID"
echo ""
echo "To stop services, run: kill $BACKEND_PID $FRONTEND_PID"
echo "Or use Ctrl+C and then run: pkill -f uvicorn; pkill -f streamlit"

# Wait for user input to keep script running
read -p "Press Enter to stop services..." 

# Clean shutdown
kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
echo "Services stopped."
"""
    
    with open('./start_services.sh', 'w') as f:
        f.write(combined_script)
    os.chmod('./start_services.sh', 0o755)
    
    print("Created startup scripts: start_backend.sh, start_frontend.sh, start_services.sh")


def main():
    """Main initialization function"""
    print("=" * 60)
    print("FHIR NAMASTE-ICD Mapping Service - Project Initialization")
    print("=" * 60)
    
    try:
        create_database()
        create_admin_user()
        create_sample_namaste_csv()
        create_sample_data()
        create_startup_scripts()
        
        print("\n" + "=" * 60)
        print("✅ Project initialization completed successfully!")
        print("=" * 60)
        print("\n📋 Next steps:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Start backend: ./start_backend.sh (or python backend/main.py)")
        print("3. Start frontend: ./start_frontend.sh (or streamlit run frontend/app.py)")
        print("4. Or start both: ./start_services.sh")
        print("\n🌐 Access URLs:")
        print("• Backend API: http://localhost:8000")
        print("• API Documentation: http://localhost:8000/docs")
        print("• Frontend GUI: http://localhost:8501")
        print("\n🔐 Demo credentials:")
        print("• Username: admin")
        print("• Password: admin123")
        print("• ABHA IDs: 14-1234-5678-9012, 14-5678-9012-3456, 14-9012-3456-7890")
        print("• OTP: any 6 digits")
        
    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
