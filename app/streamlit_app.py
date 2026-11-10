"""Rumbo: test vocacional + dónde estudiar en el Perú (público y privado).

Correr:  streamlit run app/streamlit_app.py
"""
import json
import sys
from pathlib import Path
import base64
from urllib.parse import quote_plus, urlparse

import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from folium.plugins import Fullscreen, MarkerCluster
from streamlit_folium import st_folium

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from ai.areas import AREAS, icono_area, nombre_area, normalizar  # noqa: E402
from ai.orientador import _nivel as nivel_de  # noqa: E402
from ai.orientador import recomendar  # noqa: E402
from ai.perfil_egreso import perfil_egreso  # noqa: E402
from ai.test_vocacional import (DIMENSIONES, EJEMPLO, OPCIONES, PREGUNTAS,  # noqa: E402
                                codigo_holland, puntajes, ranking_areas)

st.set_page_config(page_title="Rumbo · Orientación vocacional", page_icon="🧭", layout="wide")

# ============================================================
# Estilo
# ============================================================
AZUL, AZUL_OSCURO, CELESTE, AZUL_SUAVE, GRIS = "#1d4ed8", "#1e3a8a", "#38bdf8", "#eff6ff", "#64748b"
AMBAR, AMBAR_OSCURO = "#f59e0b", "#78350f"
COLOR_GESTION = {"Pública": AZUL, "Privada": AMBAR}  # opción 1: azul + ámbar
# Mapa por regiones: de turquesa claro a azul marino
ESCALA_AZUL = [[0, "#ecfeff"], [0.12, "#ccfbf1"], [0.3, "#5eead4"], [0.5, "#2dd4bf"], [0.65, "#0ea5e9"],
               [0.82, "#2563eb"], [1, "#1e3a8a"]]
