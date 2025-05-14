FROM node:18-alpine

WORKDIR /app

# Copy package.json and install dependencies
COPY package.json .
RUN npm install

# Copy all project files necessary for the frontend
COPY tsconfig.json tsconfig.app.json tsconfig.node.json index.html ./
COPY frontend/ ./frontend/
COPY vite.config.ts ./

# Debug information
RUN echo "Checking file structure:" && \
    ls -la && \
    echo "Checking frontend directory:" && \
    ls -la ./frontend && \
    echo "Checking if index.html exists:" && \
    ls -la ./index.html

# Set environment variable for development
ENV NODE_ENV=development
# Make sure Vite picks up environment variables
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL:-http://localhost:8000}

# Expose the port (Vite default port)
EXPOSE 5173

# Command to run development server with explicit host and port configuration
CMD ["sh", "-c", "echo 'Starting Vite dev server...' && npm run dev -- --host 0.0.0.0 --port 5173"]