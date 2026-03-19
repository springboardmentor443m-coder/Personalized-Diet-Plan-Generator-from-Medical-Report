#!/bin/bash

echo "Starting AI-NutriCare Full Stack Application..."
echo ""

echo "Starting FastAPI backend on http://localhost:8000"
cd backend
source .venv/bin/activate
python -m app.api.main &
BACKEND_PID=$!

sleep 3

echo "Starting React frontend on http://localhost:5173"
cd ../frontend
npm run dev &
FRONTEND_PID=$!

echo ""
echo "================================"
echo "AI-NutriCare is running!"
echo "================================"
echo "Backend API: http://localhost:8000"
echo "Frontend UI: http://localhost:5173"
echo ""
echo "Press Ctrl+C to stop both servers"

wait $BACKEND_PID $FRONTEND_PID
