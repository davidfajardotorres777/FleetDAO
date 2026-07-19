# FleetDAO
Sistema de Gestion de Flotas

Autor: Alesandro David Fajardo Torres
Materia: Bases de Datos II - Proyecto Integrador 2026

---

## 1. Introduccion

Las empresas de logistica suelen tener problemas para controlar los gastos de sus flotas. El costo mas grande que tienen es el combustible y arreglar los camiones cuando se rompen. Muchos sistemas de GPS actuales solo muestran donde esta el camion, pero no analizan si el chofer lo esta manejando mal o si el motor esta levantando temperatura de mas.

Mi proyecto, FleetDAO, busca solucionar esto. Es un sistema para recibir datos de los camiones, guardarlos de forma segura y analizarlos para ayudar a prevenir problemas mecanicos antes de que pasen.

## 2. Herramientas que use

Para que el proyecto funcione bien, use estas herramientas:

*   MongoDB (4.4): Es la base de datos principal. Use indices geoespaciales (2dsphere) para hacer consultas basadas en la ubicacion.
*   FastAPI: Para hacer la API que recibe los datos de los sensores del camion.
*   Pydantic: Para crear los modelos de datos y validar que la informacion este correcta antes de guardarla.
*   Jupyter Notebook: Lo use junto con folium para los mapas y matplotlib para hacer graficos comparando la velocidad con la temperatura del motor.

## 3. Como funciona

El funcionamiento basico es este:
1. El camion manda los datos de ubicacion, velocidad y temperatura por JSON.
2. FastAPI y Pydantic reciben los datos y los validan.
3. El archivo dao.py los guarda en MongoDB.
4. Para analizar los datos, uso Aggregation Pipelines de MongoDB ($group, $avg, $max) para sacar el promedio de velocidad y ver si hay temperaturas muy altas.
5. Todo esto se puede visualizar en el Jupyter Notebook con los mapas y los graficos.

---

## 4. Archivos del proyecto

FleetDAO/
- db_models/: Modelos de Pydantic para validar datos (choferes, rutas, telemetria, camiones).
- dao.py: Clase principal para interactuar con la base de datos.
- config_vars.py: Archivo para configurar las variables de entorno.
- main.py: La API de FastAPI.
- seed.py: Script para cargar los datos de prueba y poder probar el sistema.
- make_nb.py: Script que uso para generar el Notebook con todos los graficos.
- demo.ipynb: El Notebook para ver los analisis y los mapas.
- docker-compose.yml: Archivo para levantar la base de datos localmente.
- libs.txt: Las librerias de python necesarias.

---

## 5. Como correr el proyecto

Primero que nada hay que instalar Python y tener Docker andando.

Pasos:
1. Bajar el repositorio.
2. Crear un entorno virtual de python e instalar las cosas que estan en libs.txt (pip install -r libs.txt).
3. Armar un archivo .env que tenga la configuracion (MONGO_URI=mongodb://localhost:27017 y DB_NAME=fleet_management).
4. Levantar la base de datos corriendo "docker-compose up -d".
5. Correr el archivo "seed.py" (python seed.py) para que la base de datos se llene con datos de prueba.
6. Correr el archivo "make_nb.py" y despues abrir el jupyter notebook para ver todos los resultados, o abrir directo el archivo demo.html en el navegador.
