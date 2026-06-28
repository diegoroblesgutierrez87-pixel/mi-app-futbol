import requests
import json

API_KEY = "TU_KEY_AQUI"  # Mete tu key aquí
HEADERS = {'x-apisports-key': API_KEY}

# Ver qué temporadas de LaLiga hay disponibles
r = requests.get("https://v3.football.api-sports.io/leagues",
                 headers=HEADERS,
                 params={'id': 140})

print("Status:", r.status_code)
print(json.dumps(r.json(), indent=2))