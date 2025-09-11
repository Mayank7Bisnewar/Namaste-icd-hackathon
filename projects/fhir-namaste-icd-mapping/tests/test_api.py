"""
Test Suite for FHIR NAMASTE-ICD Mapping Service

Comprehensive tests for API endpoints, authentication, and core functionality.
"""

import pytest
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
import os

# Import application modules
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from main import app
from database import Base, get_db, User
from auth import get_password_hash


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(scope="function")
def test_db():
    """Create test database"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    # Create test user
    test_user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        hashed_password=get_password_hash("testpass123"),
        is_active=True,
        is_verified=True,
        role="user"
    )
    db.add(test_user)
    db.commit()
    
    yield db
    
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def auth_headers(test_db):
    """Get authentication headers for testing"""
    # Login to get token
    response = client.post("/auth/token", data={
        "username": "testuser",
        "password": "testpass123"
    })
    
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


class TestHealthEndpoints:
    """Test health check endpoints"""
    
    def test_root_endpoint(self):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert data["status"] == "healthy"
    
    def test_health_endpoint(self, test_db):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "database" in data
        assert "components" in data


class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_login_success(self, test_db):
        """Test successful login"""
        response = client.post("/auth/token", data={
            "username": "testuser",
            "password": "testpass123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
    
    def test_login_failure(self, test_db):
        """Test failed login"""
        response = client.post("/auth/token", data={
            "username": "testuser",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
    
    def test_register_user(self, test_db):
        """Test user registration"""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "full_name": "New User",
            "password": "newpass123"
        }
        
        response = client.post("/auth/register", json=user_data)
        assert response.status_code == 200
        data = response.json()
        assert "user_id" in data
        assert data["username"] == "newuser"
    
    def test_abha_authentication(self, test_db):
        """Test ABHA authentication"""
        abha_data = {
            "abha_id": "14-1234-5678-9012",
            "auth_method": "otp",
            "otp": "123456"
        }
        
        response = client.post("/auth/abha", json=abha_data)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["abha_id"] == "14-1234-5678-9012"


class TestSearchEndpoints:
    """Test search functionality"""
    
    def test_search_without_auth(self):
        """Test search endpoint without authentication"""
        response = client.get("/search?term=diabetes")
        assert response.status_code == 401
    
    def test_search_with_auth(self, test_db, auth_headers):
        """Test search endpoint with authentication"""
        # First, add some test data
        from database import TerminologyCode, TerminologySystem
        
        db = test_db
        test_code = TerminologyCode(
            system=TerminologySystem.NAMASTE,
            code="TEST001",
            display="Test Condition",
            definition="A test condition for testing"
        )
        db.add(test_code)
        db.commit()
        
        # Test search
        response = client.get("/search?term=test", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_search_with_system_filter(self, test_db, auth_headers):
        """Test search with system filter"""
        response = client.get(
            "/search?term=diabetes&system=http://terminology.ayush.gov.in/namaste",
            headers=auth_headers
        )
        assert response.status_code == 200


class TestTranslationEndpoints:
    """Test translation functionality"""
    
    def test_translate_without_auth(self):
        """Test translation without authentication"""
        response = client.get("/translate?source=namaste&target=icd11&code=TEST001")
        assert response.status_code == 401
    
    def test_translate_nonexistent_code(self, test_db, auth_headers):
        """Test translation of non-existent code"""
        response = client.get(
            "/translate?source=http://terminology.ayush.gov.in/namaste&target=http://id.who.int/icd/release/11/tm2&code=NONEXISTENT",
            headers=auth_headers
        )
        assert response.status_code == 200
        # Should return null for non-existent mappings
        data = response.json()
        assert data is None


class TestUploadEndpoints:
    """Test file upload functionality"""
    
    def test_upload_csv_without_auth(self):
        """Test CSV upload without authentication"""
        csv_content = "code,display,definition\nTEST001,Test Code,Test Definition"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_file_path = f.name
        
        try:
            with open(temp_file_path, 'rb') as f:
                response = client.post("/upload/namaste", files={"file": f})
            assert response.status_code == 401
        finally:
            os.unlink(temp_file_path)
    
    def test_upload_invalid_file_type(self, test_db, auth_headers):
        """Test upload of invalid file type"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Invalid file content")
            temp_file_path = f.name
        
        try:
            with open(temp_file_path, 'rb') as f:
                response = client.post(
                    "/upload/namaste", 
                    files={"file": ("test.txt", f, "text/plain")},
                    headers=auth_headers
                )
            assert response.status_code == 400
        finally:
            os.unlink(temp_file_path)
    
    def test_upload_valid_csv(self, test_db, auth_headers):
        """Test upload of valid CSV file"""
        csv_content = "code,display,definition\nTEST002,Test Code 2,Test Definition 2"
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_file_path = f.name
        
        try:
            with open(temp_file_path, 'rb') as f:
                response = client.post(
                    "/upload/namaste",
                    files={"file": ("test.csv", f, "text/csv")},
                    headers=auth_headers
                )
            assert response.status_code == 200
            data = response.json()
            assert data.get("success", False)
        finally:
            os.unlink(temp_file_path)


