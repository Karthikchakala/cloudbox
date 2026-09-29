FROM nginx:1.27-alpine

# Install openssl for cert generation and curl for container health check
RUN apk add --no-cache openssl curl

# Create directory for SSL certificates
RUN mkdir -p /etc/nginx/certs

# Generate self-signed fallback certificate for HTTPS development testing
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/certs/key.pem \
    -out /etc/nginx/certs/cert.pem \
    -subj "/C=US/ST=State/L=City/O=CloudBox/OU=Engineering/CN=localhost"

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/default.conf /etc/nginx/conf.d/default.conf

# Expose HTTP (80) and HTTPS (443)
EXPOSE 80 443

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]
