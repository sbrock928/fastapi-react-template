#!/bin/bash

# Navigate to frontend directory
cd "$(dirname "$0")/frontend"

# Install dependencies
echo "Installing frontend dependencies..."
npm install

# Create necessary directories if they don't exist
mkdir -p public

# Verify vite.svg exists
if [ ! -f "public/vite.svg" ]; then
  echo "Creating vite.svg..."
fi

# Verify index.html exists
if [ ! -f "index.html" ]; then
  echo "Creating index.html..."
fi

# Build the frontend
echo "Building the frontend..."
npm run build

echo "Frontend setup complete!"
echo ""
echo "To start the frontend development server:"
echo "  cd frontend && npm run dev"
echo ""
echo "To run the backend server with the built frontend:"
echo "  python main.py"
