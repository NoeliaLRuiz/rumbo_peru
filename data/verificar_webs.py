"""Verifica qué páginas web de universidades e institutos responden de verdad.

Salida: data/webs_verificadas.csv (url_original, url_final, ok)
Uso:    python data/verificar_webs.py
"""
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests
import urllib3

urllib3.disable_warnings()  # muchas webs públicas tienen certificados vencidos
RAIZ = Path(__file__).resolve().parent.parent
CABECERAS = {"User-Agent": "Mozilla/5.0 (compatible; RumboBot/1.0; orientacion vocacional)"}


def limpiar(url: str) -> str:
    """'http:/www istpolmos.edu.pe' -> 'http://www.istpolmos.edu.pe'"""
    u = str(url or "").strip().lower().replace(" ", ".")
    if not u or "geocities" in u or "." not in u:
        return ""
    u = re.sub(r"^https?:/*", "", u)
    return "http://" + u.strip("/.")


def probar(url: str) -> tuple[str, str, bool]:
    for intento in (url, url.replace("http://", "https://")):
        try:
            r = requests.get(intento, headers=CABECERAS, timeout=12, verify=False, allow_redirects=True)
            if r.status_code < 400:
                return url, r.url, True
        except requests.RequestException:
            pass
    return url, "", False


def main():
    uni = pd.read_csv(RAIZ / "data" / "webs_universidades.csv", dtype=str)["web"]
    padron = pd.read_csv(RAIZ / "data" / "oferta.csv", keep_default_na=False)["web"]
    urls = sorted({u for u in list(uni) + [limpiar(w) for w in padron] if u})
    print(f"Probando {len(urls)} páginas...")
    with ThreadPoolExecutor(max_workers=24) as ex:
        res = list(ex.map(probar, urls))
    df = pd.DataFrame(res, columns=["url_original", "url_final", "ok"])
    df.to_csv(RAIZ / "data" / "webs_verificadas.csv", index=False)
    print(f"{df['ok'].sum()} de {len(df)} responden")
    print(df[~df["ok"]]["url_original"].tolist())


if __name__ == "__main__":
    main()
