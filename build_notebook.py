import nbformat as nbf

nb = nbf.v4.new_notebook()

nb['cells'] = [
    nbf.v4.new_markdown_cell("# Análisis de Datos de FleetDAO con Pandas\n\nEste notebook utiliza **Pandas** y **Jupyter** para consumir los datos provistos por el Patrón DAO (`FleetDAO`) y transformarlos en DataFrames para un análisis avanzado, cumpliendo estrictamente con la guía del proyecto."),
    nbf.v4.new_code_cell("import pandas as pd\nimport matplotlib.pyplot as plt\nfrom dao import FleetDAO\n\n# Conectar a la base de datos a través de la capa de abstracción (DAO)\ndao = FleetDAO()\nprint('Conectado exitosamente.')"),
    nbf.v4.new_markdown_cell("## 1. Carga de Camiones en un DataFrame\nExtraemos los camiones y los convertimos en un DataFrame tabular estructurado para su análisis."),
    nbf.v4.new_code_cell("camiones = dao.get_trucks()\n\n# Convertir a Pandas DataFrame\ndf_camiones = pd.DataFrame(camiones)\n\n# Limpieza: Convertir _id a string y mostrar las primeras filas\nif not df_camiones.empty:\n    df_camiones['_id'] = df_camiones['_id'].astype(str)\n    display(df_camiones.head())\nelse:\n    print('No hay camiones registrados.')"),
    nbf.v4.new_markdown_cell("### Distribución de Marcas de Camiones\nUsando las bondades de Pandas, podemos agrupar rápidamente y visualizar."),
    nbf.v4.new_code_cell("if not df_camiones.empty:\n    marca_counts = df_camiones['brand'].value_counts()\n    \n    plt.figure(figsize=(8, 5))\n    marca_counts.plot(kind='bar', color='skyblue', edgecolor='black')\n    plt.title('Distribución de Camiones por Marca')\n    plt.xlabel('Marca')\n    plt.ylabel('Cantidad')\n    plt.xticks(rotation=45)\n    plt.grid(axis='y', linestyle='--', alpha=0.7)\n    plt.show()"),
    nbf.v4.new_markdown_cell("## 2. Análisis de Rendimiento de Conductores\nExtraemos los conductores (Drivers) para analizar la distribución de categorías de licencia."),
    nbf.v4.new_code_cell("choferes = dao.get_drivers()\ndf_choferes = pd.DataFrame(choferes)\n\nif not df_choferes.empty:\n    df_choferes['_id'] = df_choferes['_id'].astype(str)\n    \n    # Gráfico de Pastel de licencias usando Pandas nativo\n    df_choferes['license_level'].value_counts().plot(\n        kind='pie', autopct='%1.1f%%', startangle=90, figsize=(6,6),\n        colors=['#ff9999','#66b3ff','#99ff99','#ffcc99']\n    )\n    plt.title('Distribución de Niveles de Licencia')\n    plt.ylabel('')\n    plt.show()\nelse:\n    print('No hay conductores registrados.')")
]

with open('dao_consultas.ipynb', 'w', encoding='utf-8') as f:
    nbf.write(nb, f)

print("Notebook dao_consultas.ipynb actualizado exitosamente con Pandas.")
