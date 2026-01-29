# AuditEng V2 Frontend Dockerfile
# Build stage
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build argument for API URL (can be overridden at build time)
ARG VITE_API_URL
ENV VITE_API_URL=$VITE_API_URL

# Build the application
RUN npm run build

# Production stage with nginx
FROM nginx:alpine

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from builder stage (Vite outputs to 'build' folder)
COPY --from=builder /app/build /usr/share/nginx/html

# Create startup script inline (avoids Windows line ending issues)
RUN printf '#!/bin/sh\nPORT=${PORT:-80}\nsed -i "s/listen 80;/listen $PORT;/" /etc/nginx/conf.d/default.conf\necho "Starting nginx on port $PORT"\nexec nginx -g "daemon off;"\n' > /start.sh && chmod +x /start.sh

# Default port
ENV PORT=80

# Expose port
EXPOSE 80

# Start with script that handles PORT variable
CMD ["/start.sh"]
