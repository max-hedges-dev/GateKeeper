# ---------- Frontend build ----------
FROM node:18 AS frontend-build
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build   # -> /frontend/dist

# ---------- Backend runtime ----------
FROM python:3.11-slim AS app
WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Backend code
COPY backend/ ./backend/

# Frontend build placed exactly where main.py resolves it: /app/frontend/dist
# (main.py resolves ../../frontend/dist from backend/app/)
COPY --from=frontend-build /frontend/dist ./frontend/dist

EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]