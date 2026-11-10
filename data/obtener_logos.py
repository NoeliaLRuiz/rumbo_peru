"""Obtiene el logo de cada institución desde su página web oficial (scraping, sesión 03 del curso).

Para cada web verificada lee la portada y busca, en este orden:
  1. una imagen <img> de "logo" que lleve el nombre de la institución (p. ej. Logo-Monterrico.png),
     descartando logos ajenos (ministerios, redes sociales, banners)
  2. el ícono para celulares (<link rel="apple-touch-icon">), que suele ser el escudo o logo cuadrado
  3. el ícono del sitio (<link rel="icon">) o /favicon.ico
  4. la imagen para redes sociales (<meta property="og:image">)
Solo guarda la imagen si de verdad descarga, es una imagen y no es un logo blanco
(los logos blancos, hechos para fondos oscuros, no se ven sobre el fondo blanco de la app).

Salida: data/logos.csv (codigo, logo, metodo)
Uso:    python data/obtener_logos.py
"""
import io
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
import urllib3
from bs4 import BeautifulSoup
from PIL import Image

urllib3.disable_warnings()  # muchas webs públicas tienen certificados vencidos
RAIZ = Path(__file__).resolve().parent.parent
CABECERAS = {"User-Agent": "RumboBot/1.0 (orientacion vocacional; proyecto academico)"}


def es_imagen(url: str) -> bool:
    """La URL descarga una imagen de verdad y no es un logo blanco (invisible sobre fondo blanco)."""
    try:
        r = requests.get(url, headers=CABECERAS, timeout=12, verify=False, stream=True)
        tipo = r.headers.get("content-type", "")
        contenido = r.raw.read(300_000, decode_content=True)
        ok = r.status_code < 400 and ("image" in tipo or url.lower().endswith(".svg")) and len(contenido) > 150
        return ok and not es_blanco(contenido, "svg" in tipo or url.lower().endswith(".svg"))
    except requests.RequestException:
        return False


def es_blanco(contenido: bytes, es_svg: bool) -> bool:
    """Detecta logos casi blancos (pensados para fondos oscuros), como el de San Marcos."""
    if es_svg:
        texto = contenido.decode("utf-8", "ignore").lower()
        colores = re.findall(r"""(?:fill|stroke)\s*[:=]\s*["']?\s*(#[0-9a-f]{3,6}|white|rgb\([^)]*\))""", texto)
        if not colores:
            return False
        blancos = {"#fff", "#ffffff", "white", "#fefefe", "#fdfdfd", "rgb(255,255,255)", "rgb(255, 255, 255)"}
        return sum(c in blancos for c in colores) / len(colores) > 0.8
    try:
        img = Image.open(io.BytesIO(contenido)).convert("RGBA")
        img.thumbnail((64, 64))
        visibles = [(r, g, b) for r, g, b, a in img.getdata() if a > 40]
        if not visibles:
            return True
        brillo = sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b in visibles) / len(visibles)
        return brillo > 238
    except Exception:
        return False


# Imágenes que dicen "logo" pero no son de la institución
AJENAS = ("ministerio", "minedu", "gob.pe", "sunedu", "bicentenario", "marca-peru", "marcaperu", "facebook",
          "whatsapp", "instagram", "youtube", "tiktok", "twitter", "linkedin", "reclamaciones", "transparencia",
          "visa", "mastercard", "google", "android", "appstore", "banner", "sineace", "pronabec")


def puntaje_img(img, dominio: str) -> int:
    """Más puntos si la imagen parece el logo propio de la institución."""
    texto = " ".join(str(img.get(a, "")) for a in ("src", "data-src", "alt", "class", "id")).lower()
    padre = " ".join(str(x) for x in (img.parent.get("class") or [])).lower() if img.parent else ""
    if "logo" not in texto and "logo" not in padre and "brand" not in padre:
        return -99
    if any(a in texto for a in AJENAS):
        return -99
    puntos = 0
    if dominio and dominio in texto:              # p. ej. 'monterrico' en Logo-Monterrico-1.png
        puntos += 4
    if any(k in padre for k in ("logo", "brand", "header")) or "custom-logo" in texto:
        puntos += 2
    return puntos


def candidatos(web: str) -> list[tuple[str, str]]:
    r = requests.get(web, headers=CABECERAS, timeout=15, verify=False)
    sopa = BeautifulSoup(r.text, "html.parser")
    base = r.url
    partes = urlparse(base).netloc.lower().replace("www.", "").split(".")
    dominio = partes[0] if partes and len(partes[0]) >= 3 else ""

    imgs = []
    for img in sopa.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if src and not src.startswith("data:"):
            imgs.append((puntaje_img(img, dominio), urljoin(base, src)))
    imgs = sorted((x for x in imgs if x[0] >= 0), key=lambda x: -x[0])

    iconos = []
    for link in sopa.find_all("link"):
        rels = " ".join(link.get("rel", [])).lower()
        if link.get("href") and rels in ("apple-touch-icon", "icon", "shortcut icon"):
            iconos.append((urljoin(base, link["href"]), "apple-touch-icon" if "apple" in rels else "icon"))
    iconos.sort(key=lambda x: x[1] != "apple-touch-icon")

    res = []
    if imgs and imgs[0][0] >= 4:                  # logo con el nombre de la institución: el mejor
        res.append((imgs[0][1], "img-logo"))
    res += [i for i in iconos if i[1] == "apple-touch-icon"]
    res += [(u, "img-logo") for puntos, u in imgs if (u, "img-logo") not in res][:2]
    res += [i for i in iconos if i[1] == "icon"]
    res.append((urljoin(base, "/favicon.ico"), "favicon"))
    og = sopa.find("meta", attrs={"property": "og:image"})
    if og and og.get("content"):
        res.append((urljoin(base, og["content"]), "og-image"))
    return res


def logo_de(item: tuple[str, str]) -> tuple[str, str, str]:
    codigo, web = item
    try:
        for url, metodo in candidatos(web):
            if "gob.pe/assets" in url:            # ícono genérico del Estado, no de la institución
                continue
            if es_imagen(url):
                return codigo, url, metodo
    except requests.RequestException:
        pass
    return codigo, "", "sin logo"


def main():
    o = pd.read_csv(RAIZ / "data" / "oferta.csv", dtype={"codigo": str})
    webs = o.dropna(subset=["web"]).drop_duplicates("codigo")[["codigo", "web"]]
    print(f"Buscando logos en {len(webs)} webs...")
    with ThreadPoolExecutor(max_workers=16) as ex:
        res = list(ex.map(logo_de, webs.itertuples(index=False, name=None)))
    df = pd.DataFrame(res, columns=["codigo", "logo", "metodo"])
    df.to_csv(RAIZ / "data" / "logos.csv", index=False)
    print(df["metodo"].value_counts().to_string())


if __name__ == "__main__":
    main()
