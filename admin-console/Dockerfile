# Stage 1: Build React app
FROM node:20-alpine AS builder

WORKDIR /app

ARG VITE_ADMIN_DEMO_TOKEN
ARG VITE_API_BASE_URL=https://curator-api.alex-n8n.site
ENV VITE_ADMIN_DEMO_TOKEN=${VITE_ADMIN_DEMO_TOKEN}
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# Stage 2: Serve static files with nginx
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
