import pandas as pd
# principal
df = pd.read_csv('ligas_2122_a_2526.csv', low_memory=False)
df.to_parquet('ligas_2122_a_2526.parquet', index=False)
print("OK ligas")

# opcional
import os
if os.path.exists('laliga_2425_partidos.csv'):
    pd.read_csv('laliga_2425_partidos.csv', low_memory=False).to_parquet('laliga_2425_partidos.parquet', index=False)
    print("OK laliga partidos")
if os.path.exists('laliga_2425_goles.csv'):
    pd.read_csv('laliga_2425_goles.csv', low_memory=False).to_parquet('laliga_2425_goles.parquet', index=False)
    print("OK goles")