class TestFHIREndpoints:
    """Test FHIR resource endpoints"""
    
    def test_get_codesystems_without_auth(self):
        """Test CodeSystem access without authentication"""
        response = client.get("/fhir/CodeSystem")
        assert response.status_code == 401
    
    def test_get_codesystems_with_auth(self, test_db, auth_headers):
        """Test CodeSystem access with authentication"""
        response = client.get("/fhir/CodeSystem", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "resourceType" in data
        assert data["resourceType"] == "Bundle"
    
    def test_get_conceptmaps_with_auth(self, test_db, auth_headers):
        """Test ConceptMap access with authentication"""
        response = client.get("/fhir/ConceptMap", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "resourceType" in data
        assert data["resourceType"] == "Bundle"
    
    def test_generate_codesystem(self, test_db, auth_headers):
        """Test CodeSystem generation"""
        response = client.post(
            "/fhir/generate/CodeSystem?system=http://terminology.ayush.gov.in/namaste",
            headers=auth_headers
        )
        # May fail if no data, but should not be 401/403
        assert response.status_code in [200, 404]


class TestAnalyticsEndpoints:
    """Test analytics and dashboard endpoints"""
    
    def test_dashboard_without_auth(self):
        """Test dashboard access without authentication"""
        response = client.get("/analytics/dashboard")
        assert response.status_code == 401
    
    def test_dashboard_with_auth(self, test_db, auth_headers):
        """Test dashboard access with authentication"""
        response = client.get("/analytics/dashboard", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "generated_at" in data
    
    def test_mapping_statistics(self, test_db, auth_headers):
        """Test mapping statistics endpoint"""
        response = client.get("/mappings/statistics", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        # Should return statistics even if empty
        assert isinstance(data, dict)


class TestDataSync:
    """Test data synchronization functionality"""
    
    def test_sync_icd11_codes(self, test_db, auth_headers):
        """Test ICD-11 code synchronization"""
        response = client.post("/sync/icd11", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "message" in data
    
    def test_create_mappings(self, test_db, auth_headers):
        """Test automatic mapping creation"""
        response = client.post("/mappings/create", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "message" in data


class TestErrorHandling:
    """Test error handling"""
    
    def test_invalid_endpoint(self):
        """Test 404 handling"""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
    
    def test_malformed_request(self, test_db, auth_headers):
        """Test handling of malformed requests"""
        # Test with invalid JSON
        response = client.post(
            "/auth/register",
            data="invalid json",
            headers={"Content-Type": "application/json", **auth_headers}
        )
        assert response.status_code in [400, 422]


# Integration tests
class TestIntegrationFlow:
    """Test complete user flows"""
    
    def test_complete_user_journey(self, test_db):
        """Test complete user journey from registration to search"""
        
        # 1. Register user
        user_data = {
            "username": "journeyuser",
            "email": "journey@example.com",
            "full_name": "Journey User",
            "password": "journey123"
        }
        
        response = client.post("/auth/register", json=user_data)
        assert response.status_code == 200
        
        # 2. Login
        response = client.post("/auth/token", data={
            "username": "journeyuser",
            "password": "journey123"
        })
        assert response.status_code == 200
        token = response.json()["access_token"]
        auth_headers = {"Authorization": f"Bearer {token}"}
        
        # 3. Sync ICD codes
        response = client.post("/sync/icd11", headers=auth_headers)
        assert response.status_code == 200
        
        # 4. Search for codes
        response = client.get("/search?term=diabetes", headers=auth_headers)
        assert response.status_code == 200
        
        # 5. Get dashboard
        response = client.get("/analytics/dashboard", headers=auth_headers)
        assert response.status_code == 200
    
    def test_abha_user_journey(self, test_db):
        """Test ABHA user authentication journey"""
        
        # 1. ABHA authentication
        abha_data = {
            "abha_id": "14-1234-5678-9012",
            "auth_method": "otp",
            "otp": "123456"
        }
        
        response = client.post("/auth/abha", json=abha_data)
        assert response.status_code == 200
        token_data = response.json()
        assert "access_token" in token_data
        assert token_data["abha_id"] == "14-1234-5678-9012"
        
        # 2. Use token for API access
        auth_headers = {"Authorization": f"Bearer {token_data['access_token']}"}
        
        response = client.get("/search?term=fever", headers=auth_headers)
        assert response.status_code == 200


# Performance tests
class TestPerformance:
    """Test application performance"""
    
    def test_search_response_time(self, test_db, auth_headers):
        """Test search response time"""
        import time
        
        start_time = time.time()
        response = client.get("/search?term=diabetes", headers=auth_headers)
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 2.0  # Should respond within 2 seconds
    
    def test_concurrent_requests(self, test_db, auth_headers):
        """Test handling of concurrent requests"""
        import threading
        
        results = []
        
        def make_request():
            response = client.get("/search?term=test", headers=auth_headers)
            results.append(response.status_code)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Check all requests succeeded
        assert all(status == 200 for status in results)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
