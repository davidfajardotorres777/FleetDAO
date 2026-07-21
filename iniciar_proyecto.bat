@echo off
echo ===================================================
echo   Iniciando Servidores y Dashboard FleetDAO
echo ===================================================
echo.
echo 1. Levantando bases de datos (Mongo, Redis, MinIO)...
docker-compose up -d mongodb redis minio

echo.
echo 2. Iniciando Backend API (FastAPI)...
start "FleetDAO Backend API" cmd /k "call venv\Scripts\activate.bat && uvicorn main:app --reload --port 8000"

echo.
echo 3. Iniciando Panel Dashboard (Streamlit)...
start "FleetDAO Dashboard" cmd /k "call venv\Scripts\activate.bat && streamlit run dashboard.py"

echo.
echo ===================================================
echo ¡Todo iniciado con exito!
echo - API Docs: http://localhost:8000/docs
echo - Dashboard: http://localhost:8501
echo ===================================================
pause
