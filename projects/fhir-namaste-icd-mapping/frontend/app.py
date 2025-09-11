"""
Streamlit GUI Application

Web interface for the FHIR NAMASTE-ICD Mapping Service providing
search, translate, upload, and audit functionality.
"""

import streamlit as st
import requests
import pandas as pd
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import plotly.express as px
import plotly.graph_objects as go

# Configure Streamlit page
st.set_page_config(
    page_title="FHIR NAMASTE-ICD Mapping Service",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Backend API configuration
API_BASE_URL = "http://localhost:8000"

# Session state initialization
if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "user_info" not in st.session_state:
    st.session_state.user_info = None
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


def make_api_request(
    endpoint: str,
    method: str = "GET",
    data: Optional[Dict] = None,
    files: Optional[Dict] = None,
    params: Optional[Dict] = None
) -> Dict[str, Any]:
    """Make authenticated API request"""
    
    headers = {}
    if st.session_state.access_token:
        headers["Authorization"] = f"Bearer {st.session_state.access_token}"
    
    if files:
        # Don't set content-type for file uploads
        pass
    elif data:
        headers["Content-Type"] = "application/json"
    
    try:
        url = f"{API_BASE_URL}{endpoint}"
        
        if method == "GET":
            response = requests.get(url, headers=headers, params=params)
        elif method == "POST":
            if files:
                response = requests.post(url, headers=headers, files=files, data=data)
            else:
                response = requests.post(url, headers=headers, json=data, params=params)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        if response.status_code == 401:
            st.session_state.authenticated = False
            st.session_state.access_token = None
            st.error("Authentication expired. Please login again.")
            st.rerun()
        
        response.raise_for_status()
        return response.json()
        
    except requests.exceptions.RequestException as e:
        st.error(f"API request failed: {str(e)}")
        return {"error": str(e)}


def authenticate_user(username: str, password: str) -> bool:
    """Authenticate user with backend API"""
    
    try:
        data = {
            "username": username,
            "password": password
        }
        
        response = requests.post(
            f"{API_BASE_URL}/auth/token",
            data=data,  # OAuth2PasswordRequestForm expects form data
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if response.status_code == 200:
            token_data = response.json()
            st.session_state.access_token = token_data["access_token"]
            st.session_state.user_info = {
                "user_id": token_data.get("user_id"),
                "abha_id": token_data.get("abha_id"),
                "username": username
            }
            st.session_state.authenticated = True
            return True
        else:
            st.error("Invalid username or password")
            return False
            
    except requests.exceptions.RequestException as e:
        st.error(f"Authentication failed: {str(e)}")
        return False


def authenticate_with_abha(abha_id: str, otp: str) -> bool:
    """Authenticate user with ABHA ID and OTP"""
    
    try:
        data = {
            "abha_id": abha_id,
            "auth_method": "otp",
            "otp": otp
        }
        
        response = requests.post(f"{API_BASE_URL}/auth/abha", json=data)
        
        if response.status_code == 200:
            token_data = response.json()
            st.session_state.access_token = token_data["access_token"]
            st.session_state.user_info = {
                "user_id": token_data.get("user_id"),
                "abha_id": token_data.get("abha_id"),
                "username": abha_id
            }
            st.session_state.authenticated = True
            return True
        else:
            st.error("Invalid ABHA ID or OTP")
            return False
            
    except requests.exceptions.RequestException as e:
        st.error(f"ABHA authentication failed: {str(e)}")
        return False


def login_page():
    """Display login page"""
    
    st.title("🏥 FHIR NAMASTE-ICD Mapping Service")
    st.markdown("### Healthcare Terminology Mapping with FHIR R4 Compliance")
    
    # Login tabs
    tab1, tab2 = st.tabs(["Username/Password", "ABHA Authentication"])
    
    with tab1:
        st.subheader("Login with Username/Password")
        
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            if st.form_submit_button("Login", use_container_width=True):
                if username and password:
                    if authenticate_user(username, password):
                        st.success("Login successful!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.warning("Please enter both username and password")
        
        st.info("Demo credentials: `admin` / `admin123`")
    
    with tab2:
        st.subheader("ABHA Authentication")
        
        with st.form("abha_form"):
            abha_id = st.text_input(
                "ABHA ID", 
                placeholder="14-1234-5678-9012",
                help="Enter your 14-digit ABHA ID"
            )
            otp = st.text_input(
                "OTP", 
                type="password",
                placeholder="Enter 6-digit OTP",
                max_chars=6
            )
            
            if st.form_submit_button("Authenticate with ABHA", use_container_width=True):
                if abha_id and otp:
                    if authenticate_with_abha(abha_id, otp):
                        st.success("ABHA authentication successful!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.warning("Please enter both ABHA ID and OTP")
        
        st.info("Demo ABHA IDs: `14-1234-5678-9012`, `14-5678-9012-3456`, `14-9012-3456-7890` (OTP: any 6 digits)")


def search_page():
    """Terminology search page"""
    
    st.title("🔍 Terminology Search")
    st.markdown("Search for codes across NAMASTE and ICD-11 TM2 terminology systems")
    
    # Search form
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_term = st.text_input(
            "Search Term",
            placeholder="Enter code, display name, or keyword (e.g., 'Prameha', 'diabetes', 'fever')",
            help="Search across code, display name, and definition fields"
        )
    
    with col2:
        system_filter = st.selectbox(
            "Filter by System",
            options=["All Systems", "NAMASTE", "ICD-11 TM2"],
            help="Filter results by terminology system"
        )
    
    if st.button("Search", use_container_width=True) and search_term:
        with st.spinner("Searching..."):
            
            # Map system filter
            system_param = None
            if system_filter == "NAMASTE":
                system_param = "http://terminology.ayush.gov.in/namaste"
            elif system_filter == "ICD-11 TM2":
                system_param = "http://id.who.int/icd/release/11/tm2"
            
            # Make API request
            params = {"term": search_term, "limit": 50}
            if system_param:
                params["system"] = system_param
            
            results = make_api_request("/search", params=params)
            
            if "error" not in results and results:
                st.success(f"Found {len(results)} results")
                
                # Display results in expandable cards
                for result in results:
                    system_name = "NAMASTE" if "namaste" in result["system"] else "ICD-11 TM2"
                    
                    with st.expander(f"{system_name}: {result['code']} - {result['display']}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write("**Code:**", result["code"])
                            st.write("**Display:**", result["display"])
                            st.write("**System:**", system_name)
                        
                        with col2:
                            if result.get("definition"):
                                st.write("**Definition:**", result["definition"])
                            
                            if result.get("properties"):
                                st.write("**Properties:**")
                                for key, value in result["properties"].items():
                                    st.write(f"- {key}: {value}")
            
            elif not results:
                st.info("No results found. Try a different search term.")
            else:
                st.error("Search failed. Please try again.")
    
    # Recent searches (if we stored them)
    st.markdown("---")
    st.subheader("💡 Search Tips")
    st.markdown("""
    - Use common medical terms like 'diabetes', 'fever', 'cough'
    - Search by code (e.g., 'PRAM001', 'TM-E11')
    - Use partial terms for broader results
    - Try both English and Ayurvedic terminology
    """)


def translate_page():
    """Code translation page"""
    
    st.title("🔄 Code Translation")
    st.markdown("Translate codes between NAMASTE and ICD-11 TM2 systems")
    
    # Translation form
    col1, col2, col3 = st.columns(3)
    
    with col1:
        source_system = st.selectbox(
            "Source System",
            options=["NAMASTE", "ICD-11 TM2"],
            help="Select the source terminology system"
        )
    
    with col2:
        target_system = st.selectbox(
            "Target System",
            options=["ICD-11 TM2", "NAMASTE"],
            index=0 if source_system == "NAMASTE" else 1,
            help="Select the target terminology system"
        )
    
    with col3:
        code_input = st.text_input(
            "Code to Translate",
            placeholder="e.g., PRAM001 or TM-E11",
            help="Enter the code you want to translate"
        )
    
    if st.button("Translate", use_container_width=True) and code_input:
        if source_system == target_system:
            st.warning("Source and target systems must be different")
        else:
            with st.spinner("Translating..."):
                
                # Map system names to URIs
                system_map = {
                    "NAMASTE": "http://terminology.ayush.gov.in/namaste",
                    "ICD-11 TM2": "http://id.who.int/icd/release/11/tm2"
                }
                
                source_uri = system_map[source_system]
                target_uri = system_map[target_system]
                
                # Make API request
                params = {
                    "source": source_uri,
                    "target": target_uri,
                    "code": code_input
                }
                
                result = make_api_request("/translate", params=params)
                
                if result and "error" not in result:
                    st.success("Translation found!")
                    
                    # Display translation result
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Source")
                        st.write("**System:**", source_system)
                        st.write("**Code:**", result["source_code"])
                        st.write("**Display:**", result.get("source_display", "N/A"))
                    
                    with col2:
                        st.subheader("Target")
                        st.write("**System:**", target_system)
                        st.write("**Code:**", result["target_code"])
                        st.write("**Display:**", result.get("target_display", "N/A"))
                    
                    # Mapping quality info
                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("Equivalence", result["equivalence"].title())
                    
                    with col2:
                        confidence_pct = result["confidence"] * 100
                        st.metric("Confidence", f"{confidence_pct:.1f}%")
                    
                    # Show confidence with color coding
                    if result["confidence"] >= 0.9:
                        st.success("High confidence mapping")
                    elif result["confidence"] >= 0.7:
                        st.warning("Medium confidence mapping")
                    else:
                        st.error("Low confidence mapping - manual review recommended")
                
                else:
                    st.warning("No translation found for this code. The code may not exist or hasn't been mapped yet.")
    
    # Show available codes for reference
    st.markdown("---")
    st.subheader("📖 Available Sample Codes")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**NAMASTE Codes:**")
        st.code("""
PRAM001  - Prameha (Diabetes-related)
JWARA001 - Jwara (Fever)
KASA001  - Kasa (Cough)
MADHUMEHA001 - Madhumeha (Diabetes)
SANDHIVATA001 - Sandhivata (Arthritis)
        """, language="text")
    
    with col2:
        st.markdown("**ICD-11 TM2 Codes:**")
        st.code("""
TM-E11 - Diabetes mellitus
TM-R50 - Fever, unspecified
TM-R05 - Cough
TM-M15 - Polyarthrosis
TM-K21 - GERD
        """, language="text")


def upload_page():
    """Data upload page"""
    
    st.title("📤 Data Upload")
    st.markdown("Upload NAMASTE CSV files and manage terminology data")
    
    # File upload section
    st.subheader("Upload NAMASTE CSV File")
    
    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type="csv",
        help="Upload a CSV file with NAMASTE terminology codes"
    )
    
    if uploaded_file is not None:
        # Show file preview
        try:
            df = pd.read_csv(uploaded_file)
            
            st.subheader("File Preview")
            st.dataframe(df.head(10), use_container_width=True)
            
            st.info(f"File contains {len(df)} rows and {len(df.columns)} columns")
            
            # Validate required columns
            required_columns = ["code", "display"]
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                st.error(f"Missing required columns: {missing_columns}")
            else:
                st.success("File format is valid")
                
                if st.button("Upload and Process", use_container_width=True):
                    with st.spinner("Processing file..."):
                        
                        # Reset file pointer
                        uploaded_file.seek(0)
                        
                        # Upload file
                        files = {"file": uploaded_file}
                        result = make_api_request("/upload/namaste", method="POST", files=files)
                        
                        if result.get("success"):
                            st.success(f"Successfully uploaded {result.get('codes_loaded', 0)} codes!")
                            
                            # Show upload details
                            if result.get("validation"):
                                validation = result["validation"]
                                
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Total Rows", validation.get("total_rows", 0))
                                with col2:
                                    st.metric("Valid Rows", validation.get("valid_rows", 0))
                                with col3:
                                    st.metric("Codes Loaded", result.get("codes_loaded", 0))
                                
                                if validation.get("warnings"):
                                    with st.expander("Warnings"):
                                        for warning in validation["warnings"]:
                                            st.warning(warning)
                        else:
                            st.error(f"Upload failed: {result.get('message', 'Unknown error')}")
                            if result.get("errors"):
                                for error in result["errors"]:
                                    st.error(error)
        
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")
    
    # Data management section
    st.markdown("---")
    st.subheader("Data Management")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Sync ICD-11 TM2 Codes", use_container_width=True):
            with st.spinner("Syncing ICD-11 codes..."):
                result = make_api_request("/sync/icd11", method="POST")
                
                if result.get("success"):
                    st.success(f"Synced {result.get('codes_synced', 0)} ICD-11 TM2 codes")
                else:
                    st.error(f"Sync failed: {result.get('message', 'Unknown error')}")
    
    with col2:
        if st.button("Create Automatic Mappings", use_container_width=True):
            with st.spinner("Creating mappings..."):
                result = make_api_request("/mappings/create", method="POST")
                
                if result.get("success"):
                    st.success(f"Created {result.get('mappings_created', 0)} mappings")
                    
                    # Show sample mappings
                    if result.get("mappings"):
                        st.subheader("Sample Mappings Created")
                        mappings_df = pd.DataFrame(result["mappings"])
                        st.dataframe(mappings_df, use_container_width=True)
                else:
                    st.error(f"Mapping creation failed: {result.get('message', 'Unknown error')}")
    
    # Sample data download
    st.markdown("---")
    st.subheader("📥 Sample Data")
    
    sample_data = [
        {"code": "PRAM001", "display": "Prameha", "definition": "Diabetes-like condition", "category": "Metabolic"},
        {"code": "JWARA001", "display": "Jwara", "definition": "Fever condition", "category": "Infectious"},
        {"code": "KASA001", "display": "Kasa", "definition": "Cough condition", "category": "Respiratory"}
    ]
    
    sample_df = pd.DataFrame(sample_data)
    st.dataframe(sample_df, use_container_width=True)
    
    csv = sample_df.to_csv(index=False)
    st.download_button(
        label="Download Sample CSV",
        data=csv,
        file_name="sample_namaste.csv",
        mime="text/csv"
    )


def fhir_page():
    """FHIR resources page"""
    
    st.title("🔬 FHIR Resources")
    st.markdown("View and generate FHIR R4-compliant resources")
    
    # FHIR resource tabs
    tab1, tab2 = st.tabs(["CodeSystems", "ConceptMaps"])
    
    with tab1:
        st.subheader("FHIR CodeSystems")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if st.button("Generate NAMASTE CodeSystem", use_container_width=True):
                with st.spinner("Generating NAMASTE CodeSystem..."):
                    result = make_api_request(
                        "/fhir/generate/CodeSystem",
                        method="POST",
                        params={"system": "http://terminology.ayush.gov.in/namaste"}
                    )
                    
                    if "error" not in result:
                        st.success("NAMASTE CodeSystem generated!")
                        with st.expander("View FHIR JSON"):
                            st.json(result)
                    else:
                        st.error("Failed to generate CodeSystem")
        
        with col2:
            if st.button("Generate ICD-11 CodeSystem", use_container_width=True):
                with st.spinner("Generating ICD-11 CodeSystem..."):
                    result = make_api_request(
                        "/fhir/generate/CodeSystem",
                        method="POST",
                        params={"system": "http://id.who.int/icd/release/11/tm2"}
                    )
                    
                    if "error" not in result:
                        st.success("ICD-11 CodeSystem generated!")
                        with st.expander("View FHIR JSON"):
                            st.json(result)
                    else:
                        st.error("Failed to generate CodeSystem")
        
        # View existing CodeSystems
        if st.button("View All CodeSystems"):
            with st.spinner("Fetching CodeSystems..."):
                result = make_api_request("/fhir/CodeSystem")
                
                if "error" not in result and result.get("entry"):
                    st.success(f"Found {result['total']} CodeSystems")
                    
                    for i, entry in enumerate(result["entry"]):
                        resource = entry["resource"]
                        with st.expander(f"CodeSystem: {resource.get('title', resource.get('name', f'Resource {i+1}'))}"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write("**ID:**", resource.get("id"))
                                st.write("**URL:**", resource.get("url"))
                                st.write("**Version:**", resource.get("version"))
                                st.write("**Status:**", resource.get("status"))
                            
                            with col2:
                                st.write("**Publisher:**", resource.get("publisher"))
                                st.write("**Date:**", resource.get("date"))
                                if resource.get("concept"):
                                    st.write("**Concepts:**", len(resource["concept"]))
                            
                            if st.button(f"Download JSON", key=f"download_cs_{i}"):
                                json_str = json.dumps(resource, indent=2)
                                st.download_button(
                                    label="Download FHIR JSON",
                                    data=json_str,
                                    file_name=f"codesystem_{resource.get('name', i)}.json",
                                    mime="application/json",
                                    key=f"dl_cs_{i}"
                                )
                else:
                    st.info("No CodeSystems found")
    
    with tab2:
        st.subheader("FHIR ConceptMaps")
        
        if st.button("Generate NAMASTE → ICD-11 ConceptMap", use_container_width=True):
            with st.spinner("Generating ConceptMap..."):
                result = make_api_request(
                    "/fhir/generate/ConceptMap",
                    method="POST",
                    params={
                        "source_system": "http://terminology.ayush.gov.in/namaste",
                        "target_system": "http://id.who.int/icd/release/11/tm2"
                    }
                )
                
                if "error" not in result:
                    st.success("ConceptMap generated!")
                    with st.expander("View FHIR JSON"):
                        st.json(result)
                else:
                    st.error("Failed to generate ConceptMap")
        
        # View existing ConceptMaps
        if st.button("View All ConceptMaps"):
            with st.spinner("Fetching ConceptMaps..."):
                result = make_api_request("/fhir/ConceptMap")
                
                if "error" not in result and result.get("entry"):
                    st.success(f"Found {result['total']} ConceptMaps")
                    
                    for i, entry in enumerate(result["entry"]):
                        resource = entry["resource"]
                        with st.expander(f"ConceptMap: {resource.get('title', f'Map {i+1}')}"):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write("**Source:**", resource.get("sourceUri", "").split("/")[-1])
                                st.write("**Target:**", resource.get("targetUri", "").split("/")[-1])
                                st.write("**Status:**", resource.get("status"))
                            
                            with col2:
                                st.write("**Date:**", resource.get("date"))
                                if resource.get("group"):
                                    total_mappings = sum(len(g.get("element", [])) for g in resource["group"])
                                    st.write("**Mappings:**", total_mappings)
                            
                            # Show mapping details
                            if resource.get("group"):
                                for group in resource["group"]:
                                    if group.get("element"):
                                        st.write("**Sample Mappings:**")
                                        mappings_data = []
                                        for element in group["element"][:5]:  # Show first 5
                                            for target in element.get("target", []):
                                                mappings_data.append({
                                                    "Source Code": element["code"],
                                                    "Source Display": element.get("display", ""),
                                                    "Target Code": target["code"],
                                                    "Target Display": target.get("display", ""),
                                                    "Equivalence": target.get("equivalence", "")
                                                })
                                        
                                        if mappings_data:
                                            st.dataframe(pd.DataFrame(mappings_data), use_container_width=True)
                else:
                    st.info("No ConceptMaps found")


def analytics_page():
    """Analytics and dashboard page"""
    
    st.title("📊 Analytics Dashboard")
    st.markdown("System statistics and mapping analytics")
    
    # Fetch dashboard data
    with st.spinner("Loading dashboard data..."):
        dashboard_data = make_api_request("/analytics/dashboard")
    
    if "error" not in dashboard_data:
        # Summary metrics
        st.subheader("System Overview")
        
        col1, col2, col3, col4 = st.columns(4)
        
        summary = dashboard_data.get("summary", {})
        
        with col1:
            st.metric("NAMASTE Codes", summary.get("namaste_codes", 0))
        
        with col2:
            st.metric("ICD-11 Codes", summary.get("icd11_codes", 0))
        
        with col3:
            st.metric("Total Mappings", summary.get("total_mappings", 0))
        
        with col4:
            st.metric("Active Users", summary.get("active_users", 0))
        
        # Mapping statistics
        st.markdown("---")
        st.subheader("Mapping Statistics")
        
        mapping_stats = dashboard_data.get("mapping_statistics", {})
        
        if mapping_stats.get("confidence_distribution"):
            col1, col2 = st.columns(2)
            
            with col1:
                # Confidence distribution chart
                conf_dist = mapping_stats["confidence_distribution"]
                fig = px.pie(
                    values=list(conf_dist.values()),
                    names=list(conf_dist.keys()),
                    title="Mapping Confidence Distribution"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Method distribution chart
                method_dist = mapping_stats.get("method_distribution", {})
                if method_dist:
                    fig = px.bar(
                        x=list(method_dist.keys()),
                        y=list(method_dist.values()),
                        title="Mapping Methods Used"
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        # System pairs
        if mapping_stats.get("system_pairs"):
            st.subheader("System Mapping Pairs")
            pairs_data = []
            
            for pair, count in mapping_stats["system_pairs"].items():
                source, target = pair.split(" -> ")
                source_name = "NAMASTE" if "namaste" in source else "ICD-11 TM2"
                target_name = "NAMASTE" if "namaste" in target else "ICD-11 TM2"
                
                pairs_data.append({
                    "Source System": source_name,
                    "Target System": target_name,
                    "Mapping Count": count
                })
            
            if pairs_data:
                st.dataframe(pd.DataFrame(pairs_data), use_container_width=True)
        
        # NAMASTE statistics
        st.markdown("---")
        st.subheader("NAMASTE Data Analysis")
        
        namaste_stats = dashboard_data.get("namaste_statistics", {})
        
        if namaste_stats.get("categories"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Categories:**")
                for category in namaste_stats["categories"]:
                    st.write(f"• {category}")
            
            with col2:
                st.write("**Systems:**")
                for system in namaste_stats.get("systems", []):
                    st.write(f"• {system}")
        
        # Recent activity
        st.markdown("---")
        st.subheader("Recent Activity")
        
        recent_activity = dashboard_data.get("recent_activity", [])
        
        if recent_activity:
            activity_df = pd.DataFrame(recent_activity)
            activity_df["timestamp"] = pd.to_datetime(activity_df["timestamp"])
            
            st.dataframe(
                activity_df[["timestamp", "action", "user"]],
                use_container_width=True,
                column_config={
                    "timestamp": st.column_config.DatetimeColumn("Time"),
                    "action": st.column_config.TextColumn("Action"),
                    "user": st.column_config.TextColumn("User")
                }
            )
        else:
            st.info("No recent activity")
    
    else:
        st.error("Failed to load dashboard data")


def logs_page():
    """Audit logs page"""
    
    st.title("📋 Audit Logs")
    st.markdown("System audit trail and activity logs")
    
    # Get mapping statistics (includes some audit info)
    with st.spinner("Loading audit information..."):
        result = make_api_request("/mappings/statistics")
    
    if "error" not in result:
        st.subheader("Mapping Activity Summary")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Mappings", result.get("total_mappings", 0))
            
            # Confidence breakdown
            conf_dist = result.get("confidence_distribution", {})
            if conf_dist:
                st.write("**Confidence Levels:**")
                st.write(f"• High (≥80%): {conf_dist.get('high', 0)}")
                st.write(f"• Medium (60-79%): {conf_dist.get('medium', 0)}")
                st.write(f"• Low (<60%): {conf_dist.get('low', 0)}")
        
        with col2:
            # Method breakdown
            method_dist = result.get("method_distribution", {})
            if method_dist:
                st.write("**Mapping Methods:**")
                for method, count in method_dist.items():
                    st.write(f"• {method.title()}: {count}")
        
        # Show system pairs
        system_pairs = result.get("system_pairs", {})
        if system_pairs:
            st.subheader("System Interaction Matrix")
            pairs_data = []
            
            for pair, count in system_pairs.items():
                source, target = pair.split(" -> ")
                source_name = "NAMASTE" if "namaste" in source else "ICD-11 TM2"
                target_name = "NAMASTE" if "namaste" in target else "ICD-11 TM2"
                
                pairs_data.append({
                    "Source": source_name,
                    "Target": target_name,
                    "Mappings": count
                })
            
            st.dataframe(pd.DataFrame(pairs_data), use_container_width=True)
    
    else:
        st.error("Failed to load audit information")
    
    # Add manual audit log viewer placeholder
    st.markdown("---")
    st.subheader("Audit Log Viewer")
    st.info("In a full implementation, this section would show detailed audit logs with filtering and search capabilities.")
    
    # Show sample log structure
    st.write("**Sample Audit Log Structure:**")
    sample_log = {
        "timestamp": "2024-01-15T10:30:00Z",
        "user_id": 1,
        "abha_id": "14-1234-5678-9012",
        "action": "terminology_search",
        "resource_type": "TerminologyCode",
        "details": {
            "search_term": "Prameha",
            "results_count": 5,
            "execution_time_ms": 45.2
        },
        "ip_address": "192.168.1.100",
        "success": True
    }
    st.json(sample_log)


def main():
    """Main application function"""
    
    # Check authentication
    if not st.session_state.authenticated:
        login_page()
        return
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    
    # User info
    if st.session_state.user_info:
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Logged in as:**")
        st.sidebar.write(f"👤 {st.session_state.user_info['username']}")
        if st.session_state.user_info.get("abha_id"):
            st.sidebar.write(f"🆔 {st.session_state.user_info['abha_id']}")
    
    # Navigation menu
    page = st.sidebar.selectbox(
        "Choose a page",
        ["🔍 Search", "🔄 Translate", "📤 Upload", "🔬 FHIR", "📊 Analytics", "📋 Logs"]
    )
    
    # Logout button
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.access_token = None
        st.session_state.user_info = None
        st.rerun()
    
    # Page routing
    if page == "🔍 Search":
        search_page()
    elif page == "🔄 Translate":
        translate_page()
    elif page == "📤 Upload":
        upload_page()
    elif page == "🔬 FHIR":
        fhir_page()
    elif page == "📊 Analytics":
        analytics_page()
    elif page == "📋 Logs":
        logs_page()


if __name__ == "__main__":
    main()
