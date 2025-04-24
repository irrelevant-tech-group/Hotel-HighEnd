# Use Node.js as base image for frontend build
FROM node:18-alpine AS frontend-build

# Set working directory for frontend
WORKDIR /app/frontend

# Copy frontend files
COPY Front_Hotel/package*.json ./
RUN npm install
RUN ls -la
COPY Front_Hotel/ .

# Build frontend
RUN npm run build

# Use Python 3.11 slim image as base for backend
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    FLASK_ENV=production \
    DATABASE_URL=sqlite:///hotel.db \
    TZ=America/Bogota

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    tzdata \
    nginx \
    && rm -rf /var/lib/apt/lists/* \
    && ln -fs /usr/share/zoneinfo/America/Bogota /etc/localtime \
    && dpkg-reconfigure -f noninteractive tzdata

# Create Nginx directories
RUN mkdir -p /var/lib/nginx/body /var/lib/nginx/proxy /var/lib/nginx/fastcgi /var/lib/nginx/uwsgi /var/lib/nginx/scgi

# Copy requirements file
COPY Hotel-HighEnd/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p instance data

# Copy backend files
COPY Hotel-HighEnd/ .

# Copy frontend build from previous stage
COPY --from=frontend-build /app/frontend/build /app/frontend/build

# Copy nginx configuration
COPY Hotel-HighEnd/nginx.conf /etc/nginx/conf.d/default.conf

# Create a script to start both services
COPY Hotel-HighEnd/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Expose port
EXPOSE 8000
EXPOSE 8001

# Start both nginx and gunicorn
CMD ["/app/start.sh"] 