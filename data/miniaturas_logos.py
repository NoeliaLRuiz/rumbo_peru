"""Crea miniaturas cuadradas de los logos para que se vean completos (sin cortarse) en la app.

Para cada logo de data/logos.csv:
  1. lo descarga,
  2. recorta los bordes vacíos (transparentes o blancos),
  3. lo centra, completo y sin deformar, en un cuadrado blanco de 128 x 128 con margen.
Los logos en SVG (vectoriales) se dejan como están: el navegador ya los ajusta sin cortarlos.

Salida: data/logos_mini.csv (codigo, logo_mini) con la imagen en formato data:image/png;base64.
Uso:    python data/miniaturas_logos.py
"""
import base64
import io
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests
import urllib3
from PIL import Image, ImageChops

urllib3.disable_warnings()
RAIZ = Path(__file__).resolve().parent.parent
CABECERAS = {"User-Agent": "RumboBot/1.0 (orientacion vocacional; proyecto academico)"}
LADO, MARGEN = 128, 10


def recortar_bordes(img: Image.Image) -> Image.Image:
    """Quita el espacio vacío alrededor del logo (transparente o blanco)."""
    fondo = Image.new("RGBA", img.size, (255, 255, 255, 0))
    caja = ImageChops.difference(img, fondo).getbbox()          # bordes transparentes
    blanco = Image.new("RGB", img.size, (255, 255, 255))
    plano = Image.alpha_composite(Image.new("RGBA", img.size, (255, 255, 255, 255)), img).convert("RGB")
    caja_blanca = ImageChops.difference(plano, blanco).getbbox()  # bordes blancos
    caja = caja_blanca or caja
    return img.crop(caja) if caja else img


def miniatura(item: tuple[str, str]) -> tuple[str, str]:
    codigo, url = item
    if url.lower().split("?")[0].endswith(".svg"):
        return codigo, ""
    try:
        r = requests.get(url, headers=CABECERAS, timeout=15, verify=False)
        img = Image.open(io.BytesIO(r.content))
        img.seek(0)  # .ico o gif: primer cuadro
        img = recortar_bordes(img.convert("RGBA"))
        img.thumbnail((LADO - 2 * MARGEN, LADO - 2 * MARGEN), Image.LANCZOS)
        lienzo = Image.new("RGBA", (LADO, LADO), (255, 255, 255, 255))
        lienzo.alpha_composite(img, ((LADO - img.width) // 2, (LADO - img.height) // 2))
        salida = io.BytesIO()
        lienzo.convert("RGB").save(salida, format="PNG", optimize=True)
        return codigo, "data:image/png;base64," + base64.b64encode(salida.getvalue()).decode()
    except Exception:
        return codigo, ""


def main():
    logos = pd.read_csv(RAIZ / "data" / "logos.csv", dtype=str).dropna(subset=["logo"])
    print(f"Creando miniaturas de {len(logos)} logos...")
    with ThreadPoolExecutor(max_workers=16) as ex:
        res = list(ex.map(miniatura, zip(logos["codigo"], logos["logo"])))
    df = pd.DataFrame(res, columns=["codigo", "logo_mini"])
    df = df[df["logo_mini"] != ""]
    df.to_csv(RAIZ / "data" / "logos_mini.csv", index=False)
    print(f"Miniaturas creadas: {len(df)} (los SVG se usan tal cual)")


if __name__ == "__main__":
    main()
