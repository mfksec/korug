# Build stage
FROM node:18-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Runtime stage
FROM node:18-alpine

WORKDIR /app

# Install a simple static server
RUN npm install -g serve

# Copy built application from builder
COPY --from=builder /app/dist ./dist

# Set environment variable
ENV VITE_API_BASE_URL=http://localhost:8000

EXPOSE 3000

# Serve the application
CMD ["serve", "-s", "dist", "-l", "3000"]
