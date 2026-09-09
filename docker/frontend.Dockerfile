# syntax=docker/dockerfile:1

# --- dev: vite dev server with HMR ------------------------------------------
FROM node:20-slim AS dev
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install
# Source is bind-mounted over this in docker-compose for live reload.
COPY frontend .
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

# --- build: production bundle -----------------------------------------------
FROM node:20-slim AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install
COPY frontend .
RUN npm run build

# --- production: nginx serving the static build -----------------------------
FROM nginx:1.27-alpine AS production
COPY docker/frontend-nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
# HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=5 \
    CMD wget -qO- http://localhost/ >/dev/null || exit 1
CMD ["nginx", "-g", "daemon off;"]
