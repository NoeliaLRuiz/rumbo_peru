"""Busca la web oficial de escuelas e institutos pedagógicos probando los dominios más comunes.

Ejemplo: 'Emilia Barcia Boniffatti' -> eesppemiliabarciaboniffatti.edu.pe, emiliabarcia.edu.pe, ...
Solo acepta una web si responde Y su página menciona el nombre de la escuela (evita falsos positivos).
Las que se encuentran se agregan a mano en data/correcciones_manuales.csv tras revisarlas.

Uso: python data/buscar_webs_escuelas.py
"""
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests
import urllib3

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from ai.areas import normalizar  # noqa: E402

urllib3.disable_warnings()
CABECERAS = {"User-Agent": "RumboBot/1.0 (orientacion vocacional; proyecto academico)"}
VACIAS = {"DE", "DEL", "LA", "EL", "LOS", "LAS", "Y", "SAN", "SANTA", "NUESTRA", "SENORA", "MONSENOR"}
PREFIJOS = ["eespp", "eesp", "iesp", "iespp", "isp", "ispp", "eespp-", "iesp-", ""]


def slugs(nombre: str) -> list[str]:
    palabras = re.sub(r"[^A-Z ]", " ", normalizar(nombre)).split()
    utiles = [w for w in palabras if w not in VACIAS] or palabras
    opciones = {"".join(palabras), "".join(utiles), utiles[0], "".join(utiles[:2]), "".join(w[0] for w in palabras)}
    return [s.lower() for s in opciones if len(s) >= 3]


def menciona(html: str, nombre: str) -> bool:
    texto = normalizar(re.sub(r"<[^>]+>", " ", html))
    claves = [w for w in normalizar(nombre).split() if w not in VACIAS and len(w) > 3] or normalizar(nombre).split()
    return all(c in texto for c in claves[:2])


def probar(item):
    codigo, nombre = item
    for slug in slugs(nombre):
        for pref in PREFIJOS:
            for url in (f"https://www.{pref}{slug}.edu.pe/", f"https://{pref}{slug}.edu.pe/"):
                try:
                    r = requests.get(url, headers=CABECERAS, timeout=8, verify=False)
                except requests.RequestException:
                    continue
                if r.status_code < 400 and menciona(r.text, nombre):
                    return codigo, nombre, r.url
    return codigo, nombre, ""


def main():
    o = pd.read_csv(RAIZ / "data" / "oferta.csv")
    e = o[o["tipo"].str.contains("pedagóg") & o["web"].isna()].drop_duplicates("codigo")
    print(f"Probando dominios para {len(e)} escuelas e institutos pedagógicos...")
    with ThreadPoolExecutor(max_workers=24) as ex:
        res = list(ex.map(probar, zip(e["codigo"], e["nombre_corto"])))
    df = pd.DataFrame(res, columns=["codigo", "nombre", "web"])
    df.to_csv(RAIZ / "data" / "webs_candidatas_pedagogicas.csv", index=False)
    print(df[df["web"] != ""].to_string())
    print(f"Encontradas: {(df['web'] != '').sum()} de {len(df)}")


if __name__ == "__main__":
    main()
