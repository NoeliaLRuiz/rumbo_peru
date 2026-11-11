"""Construye data/oferta.csv: toda la oferta de educación superior del Perú en una tabla.

Fuentes (datos abiertos, sin datos personales):
  1. SUNEDU - Programas de universidades licenciadas (datosabiertos.gob.pe)
  2. MINEDU - Censo Educativo 2025, cuadro de carreras de institutos y CETPRO (ESCALE)
  3. MINEDU - Padrón de instituciones educativas 2025 (ESCALE): gestión pública/privada y coordenadas

Uso:  python data/build_data.py
"""
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests
from dbfread import DBF

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from ai.areas import clasificar, normalizar  # noqa: E402
from data.verificar_webs import limpiar  # noqa: E402

RAW = RAIZ / "data" / "raw"
ESCALE = "https://escale.minedu.gob.pe/documents/inicio/Bases%20de%20datos/A.%20Censo%20Educativo/2025/"
FUENTES = {
    "sunedu_programas.csv": "https://www.datosabiertos.gob.pe/sites/default/files/Programas%20de%20Universidades_8.csv",
    "47_Carreras.zip": ESCALE + "47_Carreras.zip",
    "00_Padron.zip": ESCALE + "00_Padron.zip",
}
TIPOS_IES = {
    "T0": "Instituto tecnológico",
    "S0": "Escuela superior tecnológica (EEST)",   # Ley 30512
    "K0": "Instituto pedagógico",
    "P0": "Escuela superior pedagógica (EESP)",    # Ley 30512 (p. ej. Monterrico)
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


def webs_ok() -> dict[str, str]:
    """URLs que respondieron en data/verificar_webs.py -> URL final (después de redirecciones)."""
    archivo = RAIZ / "data" / "webs_verificadas.csv"
    if not archivo.exists():
        return {}
    v = pd.read_csv(archivo, keep_default_na=False)
    v = v[v["ok"].astype(str) == "True"]
    return dict(zip(v["url_original"], v["url_final"]))


def webs_universidades() -> dict[str, str]:
    """Código SUNEDU -> web oficial, solo si respondió o fue verificada a mano."""
    w = pd.read_csv(RAIZ / "data" / "webs_universidades.csv", dtype=str)
    ok = webs_ok()
    w = w[w["web"].isin(ok.keys()) | (w["verificado_manual"] == "True")]
    return dict(zip(w["codigo"], w["web"]))


MINUSCULAS = {"de", "del", "la", "las", "el", "los", "y", "e", "en", "para", "con", "a"}


SIGLAS = {"SENATI", "ISIL", "IDAT", "SISE", "ADEX", "ISAM", "TECSUP", "SENCICO", "IPAE", "CEPEA", "ESAN", "UTEC",
          "UCAL", "UPC", "USIL", "UNI", "SAC", "S.A.C.", "S.A.", "S.R.L.", "EIRL", "E.I.R.L.", "II", "III", "IV", "XXI"}


def titulo(nombre: str) -> str:
    """'UNIVERSIDAD NACIONAL MAYOR DE SAN MARCOS' -> 'Universidad Nacional Mayor de San Marcos'
    (conectores en minúscula y siglas conocidas en mayúscula)."""
    palabras = []
    for i, w in enumerate(str(nombre).strip().split()):
        if w.upper() in SIGLAS:
            palabras.append(w.upper())
        elif i > 0 and w.lower() in MINUSCULAS:
            palabras.append(w.lower())
        else:
            palabras.append(w.capitalize())
    return " ".join(palabras)


# Nombre oficial según la Ley 30512 y la Ley General de Educación (el padrón solo trae el nombre corto)
PREFIJOS = {
    "P0": ("Escuela de Educación Superior Pedagógica", "Pública", "Privada"),
    "S0": ("Escuela de Educación Superior Tecnológica", "Pública", "Privada"),
    "K0": ("Instituto de Educación Superior Pedagógico", "Público", "Privado"),
    "T0": ("Instituto de Educación Superior Tecnológico", "Público", "Privado"),
    "M0": ("Escuela Superior de Formación Artística", "Pública", "Privada"),
    "L0": ("CETPRO", "", ""),
}


def nombre_oficial(niv_mod: str, gestion: str, cen_edu: str) -> str:
    """'P0', '2', 'MONTERRICO' -> 'Escuela de Educación Superior Pedagógica Pública Monterrico'"""
    corto = titulo(cen_edu)
    if normalizar(cen_edu).startswith(("ESCUELA", "INSTITUTO", "CETPRO", "CENTRO", "UNIVERSIDAD", "CONSERVATORIO")):
        return corto
    prefijo, pub, pri = PREFIJOS.get(niv_mod, ("", "", ""))
    tipo_gestion = pub if gestion in ("1", "2") else pri
    return " ".join(x for x in (prefijo, tipo_gestion, corto) if x)


def correcciones_manuales(oferta: pd.DataFrame) -> pd.DataFrame:
    """Correcciones verificadas a mano (data/correcciones_manuales.csv): nombre oficial y web por código."""
    c = pd.read_csv(RAIZ / "data" / "correcciones_manuales.csv", dtype=str).set_index("codigo")
    for codigo, fila in c.iterrows():
        sel = oferta["codigo"] == codigo
        if isinstance(fila["nombre"], str):
            oferta.loc[sel, "institucion"] = fila["nombre"]
        if isinstance(fila["web"], str):
            oferta.loc[sel, "web"] = fila["web"]
    return oferta


def instituciones_extra() -> pd.DataFrame:
    """Instituciones públicas que no están en SUNEDU ni en el padrón MINEDU (p. ej. escuelas nacionales
    de arte con rango universitario). Fuente: su web oficial y el pliego Educación en Transparencia MEF."""
    e = pd.read_csv(RAIZ / "data" / "instituciones_extra.csv", dtype=str)
    e["lat"] = pd.to_numeric(e["lat"], errors="coerce")
    e["lon"] = pd.to_numeric(e["lon"], errors="coerce")
    e["nombre_corto"] = e["institucion"]
    e["familia"] = ""
    return e


def universidades() -> pd.DataFrame:
    u = pd.read_csv(RAW / "sunedu_programas.csv", sep="|", encoding="latin-1", dtype=str)
    u = u[u["TIPO_NIVEL_ACADEMICO"] == "PREGRADO"]  # solo carreras profesionales
    return pd.DataFrame({
        "institucion": u["NOMBRE"].map(titulo),
        "nombre_corto": u["NOMBRE"].map(titulo),
        "codigo": "SUNEDU-" + u["CODIGO_ENTIDAD"],
        "tipo": "Universidad",
        "gestion": u["TIPO_GESTION"].map(lambda g: "Pública" if normalizar(g).startswith("PUBLIC") else "Privada"),
        "programa": u["DENOMINACION_PROGRAMA"].str.strip(),
        "familia": u["NOMBRE_CLASE_PROGRAMA_N2"],
        "departamento": u["DEPARTAMENTO_LOCAL"],
        "provincia": u["PROVINCIA_LOCAL"],
        "distrito": u["DISTRITO_LOCAL"],
        "lat": pd.to_numeric(u["LATITUD_UBICACION"], errors="coerce"),
        "lon": pd.to_numeric(u["LONGITUD_UBICACION"], errors="coerce"),
        "web": u["CODIGO_ENTIDAD"].map(webs_universidades()).fillna(""),
        "fuente": "SUNEDU",
        "certificacion": "Grado de Bachiller y Título Profesional (Ley Universitaria 30220)",
        # SUNEDU otorga la licencia por 6, 8 o 10 años según la calidad demostrada (indicador de prestigio)
        "licencia_anios": pd.to_numeric(u["PERIODO_LICENCIAMIENTO"], errors="coerce"),
        "duracion": u["DENOMINACION_PROGRAMA"].map(
            lambda p: "7 años" if normalizar(p).startswith("MEDICINA HUMANA") else "5 años aprox."),
    })


def institutos() -> pd.DataFrame:
    campos = ["COD_MOD", "CEN_EDU", "NIV_MOD", "GESTION", "D_DPTO", "D_PROV", "D_DIST",
              "NLAT_IE", "NLONG_IE", "PAGWEB"]
    filas = [{k: r[k] for k in campos}
             for r in DBF(RAW / "Padron.dbf", encoding="latin-1")
             if r["NIV_MOD"] in TIPOS_IES]
    padron = pd.DataFrame(filas)

    carreras = pd.DataFrame(iter(DBF(RAW / "Carreras.dbf", encoding="cp850")))
    carreras = carreras[["COD_MOD", "DESCRIP", "CUADRO", "DURACION", "NHORAS"]].drop_duplicates(["COD_MOD", "DESCRIP"])
    carreras = carreras[carreras["DESCRIP"].str.strip().ne("") & carreras["DESCRIP"].ne("OTROS")]

    m = padron.merge(carreras, on="COD_MOD", how="left")
    # Los pedagógicos no reportan carreras en este cuadro del censo: se listan como formación docente.
    sin_carrera = m["DESCRIP"].isna()
    m.loc[sin_carrera & m["NIV_MOD"].isin(["K0", "P0"]), "DESCRIP"] = "EDUCACIÓN - FORMACIÓN DOCENTE (consultar especialidades)"
    # El resto de instituciones activas que no reportó carreras en el censo (p. ej. SENATI, Cibertec):
    # se incluyen igual, para que aparezcan en el mapa y en la búsqueda por nombre.
    m["DESCRIP"] = m["DESCRIP"].fillna("OFERTA NO REPORTADA EN EL CENSO (consultar su web)")

    return pd.DataFrame({
        "institucion": [nombre_oficial(n, g, c) for n, g, c in zip(m["NIV_MOD"], m["GESTION"], m["CEN_EDU"])],
        "nombre_corto": m["CEN_EDU"].map(titulo),
        "codigo": "MINEDU-" + m["COD_MOD"],
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
        "web": m["PAGWEB"].fillna("").map(lambda w: webs_ok().get(limpiar(w), "")),
        "fuente": "MINEDU",
        "certificacion": [certificacion_ies(n, c) for n, c in zip(m["NIV_MOD"], m["CUADRO"])],
        "duracion": [duracion_ies(n, d, h) for n, d, h in zip(m["NIV_MOD"], m["DURACION"], m["NHORAS"])],
    })


def certificacion_ies(niv_mod: str, cuadro) -> str:
    """Qué obtiene el egresado, según el tipo de institución (Ley 30512) y el ciclo (CETPRO)."""
    if niv_mod == "T0":
        return "Título de Profesional Técnico o Técnico"
    if niv_mod == "S0":
        return "Grado de Bachiller Técnico y Título Profesional (Ley 30512)"
    if niv_mod == "P0":
        return "Grado de Bachiller en Educación y Título de Licenciado en Educación (Ley 30512)"
    if niv_mod == "K0":
        return "Título de Profesor (y grado de Bachiller en Educación en escuelas licenciadas)"
    if niv_mod == "M0":
        return "Título profesional en Arte"
    if cuadro == "C1062":
        return "Título de Técnico (ciclo medio)"
    return "Certificado de Auxiliar Técnico (ciclo básico)"


def duracion_ies(niv_mod: str, duracion, horas) -> str:
    d = str(duracion).strip() if pd.notna(duracion) else ""
    if niv_mod in ("T0", "S0"):
        return f"{d} años" if d.isdigit() and 1 <= int(d) <= 5 else "2 a 3 años"
    if niv_mod in ("K0", "P0", "M0"):
        return "5 años"
    h = int(horas) if pd.notna(horas) and horas else 0
    return f"{h:,} horas" if h > 0 else "Menos de 1 año"


def programas_manuales(oferta: pd.DataFrame) -> pd.DataFrame:
    """Reemplaza la oferta de una institución por sus programas verificados a mano
    (data/programas_manuales.csv). Sirve para escuelas cuyo censo no reporta especialidades,
    como la EESPP Monterrico: se copian los datos de la institución y se crea una fila por programa."""
    archivo = RAIZ / "data" / "programas_manuales.csv"
    if not archivo.exists():
        return oferta
    manual = pd.read_csv(archivo, dtype=str)
    nuevas = []
    for codigo, grupo in manual.groupby("codigo"):
        base = oferta[oferta["codigo"] == codigo]
        if base.empty:
            print(f"Aviso: {codigo} no está en la oferta; se omite")
            continue
        fila = base.iloc[0]
        for programa in grupo["programa"]:
            nuevas.append({**fila.to_dict(), "programa": programa.upper(), "familia": ""})
    codigos = set(manual["codigo"])
    return pd.concat([oferta[~oferta["codigo"].isin(codigos)], pd.DataFrame(nuevas)], ignore_index=True)


# Programas de formación continua: son para quienes ya estudiaron o tienen un título (titulación,
# complementación, profesionalización docente), no para estudiantes que salen del colegio.
FORMACION_CONTINUA = re.compile(r"TITULACION|COMPLEMENTACION|PROFESIONALIZACION|MODALIDAD DE EGRESADOS|"
                                r"SEGUNDA ESPECIALIDAD|PARA PROFESIONALES|CONVALIDACION")


def sin_formacion_continua(oferta: pd.DataFrame) -> pd.DataFrame:
    es_continua = oferta["programa"].map(lambda prog: bool(FORMACION_CONTINUA.search(normalizar(prog))))
    print(f"Excluidos {int(es_continua.sum())} programas de formación continua (titulación, complementación…)")
    return oferta[~es_continua]


def sin_otros_programas(oferta: pd.DataFrame) -> pd.DataFrame:
    """Quita las categorías genéricas del censo ('OTROS PROGRAMAS EN …'), que no dicen qué carrera es.
    Si una institución solo tenía esas, queda como 'oferta no reportada' para seguir apareciendo en el mapa."""
    es_otro = oferta["programa"].map(lambda prog: normalizar(prog).startswith("OTROS") or normalizar(prog) == "OTRO")
    con_otra = set(oferta.loc[~es_otro, "codigo"])
    solo_otros = es_otro & ~oferta["codigo"].isin(con_otra)
    oferta = oferta.copy()
    oferta.loc[solo_otros, "programa"] = "OFERTA NO REPORTADA EN EL CENSO (CONSULTAR SU WEB)"
    oferta.loc[solo_otros, "area"] = "otros"
    print(f"Quitados {int((es_otro & ~solo_otros).sum())} registros 'Otros programas'; "
          f"{oferta.loc[solo_otros, 'codigo'].nunique()} instituciones quedan como 'oferta no reportada'")
    return oferta[~(es_otro & ~solo_otros)].drop_duplicates()


def main():
    descargar()
    oferta = pd.concat([universidades(), institutos(), instituciones_extra()], ignore_index=True)
    oferta = programas_manuales(oferta)
    oferta["programa"] = oferta["programa"].str.upper()
    oferta = sin_formacion_continua(oferta)
    oferta["area"] = [clasificar(p, f) for p, f in zip(oferta["programa"], oferta["familia"])]
    oferta = sin_otros_programas(oferta)
    # SUNEDU escribe 'JUNÍN' y MINEDU 'JUNIN': sin tildes para que coincidan entre sí y con el mapa
    for col in ["departamento", "provincia"]:
        oferta[col] = oferta[col].map(normalizar)
    oferta["distrito"] = oferta["distrito"].str.upper().str.strip()
    # Coordenadas fuera del Perú = dato faltante
    fuera = ~oferta["lat"].between(-18.5, 0.1) | ~oferta["lon"].between(-81.5, -68.5)
    oferta.loc[fuera, ["lat", "lon"]] = None
    oferta = correcciones_manuales(oferta)
    # Logos obtenidos de la web oficial de cada institución (data/obtener_logos.py)
    archivo_logos = RAIZ / "data" / "logos.csv"
    if archivo_logos.exists():
        logos = pd.read_csv(archivo_logos, dtype=str).dropna(subset=["logo"])
        oferta["logo_web"] = oferta["codigo"].map(dict(zip(logos["codigo"], logos["logo"])))
    oferta = oferta.drop(columns="familia").drop_duplicates()
    oferta.to_csv(RAIZ / "data" / "oferta.csv", index=False, encoding="utf-8")

    print(f"{len(oferta):,} filas")
    print(oferta.groupby(["tipo", "gestion"]).size().to_string())
    print(oferta["area"].value_counts().to_string())


if __name__ == "__main__":
    main()
