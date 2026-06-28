import pandas as pd
# IMPORTA TUS FUNCIONES (cambia 'app' por el nombre de tu archivo .py sin extensión)
from app import cargar_csv, calcular_estado_jornada

df = cargar_csv()
df_final, _ = calcular_estado_jornada(df)
df_final.to_parquet('df_final_procesado.parquet', index=False)
print("Hecho - ya puedes borrar este archivo")