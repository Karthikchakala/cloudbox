FROM node:20-alpine

WORKDIR /app

# Copy dependency manifests
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Build production bundle
RUN npm run build

# Expose Vite preview/dev server port
EXPOSE 5173

# Health check
HEALTHCHECK --interval=15s --timeout=5s --retries=3 \
    CMD wget --spider -q http://127.0.0.1:5173 || exit 1

# Start Vite preview server for production
CMD ["npm", "run", "preview", "--", "--host", "0.0.0.0", "--port", "5173"]
