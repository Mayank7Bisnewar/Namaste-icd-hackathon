#!/bin/bash
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
