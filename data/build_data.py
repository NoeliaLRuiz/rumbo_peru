"""Construye data/oferta.csv: toda la oferta de educación superior del Perú en una tabla.

Fuentes (datos abiertos, sin datos personales):
  1. SUNEDU - Programas de universidades licenciadas (datosabiertos.gob.pe)
  2. MINEDU - Censo Educativo 2025, cuadro de carreras de institutos y CETPRO (ESCALE)
  3. MINEDU - Padrón de instituciones educativas 2025 (ESCALE): gestión pública/privada y coordenadas

Uso:  python data/build_data.py
"""
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests
from dbfread import DBF

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from ai.areas import clasificar, normalizar  # noqa: E402

RAW = RAIZ / "data" / "raw"
ESCALE = "https://escale.minedu.gob.pe/documents/inicio/Bases%20de%20datos/A.%20Censo%20Educativo/2025/"
FUENTES = {
    "sunedu_programas.csv": "https://www.datosabiertos.gob.pe/sites/default/files/Programas%20de%20Universidades_8.csv",
    "47_Carreras.zip": ESCALE + "47_Carreras.zip",
    "00_Padron.zip": ESCALE + "00_Padron.zip",
}
TIPOS_IES = {
    "T0": "Instituto tecnológico",
    "K0": "Instituto / escuela pedagógica",
    "M0": "Escuela de arte",
    "L0": "CETPRO (técnico-productiva)",
}


def descargar():
    RAW.mkdir(parents=True, exist_ok=True)
    for nombre, url in FUENTES.items():
        destino = RAW / nombre
        if destino.exists():
            continue
        print(f"Descargando {nombre} ...")
        r = requests.get(url, timeout=600)
        r.raise_for_status()
        destino.write_bytes(r.content)
        if nombre.endswith(".zip"):
            zipfile.ZipFile(destino).extractall(RAW)


def universidades() -> pd.DataFrame:
    u = pd.read_csv(RAW / "sunedu_programas.csv", sep="|", encoding="latin-1", dtype=str)
    u = u[u["TIPO_NIVEL_ACADEMICO"] == "PREGRADO"]  # solo carreras profesionales
    return pd.DataFrame({
        "institucion": u["NOMBRE"].str.title(),
        "tipo": "Universidad",
        "gestion": u["TIPO_GESTION"].map(lambda g: "Pública" if normalizar(g).startswith("PUBLIC") else "Privada"),
        "programa": u["DENOMINACION_PROGRAMA"].str.strip(),
        "familia": u["NOMBRE_CLASE_PROGRAMA_N2"],
        "departamento": u["DEPARTAMENTO_LOCAL"],
        "provincia": u["PROVINCIA_LOCAL"],
        "distrito": u["DISTRITO_LOCAL"],
        "lat": pd.to_numeric(u["LATITUD_UBICACION"], errors="coerce"),
        "lon": pd.to_numeric(u["LONGITUD_UBICACION"], errors="coerce"),
        "web": "",
        "fuente": "SUNEDU",
    })


def institutos() -> pd.DataFrame:
    campos = ["COD_MOD", "CEN_EDU", "NIV_MOD", "GESTION", "D_DPTO", "D_PROV", "D_DIST",
              "NLAT_IE", "NLONG_IE", "PAGWEB"]
    filas = [{k: r[k] for k in campos}
             for r in DBF(RAW / "Padron.dbf", encoding="cp850")
             if r["NIV_MOD"] in TIPOS_IES]
    padron = pd.DataFrame(filas)

    carreras = pd.DataFrame(iter(DBF(RAW / "Carreras.dbf", encoding="cp850")))
    carreras = carreras[["COD_MOD", "DESCRIP"]].drop_duplicates()
    carreras = carreras[carreras["DESCRIP"].str.strip().ne("") & carreras["DESCRIP"].ne("OTROS")]

    m = padron.merge(carreras, on="COD_MOD", how="left")
    # Los pedagógicos no reportan carreras en este cuadro del censo: se listan como formación docente.
    sin_carrera = m["DESCRIP"].isna()
    m.loc[sin_carrera & (m["NIV_MOD"] == "K0"), "DESCRIP"] = "FORMACIÓN DOCENTE (consultar especialidades)"
    m = m.dropna(subset=["DESCRIP"])

    return pd.DataFrame({
        "institucion": m["CEN_EDU"].str.title(),
        "tipo": m["NIV_MOD"].map(TIPOS_IES),
        # GESTION: 1 = pública de gestión directa, 2 = pública de gestión privada, 3 = privada
        "gestion": m["GESTION"].map({"1": "Pública", "2": "Pública", "3": "Privada"}).fillna("Privada"),
        "programa": m["DESCRIP"].str.strip(),
        "familia": "",
        "departamento": m["D_DPTO"],
        "provincia": m["D_PROV"],
        "distrito": m["D_DIST"],
        "lat": pd.to_numeric(m["NLAT_IE"], errors="coerce"),
        "lon": pd.to_numeric(m["NLONG_IE"], errors="coerce"),
        "web": m["PAGWEB"].fillna(""),
        "fuente": "MINEDU",
    })


def main():
    descargar()
    oferta = pd.concat([universidades(), institutos()], ignore_index=True)
    oferta["programa"] = oferta["programa"].str.upper()
    oferta["area"] = [clasificar(p, f) for p, f in zip(oferta["programa"], oferta["familia"])]
    for col in ["departamento", "provincia", "distrito"]:
        oferta[col] = oferta[col].str.upper().str.strip()
    # Coordenadas fuera del Perú = dato faltante
    fuera = ~oferta["lat"].between(-18.5, 0.1) | ~oferta["lon"].between(-81.5, -68.5)
    oferta.loc[fuera, ["lat", "lon"]] = None
    oferta = oferta.drop(columns="familia").drop_duplicates()
    oferta.to_csv(RAIZ / "data" / "oferta.csv", index=False, encoding="utf-8")

    print(f"{len(oferta):,} filas")
    print(oferta.groupby(["tipo", "gestion"]).size().to_string())
    print(oferta["area"].value_counts().to_string())


if __name__ == "__main__":
    main()
