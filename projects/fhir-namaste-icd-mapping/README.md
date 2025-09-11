# FHIR NAMASTE-ICD Mapping Service

A FHIR R4-compliant healthcare interoperability application that enables dual-coding between NAMASTE (Ayush terminology) and ICD-11 TM2, with ABHA authentication integration.

## 🎯 Overview

This application addresses the critical need for harmonizing traditional medicine terminology systems (NAMASTE, WHO International Terminologies, ICD-11 TM2) with India's digital healthcare (EMR/EHR) ecosystem. It provides seamless dual coding, compliance features, analytics capabilities, and insurance integration.

## 🚀 Key Features

- **Dual Coding System**: Maps NAMASTE codes to ICD-11 TM2 and vice versa
- **FHIR R4 Compliance**: Full support for FHIR resources (CodeSystem, ConceptMap, Patient, Encounter)
- **ABHA Authentication**: Mock OAuth 2.0 integration with ABHA tokens
- **Search & Translate**: REST endpoints with fuzzy search and autocomplete
- **Web Interface**: Streamlit-based GUI with search, translate, upload, and audit tabs
- **Audit & Consent**: Comprehensive logging and consent management
- **Real-time Integration**: Live API integration with WHO ICD-11 and NAMASTE datasets

## 🏗️ Architecture

```
fhir-namaste-icd-mapping/
├── backend/                 # FastAPI REST API
│   ├── main.py             # FastAPI application entry point
│   ├── fhir_resources.py   # FHIR R4 resource models
│   ├── auth.py             # OAuth 2.0 & ABHA authentication
│   ├── namaste_loader.py   # NAMASTE CSV data loader
│   ├── icd_api.py          # ICD-11 API integration
│   └── database.py         # Database models and operations
├── frontend/               # Streamlit web interface
│   ├── app.py              # Main Streamlit application
│   └── components/         # UI components
├── data/                   # Data storage and samples
└── tests/                  # Test suite
```

## 🛠️ Technology Stack

- **Backend**: FastAPI, Python 3.10+
- **Frontend**: Streamlit
- **Database**: SQLite/PostgreSQL
- **FHIR**: fhir.resources Python package
- **Authentication**: OAuth 2.0 with mock ABHA
- **APIs**: WHO ICD-11, NAMASTE datasets

## 📦 Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd fhir-namaste-icd-mapping
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Initialize database**:
```bash
python -c "from backend.database import init_db; init_db()"
```

## 🚀 Usage

### Start the Backend API
```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Start the Frontend GUI
```bash
cd frontend
streamlit run app.py --server.port 8501
```

### API Endpoints

- `GET /search?term={term}` - Search for codes across terminologies
- `GET /translate?source={source}&target={target}&code={code}` - Translate between terminologies
- `POST /upload/namaste` - Upload NAMASTE CSV data
- `GET /fhir/CodeSystem` - Retrieve FHIR CodeSystem resources
- `GET /fhir/ConceptMap` - Retrieve mapping relationships

## 🔐 Authentication

The application uses mock ABHA OAuth 2.0 authentication:

1. Access the login endpoint: `/auth/login`
2. Get redirected to ABHA mock authentication
3. Receive JWT token for API access
4. Use token in Authorization header: `Bearer {token}`

## 📊 FHIR Compliance

The application implements these FHIR R4 resources:

- **CodeSystem**: For NAMASTE and ICD-11 TM2 terminologies
- **ConceptMap**: For mapping relationships between codes
- **Patient**: With ABHA ID integration
- **Encounter**: For coded diagnoses and clinical data

## 🧪 Testing

Run the test suite:
```bash
pytest tests/ -v
```

## 🎯 Demo Flow

1. **Authentication**: Login with ABHA credentials → receive OAuth token
2. **Search**: Enter "Prameha" → view NAMASTE + ICD-11 TM2 codes
3. **Upload**: Import NAMASTE CSV → auto-ingest as FHIR CodeSystem
4. **Translate**: Use `/translate` endpoint for code mappings
5. **Export**: Download ConceptMap as FHIR JSON

## 📈 Evaluation Criteria

- **Uniqueness**: Real-time dual coding with dynamic ConceptMap generation
- **Feasibility**: Complete API coverage with FHIR compliance
- **Impact**: Direct alignment with NDHM and Ayush digitization goals
- **Sustainability**: Scalable microservice architecture

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Commit changes: `git commit -am 'Add new feature'`
4. Push to branch: `git push origin feature/new-feature`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🔗 References

- [WHO ICD-11 API Documentation](https://icd.who.int/docs/icd-api/)
- [NAMASTE Ministry of Ayush](https://www.ayush.gov.in/)
- [FHIR R4 Specification](https://hl7.org/fhir/R4/)
- [NDHM ABHA Developer Guide](https://abdm.gov.in/abdm/developers)

## 📞 Support

For questions and support, please open an issue in the GitHub repository or contact the development team.
