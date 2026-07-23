@echo off
echo ===================================================
echo   Abriendo Jupyter Notebook para el Examen
echo ===================================================
echo.
call venv\Scripts\activate.bat
jupyter notebook dao_consultas.ipynb
pause
