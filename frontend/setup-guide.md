# Vibez Frontend Setup Guide

## First-time Setup

To set up the React frontend for the first time:

```bash
# Navigate to the frontend directory 
cd /Users/stephenbrock/PycharmProjects/Vibez/frontend

# Install all dependencies including TypeScript
npm install
```

If you encounter TypeScript errors, install it globally:

```bash
npm install -g typescript
```

## Running the Development Server

To run the frontend in development mode:

```bash
# Navigate to the frontend directory
cd /Users/stephenbrock/PycharmProjects/Vibez/frontend

# Start the development server
npm run dev
```

This will start the Vite development server, typically on port 5173 (http://localhost:5173).

## Building for Production

To create a production build:

```bash
# Navigate to the frontend directory
cd /Users/stephenbrock/PycharmProjects/Vibez/frontend

# Create a production build
npm run build
```

This will create a production-ready build in the `dist` directory.

## Running with FastAPI Backend

### Development Mode (separate servers)

1. Start the FastAPI backend with development mode enabled:
```bash
cd /Users/stephenbrock/PycharmProjects/Vibez
VIBEZ_DEV_MODE=true python main.py
```

2. In a separate terminal, start the Vite development server:
```bash
cd /Users/stephenbrock/PycharmProjects/Vibez/frontend
npm run dev
```

### Production Mode (single server)

1. Build the React app:
```bash
cd /Users/stephenbrock/PycharmProjects/Vibez/frontend
npm run build
```

2. Run the FastAPI server with development mode disabled:
```bash
cd /Users/stephenbrock/PycharmProjects/Vibez
python main.py
```

FastAPI will now serve both the API endpoints and the built React frontend, all from port 8000.

## Troubleshooting

If you see the error `sh: tsc: command not found` during the build process:

1. Make sure TypeScript is installed globally:
```bash
npm install -g typescript
```

2. Check if TypeScript is properly installed:
```bash
tsc --version
```

3. If needed, install TypeScript as a direct dependency:
```bash
npm install typescript --save-dev
```

You may also need to run the build using the local TypeScript installation:
```bash
npx tsc && vite build
```
