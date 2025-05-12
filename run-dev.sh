#!/bin/bash
# Start both frontend and backend in development mode

# Start FastAPI backend
export VIBEZ_DEV_MODE=true
python main.py &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Start frontend
cd frontend
npm run dev &
FRONTEND_PID=$!

# Handle cleanup on exit
function cleanup {
  echo "Shutting down servers..."
  kill $FRONTEND_PID
  kill $BACKEND_PID
  exit
}

trap cleanup INT TERM

# Wait for user to press Ctrl+C
echo "Development servers running. Press Ctrl+C to stop."
wait
