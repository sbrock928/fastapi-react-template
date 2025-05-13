FROM node:18-alpine

WORKDIR /app

# Copy package.json and install dependencies
COPY package.json .
RUN npm install

# Copy frontend code
COPY tsconfig.json tsconfig.app.json tsconfig.node.json ./
COPY frontend/ ./frontend/
COPY vite.config.ts ./

# Debug information
RUN echo "Checking file structure:" && \
    ls -la && \
    echo "Checking frontend directory:" && \
    ls -la ./frontend && \
    echo "Checking if main.tsx exists:" && \
    ls -la ./frontend/main.tsx

# Set environment variable for development
ENV NODE_ENV=development
# Make sure Vite picks up environment variables
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL:-http://localhost:8000}

# Expose the port (Vite default port)
EXPOSE 5173

# Command to run development server with debug output
CMD ["sh", "-c", "echo 'Starting Vite dev server...' && npm run dev"]