N_PASOS = 4  # bloques de preguntas: 6 preguntas por bloque, una de cada tipo de interés

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
.stApp, .stApp p, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5,
.stApp input, .stApp textarea, .stApp button {{font-family: 'Inter', sans-serif;}}
.stApp {{background: #ffffff;}}
.block-container {{padding-top: 1.6rem; max-width: 1280px;}}

/* Portada */
.hero {{background: radial-gradient(circle at 85% 20%, rgba(56,189,248,.45), transparent 45%),
        linear-gradient(125deg, {AZUL_OSCURO} 0%, {AZUL} 70%); color: #fff; border-radius: 22px;
        padding: 26px 34px 30px; margin-bottom: 8px; box-shadow: 0 18px 40px rgba(30,58,138,.25);
        animation: aparecer .6s ease-out;}}
.hero .top {{display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;}}
.hero .marca {{font-weight: 800; font-size: 1.25rem; letter-spacing: .02em;}}
.hero .chip {{background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.28); border-radius: 999px;
             padding: 4px 12px; font-size: .78rem; margin-left: 6px;}}
.hero h1 {{color: #fff; font-size: 2.6rem; font-weight: 800; line-height: 1.1; margin: 22px 0 8px;}}
.hero p.sub {{font-size: 1.08rem; opacity: .92; max-width: 760px; margin: 0;}}
.hero .stats {{display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-top: 22px;}}
.hero .stat {{background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.25); border-radius: 14px;
             padding: 12px 16px;}}
.hero .stat b {{display: block; font-size: 1.6rem; font-weight: 800;}}
.hero .stat span {{font-size: .82rem; opacity: .9;}}

/* Secciones */
.sec {{margin: 38px 0 14px; padding-bottom: 12px; border-bottom: 1px solid #dbeafe; scroll-margin-top: 90px;
      animation: aparecer .5s ease-out;}}
.sec .eyebrow {{color: {AZUL}; font-weight: 700; letter-spacing: .14em; font-size: .72rem; text-transform: uppercase;}}
.sec h2 {{color: #0f172a; font-weight: 800; font-size: 1.65rem; margin: 2px 0 2px; padding: 0;}}
.sec p {{color: {GRIS}; margin: 0; font-size: .98rem;}}

/* Navegación de resultados */
.nav {{display: flex; gap: 6px; flex-wrap: wrap; padding: 10px 12px; background: {AZUL_SUAVE};
      border: 1px solid #dbeafe; border-radius: 14px; margin: 4px 0 6px;}}
.nav a {{color: {AZUL_OSCURO} !important; text-decoration: none; font-weight: 600; font-size: .88rem;
        padding: 6px 12px; border-radius: 10px; transition: all .15s;}}
.nav a:hover {{background: {AZUL}; color: #fff !important;}}

/* Indicadores */
.kpis {{display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 6px 0 14px;}}
.kpi {{background: #fff; border: 1px solid #dbeafe; border-top: 4px solid {AZUL}; border-radius: 14px;
      padding: 12px 16px; box-shadow: 0 4px 14px rgba(29,78,216,.06);}}
.kpi .v {{font-size: 1.65rem; font-weight: 800; color: {AZUL_OSCURO}; line-height: 1.2;}}
.kpi .l {{color: {GRIS}; font-size: .83rem;}}
.kpi.claro {{border-top-color: {AMBAR};}}

/* Elementos varios */
.perfil {{font-size: 3.4rem; font-weight: 800; letter-spacing: .35rem; line-height: 1.1;
         background: linear-gradient(90deg, {AZUL_OSCURO}, {CELESTE}); -webkit-background-clip: text;
         -webkit-text-fill-color: transparent;}}
.pill {{display: inline-block; padding: 3px 11px; border-radius: 999px; font-size: .78rem; font-weight: 600;
       margin: 0 4px 4px 0;}}
.pill.pub {{background: {AZUL}; color: #fff;}} .pill.pri {{background: {AMBAR}; color: {AMBAR_OSCURO};}}
.pill.tipo {{background: {AZUL_SUAVE}; color: {AZUL_OSCURO}; border: 1px solid #bfdbfe;}}
.leyenda {{font-size: .85rem; color: {GRIS};}}
.leyenda i {{display: inline-block; width: 11px; height: 11px; border-radius: 50%; margin: 0 5px 0 12px;
            vertical-align: middle;}}
.dato {{font-size: .92rem; margin: 4px 0;}} .dato b {{color: {AZUL_OSCURO};}}
[class*="st-key-card"] {{background: #fff; border-color: #dbeafe !important; border-radius: 16px !important;
                        transition: transform .2s, box-shadow .2s; animation: aparecer .5s ease-out;}}
[class*="st-key-card"]:hover {{transform: translateY(-3px); box-shadow: 0 14px 28px rgba(29,78,216,.14);
                              border-color: #93c5fd !important;}}
[class*="st-key-mapa"] {{border-radius: 16px !important; border-color: #dbeafe !important; background: #fff;}}
.stTabs [data-baseweb="tab-list"] {{gap: 4px; border-bottom: 1px solid #dbeafe;}}
.stTabs [data-baseweb="tab"] {{font-weight: 600; padding: 10px 16px;}}
.pie {{margin-top: 48px; padding: 18px 0; border-top: 1px solid #dbeafe; color: {GRIS}; font-size: .85rem;
      text-align: center;}}
@keyframes aparecer {{from {{opacity: 0; transform: translateY(10px);}} to {{opacity: 1; transform: none;}}}}
</style>
""", unsafe_allow_html=True)


def seccion(num, titulo: str, subtitulo: str = "", ancla: str = ""):
    """Encabezado de sección (con ancla para el menú de navegación)."""
    eyebrow = f"Sección {num:02d}" if isinstance(num, int) else num
    st.markdown(f'<div class="sec" id="{ancla}"><div class="eyebrow">{eyebrow}</div><h2>{titulo}</h2>'
                f'<p>{subtitulo}</p></div>', unsafe_allow_html=True)


def kpis(items: list[tuple[str, str]], claro_desde: int = 99):
    html = "".join(f'<div class="kpi{" claro" if n >= claro_desde else ""}"><div class="v">{v}</div>'
                   f'<div class="l">{l}</div></div>' for n, (v, l) in enumerate(items))
    st.markdown(f'<div class="kpis">{html}</div>', unsafe_allow_html=True)


def pill_gestion(g: str) -> str:
    return f'<span class="pill {"pub" if g == "Pública" else "pri"}">{g}</span>'


LEYENDA = (f'<div class="leyenda"><i style="background:{COLOR_GESTION["Pública"]}"></i>Pública'
           f'<i style="background:{COLOR_GESTION["Privada"]}"></i>Privada · haz clic en un punto para ver '
           f'la institución y su web</div>')

# ============================================================
# Datos
# ============================================================
PALABRAS_VACIAS = {"DE", "DEL", "LA", "EL", "LOS", "LAS", "Y", "E", "EN", "CON", "PARA", "INGENIERIA",
                   "TECNICA", "TECNICO", "TECNICAS", "CIENCIAS", "CIENCIA", "LICENCIATURA", "PROFESIONAL"}
SIN_CARRERA = "OFERTA NO REPORTADA"


def raiz_carrera(programa: str) -> str:
    """Clave para juntar carreras equivalentes de distinto nivel:
    'ENFERMERÍA' y 'ENFERMERIA TÉCNICA' -> 'ENFERM'; 'INGENIERÍA DE SISTEMAS' -> 'SISTEM'."""
    palabras = [w for w in normalizar(programa).replace(",", " ").split() if w not in PALABRAS_VACIAS]
    return palabras[0][:6] if palabras else normalizar(programa)


ARCHIVO_OFERTA = RAIZ / "data" / "oferta.csv"


@st.cache_data
def cargar_oferta(version: float) -> pd.DataFrame:
    """`version` = fecha de modificación del CSV: si se regeneran los datos, la caché se renueva sola."""
    df = pd.read_csv(ARCHIVO_OFERTA)
    df["web"] = df["web"].where(df["web"].notna() & (df["web"] != ""), None)
    # Para todas las instituciones: búsqueda en Google con nombre + distrito (por si no hay web oficial)
    prefijo = df["tipo"].map({"Instituto tecnológico": "Instituto", "Instituto pedagógico": "Instituto pedagógico",
                              "Escuela superior tecnológica (EEST)": "Escuela", "Escuela superior pedagógica (EESP)":
                              "Escuela pedagógica", "Escuela de arte": "Escuela",
                              "CETPRO (técnico-productiva)": "CETPRO"}).fillna("")
    consulta = prefijo + " " + df["institucion"] + " " + df["distrito"].fillna("").str.title() + " admisión"
    df["buscar"] = "https://www.google.com/search?q=" + consulta.map(lambda q: quote_plus(q))
    df["raiz"] = df["programa"].map(raiz_carrera)
    logos_web = df["logo_web"] if "logo_web" in df else pd.Series(None, index=df.index)
    df["logo"] = [logo_url(n, w) for n, w in zip(df["nombre_corto"].fillna(df["institucion"]), logos_web)]
    return df


@st.cache_data
def cargar_geo() -> dict:
    return json.loads((RAIZ / "data" / "geo" / "peru_departamentos.geojson").read_text(encoding="utf-8"))


def tiene_web(x) -> bool:
    return isinstance(x, str) and x.startswith("http")


PALABRAS_NOMBRE = {"DE", "DEL", "LA", "EL", "Y", "E", "LOS", "LAS", "S.A.C.", "S.A.", "S.R.L.", "SAC"}


def logo_url(nombre: str, logo_web) -> str:
    """Logo de la institución tomado de su web oficial (data/obtener_logos.py).
    Si no hay: un círculo azul con sus iniciales (SVG en línea), para que todas tengan imagen."""
    if tiene_web(logo_web):
        return logo_web
    iniciales = "".join(w[0] for w in str(nombre).upper().split() if w not in PALABRAS_NOMBRE and w[0].isalpha())[:2]
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='64' height='64'><circle cx='32' cy='32' r='32' "
           f"fill='#1d4ed8'/><text x='32' y='41' font-family='Arial' font-size='24' font-weight='700' "
           f"fill='white' text-anchor='middle'>{iniciales or '?'}</text></svg>")
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def logo_html(r, tam: int = 40) -> str:
    return (f"<img src='{r.logo}' width='{tam}' height='{tam}' style='border-radius:10px;object-fit:contain;"
            f"background:#fff;border:1px solid #dbeafe;padding:3px;vertical-align:middle'>")


COLUMNAS_TABLA = ["logo", "institucion", "tipo", "gestion", "programa", "departamento", "provincia", "distrito",
                  "web", "buscar"]
CONFIG_TABLA = {
    "logo": st.column_config.ImageColumn("", width="small"),
    "institucion": "Institución", "tipo": "Tipo", "gestion": "Gestión", "programa": "Carrera",
    "departamento": "Región", "provincia": "Provincia", "distrito": "Distrito",
    "web": st.column_config.LinkColumn("Sitio web", display_text="Ir a la web ↗"),
    "buscar": st.column_config.LinkColumn("Más info", display_text="Buscar ↗"),
}

oferta = cargar_oferta(ARCHIVO_OFERTA.stat().st_mtime)
GEO = cargar_geo()
departamentos = sorted(oferta["departamento"].dropna().unique())
programas_reales = sorted(p for p in oferta["programa"].unique() if not p.startswith(SIN_CARRERA))

# ============================================================
# Mapas
# ============================================================
METRICAS = {"Ofertas de estudio": "ofertas", "Instituciones": "instituciones", "% de oferta pública": "publica"}


@st.cache_data
def centros_regiones() -> dict:
    """Centro y tamaño aproximado de cada región (para hacer zoom sobre ella)."""
    def coords(geom):
        c = geom["coordinates"]
        polys = c if geom["type"] == "MultiPolygon" else [c]
        return [pt for poly in polys for anillo in poly for pt in anillo]
    res = {}
    for f in GEO["features"]:
        pts = coords(f["geometry"])
        lons, lats = [p[0] for p in pts], [p[1] for p in pts]
        ancho = max(max(lons) - min(lons), max(lats) - min(lats))
        res[f["properties"]["NOMBDEP"]] = {"lat": (min(lats) + max(lats)) / 2, "lon": (min(lons) + max(lons)) / 2,
                                           "zoom": 8.6 if ancho < 0.5 else 7.2 if ancho < 2.5 else 6.2 if ancho < 5 else 5.4}
    return res


def mapa_regiones(df: pd.DataFrame, metrica: str, key: str, height: int = 520, destacar: str | None = None):
    """Mapa coroplético interactivo del Perú por región: zoom con la rueda del mouse, arrastre y detalle al pasar."""
    agg = (df.groupby("departamento")
             .agg(ofertas=("programa", "size"), instituciones=("institucion", "nunique"),
                  publica=("gestion", lambda s: round((s == "Pública").mean() * 100, 1)))
             .reindex([f["properties"]["NOMBDEP"] for f in GEO["features"]], fill_value=0))
    col = METRICAS[metrica]
    fig = go.Figure(go.Choroplethmap(
        geojson=GEO, featureidkey="properties.NOMBDEP", locations=agg.index, z=agg[col],
        colorscale=ESCALA_AZUL, marker_opacity=0.82, marker_line_color="#ffffff", marker_line_width=1.3,
        customdata=agg[["ofertas", "instituciones", "publica"]].values,
        hovertemplate="<b>%{location}</b><br>Ofertas de estudio: %{customdata[0]:,}"
                      "<br>Instituciones: %{customdata[1]:,}<br>Oferta pública: %{customdata[2]}%<extra></extra>",
        colorbar={"title": {"text": metrica, "side": "right"}, "thickness": 12, "len": 0.7, "outlinewidth": 0,
                  "x": 0.98, "bgcolor": "rgba(255,255,255,.75)"},
    ))
    centro = {"lat": -9.4, "lon": -75.0}
    zoom = 4.25
    if destacar and destacar in agg.index:
        fig.add_trace(go.Choroplethmap(  # contorno resaltado de la región elegida
            geojson=GEO, featureidkey="properties.NOMBDEP", locations=[destacar], z=[1],
            colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]], showscale=False,
            marker_line_color=AMBAR, marker_line_width=4, hoverinfo="skip"))
        c = centros_regiones()[destacar]
        centro, zoom = {"lat": c["lat"], "lon": c["lon"]}, c["zoom"]
    fig.update_layout(map={"style": "carto-positron", "center": centro, "zoom": zoom},
                      height=height, margin={"l": 0, "r": 0, "t": 0, "b": 0}, paper_bgcolor="rgba(0,0,0,0)",
                      font={"family": "Inter"}, hoverlabel={"bgcolor": "#fff", "bordercolor": AZUL,
                                                            "font": {"family": "Inter", "color": "#0f172a"}},
                      uirevision=f"{key}-{destacar}")
    st.plotly_chart(fig, width="stretch", key=key,
                    config={"scrollZoom": True, "displaylogo": False,
                            "modeBarButtonsToRemove": ["select2d", "lasso2d", "toImage"]})
    st.caption("Usa la rueda del mouse para hacer zoom y arrastra para moverte.")
    return agg


def mapa_instituciones(df: pd.DataFrame, key: str, height: int = 470):
    """Mapa de puntos: una marca por sede, con sus carreras y enlaces en el popup."""
    pts = df.dropna(subset=["lat", "lon"])
    if pts.empty:
        st.info("No hay coordenadas para mostrar en el mapa.")
        return
    sedes = (pts.groupby(["institucion", "tipo", "gestion", "distrito", "provincia", "lat", "lon"], dropna=False)
                .agg(programas=("programa", lambda s: sorted(set(s))), web=("web", "first"), buscar=("buscar", "first"),
                     logo=("logo", "first"))
                .reset_index())
    mapa = folium.Map(tiles="OpenStreetMap", control_scale=True)
    mapa.fit_bounds([[sedes["lat"].min(), sedes["lon"].min()], [sedes["lat"].max(), sedes["lon"].max()]],
                    max_zoom=13)
    Fullscreen(position="topright", title="Pantalla completa", title_cancel="Salir").add_to(mapa)
    grupo = MarkerCluster(options={"showCoverageOnHover": False}).add_to(mapa)
    for r in sedes.itertuples():
        lista = "".join(f"<li>{p.title()}</li>" for p in r.programas[:6])
        extra = f"<li>… y {len(r.programas) - 6} más</li>" if len(r.programas) > 6 else ""
        enlaces = ((f'<a href="{r.web}" target="_blank">Ir a la web ↗</a> · ' if tiene_web(r.web) else "")
                   + f'<a href="{r.buscar}" target="_blank">Buscar ↗</a>')
        folium.CircleMarker(
            [r.lat, r.lon], radius=8, color="#ffffff", weight=2, fill=True,
            fill_color=COLOR_GESTION[r.gestion], fill_opacity=0.95,
            tooltip=f"{r.institucion} · {r.gestion}",
            popup=folium.Popup(f"<div style='font-family:Inter,sans-serif;font-size:13px'>"
                               f"{logo_html(r, 34)} <b style='color:{AZUL_OSCURO}'>{r.institucion}</b><br>"
                               f"<span style='color:{GRIS}'>{r.tipo} · {r.gestion}<br>"
                               f"{r.distrito.title()}, {r.provincia.title()}</span>"
                               f"<ul style='padding-left:16px;margin:6px 0'>{lista}{extra}</ul>{enlaces}</div>",
                               max_width=300),
        ).add_to(grupo)
    st_folium(mapa, height=height, use_container_width=True, returned_objects=[], key=key)
    st.markdown(LEYENDA, unsafe_allow_html=True)


# ============================================================
# Estado de la sesión
# ============================================================
# Las respuestas se guardan aparte de los widgets: así no se pierden al pasar de un paso a otro.
ss = st.session_state
ss.setdefault("paso", 0)
ss.setdefault("resp", [None] * len(PREGUNTAS))
ss.setdefault("depto", "LIMA")
ss.setdefault("sobre_mi", "")


def calcular_resultado():
    punt = puntajes(ss["resp"])
    ranking = ranking_areas(punt)
    ss["resultado"] = {"punt": punt, "ranking": ranking, "depto": ss["depto"],
                       "rec": recomendar(punt, ranking, oferta, ss["sobre_mi"], ss["depto"])}
    ss["paso"] = N_PASOS + 1
    ss["celebrar"] = True
    ss.pop("prog_sel", None)


def usar_demo():
    ss["resp"] = list(EJEMPLO)
    ss["depto"] = "AYACUCHO"
    ss["sobre_mi"] = "Me gusta ayudar a mis compañeros con biología y quiero estudiar cerca de mi familia en Ayacucho."
    calcular_resultado()


def ir_a(paso: int):
    ss["paso"] = paso


def reiniciar():
    for k in list(ss.keys()):
        del ss[k]


def ver_donde(programa: str):
    ss["prog_sel"] = programa


@st.cache_data(show_spinner="Preparando el perfil de egreso...")
def perfil_cacheado(programa: str, nivel: str, area_id: str) -> dict:
    return perfil_egreso(programa, nivel, area_id)


# ============================================================
# Comparador
# ============================================================
def comparador(prog_inicial: str, region_inicial: str, k: str):
    """Compara lado a lado hasta 4 instituciones que ofrecen una carrera, y el perfil de egreso por nivel."""
    c1, c2, c4, c3 = st.columns([2, 1, 1, 1])
    prog = c1.selectbox("Carrera a comparar", programas_reales, index=programas_reales.index(prog_inicial),
                        format_func=str.title, key=f"{k}_prog")
    regiones = ["TODAS"] + departamentos
    region = c2.selectbox("Región", regiones, index=regiones.index(region_inicial), key=f"{k}_reg",
                          format_func=str.title)
    gestion = c4.selectbox("Gestión", ["Ambas", "Pública", "Privada"], key=f"{k}_gest")
    c3.markdown("<div style='height:1.9rem'></div>", unsafe_allow_html=True)
    equivalentes = c3.toggle("Incluir carreras equivalentes", value=True, key=f"{k}_eq",
                             help="Junta, por ejemplo, Enfermería (universidad) y Enfermería Técnica (instituto)")
    sub = oferta[oferta["raiz"] == raiz_carrera(prog)] if equivalentes else oferta[oferta["programa"] == prog]
    sub = sub[~sub["programa"].str.startswith(SIN_CARRERA)]
    if region != "TODAS":
        sub = sub[sub["departamento"] == region]
    if gestion != "Ambas":
        sub = sub[sub["gestion"] == gestion]
    sub = sub.drop_duplicates(["institucion", "tipo", "programa", "distrito"])
    if sub.empty:
        st.info("No hay instituciones con esta carrera y filtros. Prueba con otra región o con «Ambas».")
        return
    # Por defecto: una de cada combinación tipo × gestión (universidad pública, instituto privado, ...)
    por_defecto = list(sub.groupby(["tipo", "gestion"], sort=False).head(1)
                       .sort_values("tipo", key=lambda t: t != "Universidad").index)[:4]
    elegidas = st.multiselect(
        "Instituciones a comparar (hasta 4)", list(sub.index), default=por_defecto, max_selections=4,
        key=f"{k}_inst_{prog}_{region}_{gestion}_{equivalentes}",  # se reinicia al cambiar la carrera o la región
        format_func=lambda i: f"{sub.at[i, 'institucion']} · {sub.at[i, 'programa'].title()} · "
                              f"{sub.at[i, 'tipo']} · {sub.at[i, 'gestion']} · {sub.at[i, 'distrito'].title()}")
    if not elegidas:
        return

    for col, i in zip(st.columns(len(elegidas)), elegidas):
        r = sub.loc[i]
        with col, st.container(border=True, key=f"card_cmp_{k}_{i}"):
            st.markdown(f"<div style='display:flex;gap:10px;align-items:center;margin-bottom:4px'>{logo_html(r, 46)}"
                        f"<div style='font-weight:800;font-size:1.02rem;color:{AZUL_OSCURO};line-height:1.2'>"
                        f"{r.institucion}</div></div>"
                        f"<div style='color:{GRIS};font-size:.9rem;margin-bottom:6px'>{r.programa.title()}</div>"
                        f"{pill_gestion(r.gestion)}<span class='pill tipo'>{r.tipo}</span>"
                        f"<div class='dato'><b>Al egresar:</b> {r.certificacion}</div>"
                        f"<div class='dato'><b>Duración:</b> {r.duracion}</div>"
                        f"<div class='dato'><b>Costo:</b> "
                        f"{'gratuita o de bajo costo' if r.gestion == 'Pública' else 'pensión, consultar'}</div>"
                        f"<div class='dato'><b>Ubicación:</b> {r.distrito.title()}, {r.departamento.title()}</div>",
                        unsafe_allow_html=True)
            if tiene_web(r.web):
                st.link_button("Ver perfil oficial en su web ↗", r.web, width="stretch", type="primary")
            st.link_button("Buscar más información ↗", r.buscar, width="stretch")

    izq, der = st.columns([3, 2])
    with izq:
        st.markdown("##### Perfil de egreso referencial")
        # Un perfil por cada combinación carrera + nivel elegida (p. ej. Enfermería universitaria vs. técnica)
        pares = list(dict.fromkeys((sub.at[i, "programa"], nivel_de(sub.at[i, "tipo"]), sub.at[i, "area"])
                                   for i in elegidas))
        for n, (programa, nivel, area_id) in enumerate(pares):
            p = perfil_cacheado(programa, nivel, area_id)
            with st.expander(f"{programa.title()} · formación {nivel}", expanded=n < 2):
                st.caption(p["enfoque"])
                st.write(p["resumen"])
                a, b = st.columns(2)
                a.markdown("**Sabrás hacer**\n" + "\n".join(f"- {x}" for x in p["sabras_hacer"]))
                b.markdown("**Dónde podrás trabajar**\n" + "\n".join(f"- {x}" for x in p["donde_trabajar"]))
        st.caption("Perfil referencial generado " + ("con IA" if p.get("fuente") == "ia" else "con plantillas")
                   + " para el nivel de formación, no para una institución en particular. "
                     "Revisa el perfil de egreso oficial en la web de cada institución.")
    with der:
        st.markdown("##### Ubicación de las instituciones")
        with st.container(border=True, key=f"mapa_cmp_{k}"):
            mapa_instituciones(sub.loc[elegidas], key=f"mapa_cmp_{k}_{'_'.join(map(str, elegidas))}", height=340)


# ============================================================
# Portada
# ============================================================
st.markdown(f"""
<div class="hero">
  <div class="top">
    <div class="marca">🧭 Rumbo</div>
    <div><span class="chip">Datos SUNEDU</span><span class="chip">Censo Educativo MINEDU 2025</span>
         <span class="chip">IA con Claude</span></div>
  </div>
  <h1>Encuentra qué estudiar<br>y dónde, cerca de casa</h1>
  <p class="sub">Test vocacional gratuito que te muestra todas tus opciones reales en el Perú: universidades,
     institutos, escuelas superiores, pedagógicos y CETPRO, públicos y privados.</p>
  <div class="stats">
    <div class="stat"><b>{len(oferta):,}</b><span>ofertas de estudio</span></div>
    <div class="stat"><b>{oferta['institucion'].nunique():,}</b><span>instituciones</span></div>
    <div class="stat"><b>{oferta['departamento'].nunique()}</b><span>regiones</span></div>
    <div class="stat"><b>{(oferta['gestion'] == 'Pública').mean():.0%}</b><span>en instituciones públicas</span></div>
  </div>
</div>""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🧭 Rumbo")
    st.write("Orientación vocacional con datos abiertos de **SUNEDU** y del **Censo Educativo 2025 del MINEDU**.")
    st.caption("No guardamos tus respuestas ni datos personales.")
    st.button("Reiniciar test", on_click=reiniciar, width="stretch")

tab_test, tab_panorama, tab_explorar, tab_comparar, tab_colegios = st.tabs(
    ["🧭  Test vocacional", "🗺️  Panorama nacional", "🔎  Explorar la oferta", "⚖️  Comparar", "🏫  Para colegios"])

# ============================================================
# TEST
# ============================================================
with tab_test:
    paso = ss["paso"]

    # ---- Paso 0: bienvenida + panorama nacional ----
    if paso == 0:
        seccion("Comienza aquí", "Empieza tu test vocacional", "24 actividades en 4 pasos cortos · unos 3 minutos", "inicio")
        izq, der = st.columns([3, 2], gap="large")
        with izq, st.container(border=True, key="card_inicio"):
            ss["depto"] = st.selectbox("¿En qué región vives?", departamentos,
                                       index=departamentos.index(ss["depto"]), format_func=str.title)
            ss["sobre_mi"] = st.text_area("Cuéntanos con tus palabras qué te gusta o qué te imaginas haciendo "
                                          "(opcional)", value=ss["sobre_mi"], max_chars=600, height=110)
            b1, b2 = st.columns(2)
            b1.button("Empezar el test →", type="primary", on_click=ir_a, args=(1,), width="stretch")
            b2.button("Ver un ejemplo (demo)", on_click=usar_demo, width="stretch")
        with der, st.container(border=True, key="card_beneficios"):
            st.markdown("**Lo que vas a obtener**")
            st.markdown("1. Tu **perfil de intereses** (modelo RIASEC)\n"
                        "2. **Carreras sugeridas**, universitarias y técnicas\n"
                        "3. **Mapa** de dónde estudiarlas en tu región\n"
                        "4. **Comparación** de instituciones públicas y privadas\n"
                        "5. Un **reporte** para tu tutor o tu familia")


    # ---- Pasos 1-4: preguntas ----
    elif 1 <= paso <= N_PASOS:
        seccion(f"Paso {paso} de {N_PASOS}", "¿Cuánto te gustaría hacer cada actividad?",
                "No hay respuestas buenas ni malas: responde lo que sientes", "preguntas")
        st.progress(paso / N_PASOS)
        indices = [paso - 1 + N_PASOS * d for d in range(len(DIMENSIONES))]  # una pregunta de cada tipo
        cols = st.columns(2)
        for n, i in enumerate(indices):
            with cols[n % 2], st.container(border=True, key=f"card_q{i}"):
                actual = ss["resp"][i]
                valor = st.radio(f"**{PREGUNTAS[i][1]}**", list(OPCIONES), format_func=OPCIONES.get,
                                 horizontal=True, index=list(OPCIONES).index(actual) if actual else None, key=f"w{i}")
                ss["resp"][i] = valor
        faltan = sum(ss["resp"][i] is None for i in indices)
        b1, _, b2 = st.columns([1, 2, 1])
        b1.button("← Atrás", on_click=ir_a, args=(paso - 1,), width="stretch")
        if paso < N_PASOS:
            b2.button("Siguiente →", type="primary", disabled=faltan > 0, on_click=ir_a, args=(paso + 1,),
                      width="stretch")
        else:
            b2.button("Ver mis resultados →", type="primary", disabled=faltan > 0, on_click=calcular_resultado,
                      width="stretch")
        if faltan:
            st.caption(f"Responde las {faltan} actividades que faltan para continuar.")

    # ---- Resultados ----
    elif ss.get("resultado"):
        res = ss["resultado"]
        punt, ranking, rec, depto_est = res["punt"], res["ranking"], res["rec"], res["depto"]
        if ss.pop("celebrar", False):
            st.balloons()
            st.toast("¡Listo! Este es tu perfil 🎉")

        st.markdown('<div class="nav"><a href="#perfil">01 · Tu perfil</a><a href="#areas">02 · Áreas afines</a>'
                    '<a href="#carreras">03 · Carreras</a><a href="#donde">04 · Dónde estudiar</a>'
                    '<a href="#comparar">05 · Comparar</a><a href="#reporte">06 · Reporte</a></div>',
                    unsafe_allow_html=True)

        # 01 Perfil
        seccion(1, "Tu perfil de intereses", "Basado en el modelo RIASEC de John Holland", "perfil")
        izq, der = st.columns([1, 1], gap="large")
        with izq:
            st.markdown(f'<div class="perfil">{codigo_holland(punt)}</div>', unsafe_allow_html=True)
            st.write(rec["perfil"])
            st.markdown("".join(f"<span class='pill tipo'>{f}</span>" for f in rec["fortalezas"]),
                        unsafe_allow_html=True)
            st.info("**Siguiente paso:** " + rec["siguiente_paso"])
            st.caption("Recomendación generada con IA (Claude) y validada contra los datos oficiales."
                       if rec.get("fuente") == "ia" else "Recomendación generada con reglas del modelo RIASEC.")
        with der, st.container(border=True, key="card_radar"):
            etiquetas = [DIMENSIONES[d][0] for d in punt] + [DIMENSIONES[next(iter(punt))][0]]
            valores = list(punt.values()) + [next(iter(punt.values()))]
            radar = go.Figure(go.Scatterpolar(
                r=valores, theta=etiquetas, fill="toself", line={"color": AZUL, "width": 2.5},
                fillcolor="rgba(56,189,248,.30)", marker={"size": 7, "color": AZUL_OSCURO},
                hovertemplate="%{theta}: %{r:.0f}/100<extra></extra>"))
            radar.update_layout(polar={"radialaxis": {"range": [0, 100], "showticklabels": False, "gridcolor": "#dbeafe"},
                                       "angularaxis": {"gridcolor": "#dbeafe"}, "bgcolor": "#fff"},
                                margin={"l": 50, "r": 50, "t": 25, "b": 25}, height=330, showlegend=False,
                                font={"family": "Inter", "size": 13})
            st.plotly_chart(radar, width="stretch", config={"displayModeBar": False})

        # 02 Áreas
        seccion(2, "Tus áreas más afines", "Qué tanto se parecen tus intereses a cada campo de estudio", "areas")
        for col, (a, s) in zip(st.columns(4), ranking[:4]):
            with col, st.container(border=True, key=f"card_area_{a}"):
                st.markdown(f"<div style='font-size:2rem'>{icono_area(a)}</div>"
                            f"<div style='font-weight:700;color:{AZUL_OSCURO};min-height:2.6rem'>{AREAS[a]['nombre']}</div>",
                            unsafe_allow_html=True)
                st.progress(min(s / 100, 1.0), text=f"Afinidad {s:.0f}/100")

        # 03 Carreras
        seccion(3, "Carreras sugeridas para ti", f"Primero las que puedes estudiar en {depto_est.title()}", "carreras")
        en_region = oferta[oferta["departamento"] == depto_est]["programa"].value_counts()
        carreras = sorted(rec["carreras"], key=lambda c: -en_region.get(c["programa"], 0))
        cols = st.columns(3)
        for n, c in enumerate(carreras):
            with cols[n % 3], st.container(border=True, key=f"card_prog_{n}"):
                lugares = int(en_region.get(c["programa"], 0))
                st.markdown(f"<div style='font-weight:800;font-size:1.05rem;color:{AZUL_OSCURO}'>"
                            f"{icono_area(c['area_id'])} {c['programa'].title()}</div>"
                            f"<span class='pill tipo'>{c['nivel'].capitalize()}</span>"
                            f"<span class='pill tipo'>{nombre_area(c['area_id'])}</span>"
                            f"<p style='margin:8px 0;font-size:.93rem'>{c['por_que']}</p>"
                            f"<div class='dato'><b>{lugares}</b> lugares en {depto_est.title()}</div>"
                            if lugares else
                            f"<div style='font-weight:800;font-size:1.05rem;color:{AZUL_OSCURO}'>"
                            f"{icono_area(c['area_id'])} {c['programa'].title()}</div>"
                            f"<span class='pill tipo'>{c['nivel'].capitalize()}</span>"
                            f"<p style='margin:8px 0;font-size:.93rem'>{c['por_que']}</p>"
                            f"<div class='dato'>No se ofrece en {depto_est.title()}: mira otras regiones</div>",
                            unsafe_allow_html=True)
                st.button("Ver dónde estudiar ↓", key=f"ver_{n}", on_click=ver_donde, args=(c["programa"],),
                          width="stretch")

        # 04 Dónde estudiar
        seccion(4, "¿Dónde puedo estudiarlo?", "Instituciones públicas y privadas, con enlace a su web", "donde")
        opciones_prog = list(dict.fromkeys(c["programa"] for c in carreras))
        if ss.get("prog_sel") not in opciones_prog:
            ss["prog_sel"] = opciones_prog[0]
        f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
        prog = f1.selectbox("Carrera", opciones_prog, key="prog_sel",
                            format_func=lambda p: f"{p.title()} ({en_region.get(p, 0)} en {depto_est.title()})")
        region = f2.selectbox("Región", ["TODAS"] + departamentos, index=1 + departamentos.index(depto_est),
                              format_func=str.title)
        gestion = f3.selectbox("Gestión", ["Ambas", "Pública", "Privada"])
        f4.markdown("<div style='height:1.9rem'></div>", unsafe_allow_html=True)
        area_prog = oferta.loc[oferta["programa"] == prog, "area"].iloc[0]
        ver_similares = f4.toggle("Carreras parecidas", value=False,
                                  help=f"Incluye otras carreras del área {nombre_area(area_prog)}")
        base = oferta[oferta["area"] == area_prog] if ver_similares else oferta[oferta["programa"] == prog]
        if gestion != "Ambas":
            base = base[base["gestion"] == gestion]
        sel = base[base["departamento"] == region] if region != "TODAS" else base

        kpis([(f"{len(sel):,}", "lugares encontrados"),
              (f"{int((sel['gestion'] == 'Pública').sum()):,}", "en instituciones públicas"),
              (f"{int((sel['gestion'] == 'Privada').sum()):,}", "en instituciones privadas"),
              (f"{int(sel['web'].notna().sum()):,}", "con web oficial")], claro_desde=2)

        izq, der = st.columns([3, 2], gap="large")
        with izq, st.container(border=True, key="mapa_donde"):
            st.markdown(f"**Mapa de instituciones · {region.title()}**")
            if sel.empty:
                st.warning("No hay oferta con esos filtros. Prueba con «Carreras parecidas» o con otra región.")
            else:
                mapa_instituciones(sel, key=f"mapa_donde_{prog}_{region}_{gestion}_{ver_similares}")
        with der, st.container(border=True, key="mapa_nacional_carrera"):
            st.markdown(f"**¿En qué regiones se ofrece?** · {prog.title()}")
            mapa_regiones(base, "Ofertas de estudio", key="ch_carrera", height=450)

        if not sel.empty:
            tabla = sel[COLUMNAS_TABLA].sort_values(["gestion", "tipo", "institucion"])
            tabla["programa"] = tabla["programa"].str.title()
            st.dataframe(tabla, hide_index=True, width="stretch", column_config=CONFIG_TABLA, height=300)

        # 05 Comparar
        seccion(5, "Compara instituciones y perfil de egreso",
                "Universidad, escuela superior, instituto o CETPRO, público o privado: ¿qué obtienes al terminar?",
                "comparar")
        comparador(prog if prog in programas_reales else programas_reales[0], region, "res")

        # 06 Reporte
        seccion(6, "Comparte tu resultado", "Descarga el reporte y conversa con tu tutor o tu familia", "reporte")
        tabla_rep = sel.sort_values(["gestion", "tipo", "institucion"]).head(30)
        reporte = (f"# Reporte vocacional - Rumbo\n\nPerfil: {codigo_holland(punt)}\n\n{rec['perfil']}\n\n"
                   "## Carreras sugeridas\n" + "\n".join(f"- {c['programa'].title()} ({c['nivel']})" for c in carreras)
                   + f"\n\n## Dónde estudiar {prog.title()} ({region.title()}, {gestion})\n"
                   + "\n".join(f"- {r.institucion} - {r.tipo} - {r.gestion} - {r.distrito.title()} - "
                               f"{r.web if tiene_web(r.web) else r.buscar}" for r in tabla_rep.itertuples()))
        b1, b2 = st.columns(2)
        b1.download_button("Descargar reporte para el tutor", reporte, file_name="reporte_rumbo.md",
                           mime="text/markdown", width="stretch", type="primary")
        b2.button("Hacer el test de nuevo", on_click=reiniciar, width="stretch")
    else:
        ss["paso"] = 0
        st.rerun()

# ============================================================
# PANORAMA NACIONAL
# ============================================================
with tab_panorama:
    seccion("Panorama nacional", "La educación superior en el Perú, región por región",
            "Elige qué medir, enfoca una región y usa el zoom del mapa", "panorama")
    izq, der = st.columns([3, 2], gap="large")
    with izq, st.container(border=True, key="mapa_panorama"):
        m1, m2 = st.columns([3, 2])
        with m1:
            metrica = st.segmented_control("Ver en el mapa", list(METRICAS), default="Ofertas de estudio",
                                           key="met_panorama") or "Ofertas de estudio"
        enfoque = m2.selectbox("Enfocar una región", ["TODO EL PERÚ"] + departamentos, key="enfoque",
                               format_func=str.title)
        destacar = None if enfoque == "TODO EL PERÚ" else enfoque
        agg = mapa_regiones(oferta, metrica, key="ch_panorama", height=520, destacar=destacar)
    with der:
        if destacar:
            r = oferta[oferta["departamento"] == destacar]
            st.markdown(f"<div style='font-weight:800;font-size:1.3rem;color:{AZUL_OSCURO}'>"
                        f"{destacar.title()}</div>", unsafe_allow_html=True)
            kpis([(f"{len(r):,}", "ofertas de estudio"), (f"{r['institucion'].nunique():,}", "instituciones"),
                  (f"{(r['gestion'] == 'Pública').mean():.0%}", "oferta pública")], claro_desde=2)
            top_c = (r[~r["programa"].str.startswith(SIN_CARRERA)]["programa"].value_counts().head(8)
                     .sort_values())
            fig = go.Figure(go.Bar(x=top_c.values, y=[p.title()[:38] for p in top_c.index], orientation="h",
                                   marker_color=AZUL, hovertemplate="%{y}: %{x} lugares<extra></extra>"))
            fig.update_layout(title={"text": "Carreras más ofrecidas", "font": {"size": 14}}, height=330,
                              margin={"l": 10, "r": 10, "t": 40, "b": 10}, plot_bgcolor="#fff",
                              font={"family": "Inter", "size": 11})
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        else:
            top = agg.sort_values(METRICAS[metrica], ascending=True).tail(10)
            fig = go.Figure(go.Bar(x=top[METRICAS[metrica]], y=top.index.str.title(), orientation="h",
                                   marker_color=AZUL, hovertemplate="%{y}: %{x}<extra></extra>"))
            fig.update_layout(title={"text": f"Top 10 regiones · {metrica.lower()}", "font": {"size": 14}},
                              height=330, margin={"l": 10, "r": 10, "t": 40, "b": 10},
                              plot_bgcolor="#fff", font={"family": "Inter"})
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
            por_tipo = oferta.groupby("tipo")["institucion"].nunique().sort_values(ascending=False)
            dona = go.Figure(go.Pie(labels=por_tipo.index, values=por_tipo.values, hole=.6, sort=False,
                                    marker={"colors": ["#1e3a8a", "#1d4ed8", "#3b82f6", "#60a5fa", "#93c5fd",
                                                       "#bfdbfe", "#38bdf8", "#0ea5e9"]},
                                    textinfo="none", hovertemplate="%{label}: %{value}<extra></extra>"))
            dona.update_layout(title={"text": "Instituciones por tipo", "font": {"size": 14}}, height=230,
                               margin={"l": 10, "r": 10, "t": 40, "b": 10}, font={"family": "Inter", "size": 11},
                               legend={"font": {"size": 10}})
            st.plotly_chart(dona, width="stretch", config={"displayModeBar": False})

# ============================================================
# EXPLORAR
# ============================================================
with tab_explorar:
    seccion("Explorar", "Toda la oferta de educación superior del Perú",
            "Busca por carrera o por institución y míralo en el mapa", "explorar")
    e1, e2, e3, e4 = st.columns([2, 1, 1, 1])
    texto = e1.text_input("Carrera o institución", placeholder="enfermería, SENATI, Monterrico, diseño...")
    region_e = e2.selectbox("Región ", ["TODAS"] + departamentos, format_func=str.title)
    gestion_e = e3.selectbox("Gestión ", ["Ambas", "Pública", "Privada"])
    tipos = e4.multiselect("Tipo de institución", sorted(oferta["tipo"].unique()))
    q = oferta
    if texto:
        sin_t = str.maketrans("ÁÉÍÓÚ", "AEIOU")
        buscado = texto.upper().translate(sin_t)
        q = q[q["programa"].str.upper().str.translate(sin_t).str.contains(buscado, regex=False, na=False)
              | q["institucion"].str.upper().str.translate(sin_t).str.contains(buscado, regex=False, na=False)]
    if gestion_e != "Ambas":
        q = q[q["gestion"] == gestion_e]
    if tipos:
        q = q[q["tipo"].isin(tipos)]
    q_nacional = q
    if region_e != "TODAS":
        q = q[q["departamento"] == region_e]

    kpis([(f"{len(q):,}", "ofertas encontradas"), (f"{q['institucion'].nunique():,}", "instituciones"),
          (f"{(q['gestion'] == 'Pública').sum():,}", "ofertas públicas"),
          (f"{(q['gestion'] == 'Privada').sum():,}", "ofertas privadas")], claro_desde=3)

    v1, v2, v3 = st.tabs(["Mapa por región", "Mapa de instituciones", "Tabla"])
    with v1:
        izq, der = st.columns([3, 2], gap="large")
        with izq, st.container(border=True, key="mapa_exp_reg"):
            met_e = st.segmented_control("Ver en el mapa ", list(METRICAS), default="Ofertas de estudio",
                                         key="met_explorar") or "Ofertas de estudio"
            mapa_regiones(q_nacional, met_e, key="ch_explorar", height=480)
        with der:
            resumen = q.groupby(["tipo", "gestion"]).size().reset_index(name="n")
            if not resumen.empty:
                fig = go.Figure([go.Bar(y=resumen[resumen["gestion"] == g]["tipo"],
                                        x=resumen[resumen["gestion"] == g]["n"], name=g, orientation="h",
                                        marker_color=COLOR_GESTION[g], hovertemplate="%{y}: %{x}<extra>" + g + "</extra>")
                                 for g in ["Pública", "Privada"]])
                fig.update_layout(barmode="stack", height=420, title={"text": "Ofertas por tipo y gestión",
                                                                       "font": {"size": 14}},
                                  margin={"l": 10, "r": 10, "t": 40, "b": 10}, plot_bgcolor="#fff",
                                  legend={"orientation": "h", "y": -0.12}, font={"family": "Inter"})
                st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    with v2:
        sedes = q.drop_duplicates(["institucion", "lat", "lon"])
        if len(sedes) > 1500:
            st.info(f"Hay {len(sedes):,} sedes. Elige una región o escribe una carrera para ver el mapa de instituciones.")
        else:
            with st.container(border=True, key="mapa_exp_pts"):
                mapa_instituciones(q, key=f"mapa_exp_{texto}_{region_e}_{gestion_e}_{len(q)}", height=520)
    with v3:
        st.dataframe(q[COLUMNAS_TABLA].head(1000), hide_index=True, width="stretch", column_config=CONFIG_TABLA,
                     height=480)
        if len(q) > 1000:
            st.caption(f"Se muestran 1,000 de {len(q):,} resultados. Usa los filtros para acotar.")

# ============================================================
# COMPARAR
# ============================================================
with tab_comparar:
    seccion("Comparar", "Compara universidades, escuelas e institutos",
            "Título que obtienes, duración, costo, ubicación y perfil de egreso, lado a lado", "comparar_tab")
    comparador("ENFERMERÍA", "TODAS", "tab")

# ============================================================
# PARA COLEGIOS
# ============================================================
with tab_colegios:
    seccion(1, "Cómo funciona", "De la duda a un plan concreto en una clase de tutoría", "como")
    pasos = [("🧭", "El estudiante hace el test", "24 actividades en 4 pasos, desde el celular o la sala de cómputo."),
             ("🤖", "La IA interpreta su perfil", "Claude explica sus intereses y sugiere carreras reales del Perú."),
             ("🗺️", "Ve dónde estudiar", "Mapa con instituciones públicas y privadas de su región y su web."),
             ("📄", "El tutor recibe el reporte", "Para conversar con el estudiante y su familia.")]
    for col, (ic, tit, txt) in zip(st.columns(4), pasos):
        with col, st.container(border=True, key=f"card_paso_{tit[:6]}"):
            st.markdown(f"<div style='font-size:1.8rem'>{ic}</div><div style='font-weight:700;color:{AZUL_OSCURO}'>"
                        f"{tit}</div><div style='color:{GRIS};font-size:.9rem'>{txt}</div>", unsafe_allow_html=True)

    seccion(2, "Planes", "El estudiante siempre usa Rumbo gratis", "planes")
    planes = [("Estudiante", "Gratis", "", ["Test vocacional", "Carreras sugeridas", "Mapas y enlaces"]),
              ("Colegio", "S/ 8", "por estudiante al año", ["Todo lo del plan Estudiante", "Reportes por aula",
                                                            "Charla guiada para tutores"]),
              ("UGEL / DRE", "S/ 2,500", "por UGEL al año", ["Panel de tendencias vocacionales",
                                                             "Brechas de oferta por provincia", "Soporte"])]
    for col, (nombre, precio, unidad, items) in zip(st.columns(3), planes):
        with col, st.container(border=True, key=f"card_plan_{nombre[:5]}"):
            st.markdown(f"<div class='eyebrow' style='color:{AZUL};font-weight:700;letter-spacing:.12em;"
                        f"font-size:.75rem;text-transform:uppercase'>{nombre}</div>"
                        f"<div style='font-size:2rem;font-weight:800;color:{AZUL_OSCURO}'>{precio}</div>"
                        f"<div style='color:{GRIS};font-size:.85rem;margin-bottom:8px'>{unidad or '&nbsp;'}</div>",
                        unsafe_allow_html=True)
            st.markdown("\n".join(f"- {i}" for i in items))

    seccion(3, "Datos y privacidad", "Información oficial y abierta", "datos")
    st.markdown("- **SUNEDU:** programas de las universidades licenciadas.\n"
                "- **MINEDU, Censo Educativo 2025:** institutos y escuelas de educación superior tecnológica y "
                "pedagógica (Ley 30512), escuelas de arte y CETPRO, con su gestión y ubicación.\n"
                "- **Mapa:** límites departamentales del Perú (GeoJSON abierto).\n"
                "- **Privacidad:** no guardamos respuestas ni datos personales de los estudiantes.")

st.markdown('<div class="pie">Rumbo · Orientación vocacional con datos abiertos del Perú · '
            'Proyecto final Diplomatura Q-Lab PUCP 2026</div>', unsafe_allow_html=True)
