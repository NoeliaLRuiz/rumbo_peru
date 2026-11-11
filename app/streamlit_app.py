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
from ai.test_vocacional import (AYUDAS, DIMENSIONES, EJEMPLO, OPCIONES, POR_SECCION, PREGUNTAS,  # noqa: E402
                                SECCIONES_TEST,
                                codigo_holland, puntajes, ranking_areas)

LOGO_SVG = (Path(__file__).resolve().parent / "logo_rumbo.svg").read_text(encoding="utf-8")
LOGO_URI = "data:image/svg+xml;base64," + base64.b64encode(LOGO_SVG.encode()).decode()
st.set_page_config(page_title="Rumbo · Orientación vocacional",
                   page_icon=str(Path(__file__).resolve().parent / "logo_rumbo.svg"), layout="wide")
# La página está en español: así el navegador no ofrece "traducirla" (eso cambiaba "o a la" por "oa la")
st.html("<script>document.documentElement.lang = 'es';"
        "if (!document.querySelector('meta[name=google]')) {const m = document.createElement('meta');"
        "m.name = 'google'; m.content = 'notranslate'; document.head.appendChild(m);}</script>",
        unsafe_allow_javascript=True)

# ============================================================
# Estilo
# ============================================================
# Paleta verde esmeralda (los nombres AZUL_* se mantienen por compatibilidad: hoy son tonos de verde)
AZUL, AZUL_OSCURO, CELESTE, AZUL_SUAVE, GRIS = "#059669", "#064e3b", "#34d399", "#ecfdf5", "#64748b"
AMBAR, AMBAR_OSCURO = "#f59e0b", "#78350f"
COLOR_GESTION = {"Pública": AZUL, "Privada": AMBAR}  # opción 1: azul + ámbar
# Mapa por regiones: de turquesa claro a azul marino
ESCALA_AZUL = [[0, "#f0fdf4"], [0.15, "#d1fae5"], [0.32, "#a7f3d0"], [0.5, "#6ee7b7"], [0.66, "#34d399"],
               [0.82, "#059669"], [1, "#064e3b"]]
N_PASOS = 4  # bloques de preguntas: 6 preguntas por bloque, una de cada tipo de interés

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
.stApp, .stApp p, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5,
.stApp input, .stApp textarea, .stApp button {{font-family: 'Inter', sans-serif;}}
.stApp {{background: #ffffff;}}
.block-container {{padding-top: 0; max-width: 1280px;}}
.stApp {{overflow-x: hidden;}}
header[data-testid="stHeader"] {{background: transparent;}}
[data-testid="stDecoration"] {{display: none;}}
[data-testid="stAppViewContainer"] > .main, [data-testid="stMain"] {{padding-top: 0 !important;}}
[data-testid="stMainBlockContainer"], .block-container {{padding-top: 0 !important;}}
header[data-testid="stHeader"] button, header[data-testid="stHeader"] a, header[data-testid="stHeader"] span
  {{color: #ffffff !important;}}

/* Portada */
/* La portada ocupa todo el ancho de la página, de borde a borde y desde arriba */
/* Verde esmeralda con textura de puntos (evoca un mapa) */
.hero {{background: radial-gradient(rgba(255,255,255,.13) 1.2px, transparent 1.3px) 0 0 / 18px 18px,
        linear-gradient(90deg, #064e3b 0%, #059669 100%); color: #fff;
        margin: -4rem calc(50% - 50vw) 18px; padding: 6.5rem 0 34px; animation: aparecer .6s ease-out;}}
.hero .dentro {{max-width: 1280px; margin: 0 auto; padding: 0 3rem;}}
.hero .top {{display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;}}
.hero .marca {{display: flex; align-items: center; gap: 14px;}}
.hero .marca img {{width: 74px; height: 74px; filter: drop-shadow(0 4px 10px rgba(0,0,0,.25));}}
.hero .marca .nombre {{font-size: 3.6rem; font-weight: 800; letter-spacing: .01em; line-height: 1;}}
.hero .marca .lema {{font-size: .95rem; opacity: .9; font-weight: 500; letter-spacing: .04em; margin-top: 4px;}}
.hero .chip {{background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.28); border-radius: 999px;
             padding: 4px 12px; font-size: .78rem; margin-left: 6px;}}
.hero h1 {{color: #fff; font-size: 1.9rem; font-weight: 700; line-height: 1.2; margin: 22px 0 8px;}}
.hero p.sub {{font-size: 1.08rem; opacity: .92; max-width: 760px; margin: 0;}}
.hero .stats {{display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-top: 22px;}}
.hero .stat {{background: rgba(255,255,255,.12); border: 1px solid rgba(255,255,255,.25); border-radius: 14px;
             padding: 12px 16px;}}
.hero .stat b {{display: block; font-size: 1.6rem; font-weight: 800;}}
.hero .stat span {{font-size: .82rem; opacity: .9;}}

/* Secciones */
/* Cada sección empieza con una franja propia, bien separada de la anterior */
.sec {{margin: 52px 0 20px; padding: 18px 22px; scroll-margin-top: 90px; position: relative;
      background: linear-gradient(90deg, {AZUL_SUAVE} 0%, #ffffff 85%); border: 1px solid #d1fae5;
      border-left: 6px solid {AZUL}; border-radius: 16px; animation: aparecer .5s ease-out;}}
.sec::before {{content: ""; position: absolute; left: 0; right: 0; top: -28px; border-top: 1px dashed #cbd5e1;}}
.sec .eyebrow {{color: {AZUL}; font-weight: 700; letter-spacing: .14em; font-size: .72rem; text-transform: uppercase;}}
.sec h2 {{color: #0f172a; font-weight: 800; font-size: 1.7rem; margin: 2px 0 2px; padding: 0;}}
.sec p {{color: {GRIS}; margin: 0; font-size: .98rem;}}
/* Portada del test: franja de título, consejos y tarjetas de secciones */
.banda {{background: linear-gradient(90deg, {AZUL_OSCURO}, {AZUL}); color: #fff; text-align: center;
        font-weight: 800; font-size: 1.9rem; padding: 14px 18px; border-radius: 14px; margin: 8px 0 22px;}}
.tips {{background: #ecfdf5; border-radius: 16px; padding: 18px 16px; display: flex; flex-direction: column; gap: 22px;}}
.tip {{text-align: center; color: #334155; font-size: .97rem;}}
.tip .ico {{width: 74px; height: 74px; margin: 0 auto 8px; border-radius: 50%; background: #ffffff;
            border: 2px solid #ffffff; display: flex; align-items: center; justify-content: center;
            box-shadow: 0 4px 12px rgba(5,150,105,.12);}}
.tip .ico svg {{width: 46px; height: 46px; filter: drop-shadow(0 2px 3px rgba(0,0,0,.12));}}
.intro {{font-size: 1.05rem; color: #1f2937; margin: 0 0 10px; text-align: justify;}}
.secs {{display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin: 10px 0 16px;}}
.sec-card .etq {{display: inline-block; background: #94a3b8; color: #fff; font-weight: 700; font-size: .85rem;
                padding: 3px 14px; border-radius: 6px 6px 0 0;}}
.sec-card .cuerpo {{background: #f1f5f9; border-radius: 0 12px 12px 12px; padding: 14px; color: {AZUL};
                   font-weight: 700; min-height: 92px;}}
.sec-card .ico {{display: block; font-size: 1.5rem; margin-bottom: 4px;}}
.sec-card.activa .etq {{background: {AZUL};}} .sec-card.activa .cuerpo {{background: {AZUL_SUAVE};
                       border: 2px solid {AZUL};}}
.sec-card.hecha .etq {{background: {AMBAR}; color: {AMBAR_OSCURO};}}
.secs.pasos .cuerpo {{min-height: 70px; font-size: .9rem;}}
.callout {{background: {AZUL}; color: #fff; border-radius: 14px; padding: 12px 16px; font-size: .95rem; margin-bottom: 14px;}}
.pregunta-sec {{font-size: 1.45rem; font-weight: 800; color: {AZUL_OSCURO}; margin: 8px 0 2px;}}
.nota {{color: {GRIS}; margin-bottom: 10px;}}
.fila-region {{display: grid; grid-template-columns: 110px 1fr 38px; align-items: center; gap: 8px;
               padding: 5px 6px; border-radius: 8px; font-size: .9rem;}}
.fila-region .barra {{background: #f1f5f9; border-radius: 999px; height: 10px; overflow: hidden;}}
.fila-region .barra i {{display: block; height: 100%; background: {AZUL}; border-radius: 999px;}}
.fila-region .num {{text-align: right; font-weight: 700; color: {AZUL_OSCURO};}}
.fila-region.actual {{background: {AZUL_SUAVE}; font-weight: 700;}}
.dato.adm {{background: #fef3c7; border-radius: 10px; padding: 6px 10px; margin: 6px 0;}}
.dato.adm small {{color: {GRIS};}}
.sello {{display: inline-block; background: #fef3c7; color: {AMBAR_OSCURO}; border: 1px solid #fcd34d;
          padding: 3px 10px; border-radius: 999px; font-size: .78rem; font-weight: 700; margin: 0 4px 4px 0;}}
.destacadas {{background: linear-gradient(90deg, {AZUL_SUAVE}, #ffffff); border: 2px solid {AZUL};
             border-radius: 16px; padding: 14px 18px; margin: 4px 0 16px;}}
.destacadas .tit {{font-weight: 800; font-size: 1.15rem; color: {AZUL_OSCURO};}}
.destacadas .sub {{color: {GRIS}; font-size: .88rem; margin-bottom: 10px;}}
.destacadas .lista {{display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 10px;}}
.destacadas .op {{display: flex; gap: 10px; align-items: flex-start; background: #fff; border: 1px solid #d1fae5;
                 border-radius: 12px; padding: 10px;}}
.inst-nombre {{font-weight: 800; font-size: 1.28rem; color: {AZUL_OSCURO}; line-height: 1.25;}}

/* Navegación de resultados */
.nav {{display: flex; gap: 6px; flex-wrap: wrap; padding: 10px 12px; background: {AZUL_SUAVE};
      border: 1px solid #d1fae5; border-radius: 14px; margin: 4px 0 6px;}}
.nav a {{color: {AZUL_OSCURO} !important; text-decoration: none; font-weight: 600; font-size: .88rem;
        padding: 6px 12px; border-radius: 10px; transition: all .15s;}}
.nav a:hover {{background: {AZUL}; color: #fff !important;}}

/* Indicadores */
.kpis {{display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 6px 0 14px;}}
.kpi {{background: #fff; border: 1px solid #d1fae5; border-top: 4px solid {AZUL}; border-radius: 14px;
      padding: 12px 16px; box-shadow: 0 4px 14px rgba(5,150,105,.06);}}
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
.pill.tipo {{background: {AZUL_SUAVE}; color: {AZUL_OSCURO}; border: 1px solid #a7f3d0;}}
.leyenda {{font-size: .85rem; color: {GRIS};}}
.leyenda i {{display: inline-block; width: 11px; height: 11px; border-radius: 50%; margin: 0 5px 0 12px;
            vertical-align: middle;}}
.dato {{font-size: .92rem; margin: 4px 0;}} .dato b {{color: {AZUL_OSCURO};}}
[class*="st-key-card"] {{background: #fff; border-color: #d1fae5 !important; border-radius: 16px !important;
                        transition: transform .2s, box-shadow .2s; animation: aparecer .5s ease-out;}}
[class*="st-key-card"]:hover {{transform: translateY(-3px); box-shadow: 0 14px 28px rgba(5,150,105,.14);
                              border-color: #6ee7b7 !important;}}
[class*="st-key-mapa"] {{border-radius: 16px !important; border-color: #d1fae5 !important; background: #fff;}}
.stTabs [data-baseweb="tab-list"] {{gap: 4px; border-bottom: 1px solid #d1fae5;}}
.stTabs [data-baseweb="tab"] {{font-weight: 600; padding: 10px 16px;}}
.pie {{margin-top: 48px; padding: 18px 0; border-top: 1px solid #d1fae5; color: {GRIS}; font-size: .85rem;
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
    texto = "Pública · gratuita o de bajo costo" if g == "Pública" else "Privada"
    return f'<span class="pill {"pub" if g == "Pública" else "pri"}">{texto}</span>'


def sello(r) -> str:
    """Sello de prestigio basado en datos oficiales (no en opiniones)."""
    anios = getattr(r, "licencia_anios", None)
    if r.tipo == "Universidad" and pd.notna(anios):
        nivel = {10: "la licencia máxima", 8: "licencia de 8 años", 6: "licencia de 6 años"}.get(int(anios), "")
        estrellas = {10: "★★★", 8: "★★", 6: "★"}.get(int(anios), "")
        return (f"<span class='sello' title='SUNEDU otorga la licencia por 6, 8 o 10 años según la calidad "
                f"demostrada. 10 años es la máxima.'>🏅 Licencia SUNEDU {int(anios)} años {estrellas}</span>"
                if nivel else "")
    if "Ley 30512" in str(r.certificacion) or str(r.tipo).startswith("Escuela superior"):
        return "<span class='sello' title='Las escuelas de educación superior de la Ley 30512 están licenciadas por el MINEDU'>🏅 Escuela de Educación Superior licenciada</span>"
    if "rango universitario" in str(r.certificacion):
        return "<span class='sello'>🏅 Escuela nacional con rango universitario</span>"
    return ""


def orden_prestigio(df: pd.DataFrame) -> pd.DataFrame:
    """Públicas primero; dentro de cada grupo, más años de licencia primero."""
    lic = df["licencia_anios"] if "licencia_anios" in df else pd.Series(0, index=df.index)
    return (df.assign(_pub=df["gestion"] != "Pública", _lic=-lic.fillna(0))
              .sort_values(["_pub", "_lic", "tipo", "institucion"]).drop(columns=["_pub", "_lic"]))


SINEACE = "https://app.sineace.gob.pe/buscador/acreditacion.aspx"

# Íconos a color para los consejos del test (paleta de la app: verde, ámbar y turquesa)
ICONOS_TIPS = {
    "reloj": '<svg viewBox="0 0 48 48"><rect x="19" y="3" width="10" height="5" rx="2" fill="#f59e0b"/>'
             '<circle cx="24" cy="27" r="16" fill="#059669"/><circle cx="24" cy="27" r="12" fill="#ffffff"/>'
             '<path d="M24 19v8l5.5 3.5" fill="none" stroke="#f59e0b" stroke-width="3" stroke-linecap="round"/>'
             '<circle cx="24" cy="27" r="2" fill="#064e3b"/></svg>',
    "sinceridad": '<svg viewBox="0 0 48 48"><rect x="6" y="21" width="9" height="20" rx="2" fill="#059669"/>'
                  '<path d="M15 39c3 2 6 2.5 10 2.5h7c2 0 3.5-1.3 3.8-3.2l2.1-11c.4-2.2-1.3-4.3-3.6-4.3H28l1.5-7'
                  'c.5-2.4-1.3-4.5-3.7-4.5L19 21h-4z" fill="#fbbf24" stroke="#d97706" stroke-width="1.5" '
                  'stroke-linejoin="round"/><path d="M38 9l3-3M42 15h3M35 5V2" stroke="#14b8a6" '
                  'stroke-width="2.6" stroke-linecap="round"/></svg>',
    "privacidad": '<svg viewBox="0 0 48 48"><path d="M24 4l16 6.5v11.5c0 10.5-7 18-16 22C15 40 8 32.5 8 22V10.5z" '
                  'fill="#059669"/><path d="M24 8.5l12 4.9v8.6c0 8-5.2 13.8-12 17V8.5z" fill="#047857"/>'
                  '<rect x="17" y="21" width="14" height="11" rx="2.5" fill="#fbbf24"/>'
                  '<path d="M19.5 21v-3a4.5 4.5 0 0 1 9 0v3" fill="none" stroke="#fbbf24" stroke-width="2.6"/>'
                  '<circle cx="24" cy="26.5" r="1.8" fill="#78350f"/></svg>',
    "ubicacion": '<svg viewBox="0 0 48 48"><ellipse cx="24" cy="44" rx="9" ry="2.5" fill="#99f6e4"/>'
                 '<path d="M24 43s14-12.5 14-23.5a14 14 0 0 0-28 0C10 30.5 24 43 24 43z" fill="#14b8a6"/>'
                 '<circle cx="24" cy="19.5" r="9.5" fill="#ffffff"/><path d="M16.5 18l7.5-3.6 7.5 3.6-7.5 3.6z" '
                 'fill="#064e3b"/><path d="M19.5 19.6v3c0 1.4 2 2.5 4.5 2.5s4.5-1.1 4.5-2.5v-3l-4.5 2.2z" '
                 'fill="#064e3b"/><path d="M30.5 18.5v4.5" stroke="#f59e0b" stroke-width="1.8" '
                 'stroke-linecap="round"/><circle cx="30.5" cy="23.8" r="1.4" fill="#f59e0b"/></svg>',
}
COLORES_TIPS = ["#fef3c7", "#ffedd5", "#d1fae5", "#ccfbf1"]  # fondo pastel de cada círculo


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
    df["perfil_link"] = [enlace_perfil(n, p, w) for n, p, w in zip(df["institucion"], df["programa"], df["web"])]
    df["admision_link"] = [enlace_admision(n, w) for n, w in zip(df["institucion"], df["web"])]
    logos_web = df["logo_web"] if "logo_web" in df else pd.Series(None, index=df.index)
    df["logo"] = [logo_url(n, w) for n, w in zip(df["nombre_corto"].fillna(df["institucion"]), logos_web)]
    # Miniatura cuadrada con el logo completo (data/miniaturas_logos.py): así no se corta en tablas ni tarjetas
    archivo_mini = RAIZ / "data" / "logos_mini.csv"
    if archivo_mini.exists():
        mini = pd.read_csv(archivo_mini, dtype=str).set_index("codigo")["logo_mini"]
        df["logo"] = df["codigo"].map(mini).fillna(df["logo"])
    return df


@st.cache_data
def cargar_geo() -> dict:
    return json.loads((RAIZ / "data" / "geo" / "peru_departamentos.geojson").read_text(encoding="utf-8"))


def tiene_web(x) -> bool:
    return isinstance(x, str) and x.startswith("http")


def enlace_admision(institucion: str, web) -> str:
    """Enlace a las fechas de admisión vigentes: busca dentro de la web oficial de la institución."""
    if tiene_web(web):
        consulta = f'site:{urlparse(web).netloc.replace("www.", "")} admisión cronograma'
    else:
        consulta = f'"{institucion}" admisión cronograma'
    return "https://www.google.com/search?q=" + quote_plus(consulta)


@st.cache_data
def cargar_admision() -> dict:
    """Meses de admisión verificados a mano (data/admision_manual.csv), con su fuente y fecha de revisión."""
    archivo = RAIZ / "data" / "admision_manual.csv"
    if not archivo.exists():
        return {}
    a = pd.read_csv(archivo, dtype=str).fillna("")
    return {r.codigo: r._asdict() for r in a.itertuples(index=False)}


def enlace_perfil(institucion: str, programa: str, web) -> str:
    """Enlace al perfil de egreso oficial de esa carrera en esa institución: busca dentro de su web oficial
    (site:dominio); si no tiene web registrada, busca por el nombre completo de la institución."""
    carrera = "" if str(programa).startswith(SIN_CARRERA) else str(programa).split("(")[0].replace(" - ", " ").title()
    if tiene_web(web):
        consulta = f'site:{urlparse(web).netloc.replace("www.", "")} "perfil de egreso" {carrera}'
    else:
        consulta = f'"{institucion}" "perfil de egreso" {carrera}'
    return "https://www.google.com/search?q=" + quote_plus(consulta.strip())


PALABRAS_NOMBRE = {"DE", "DEL", "LA", "EL", "Y", "E", "LOS", "LAS", "S.A.C.", "S.A.", "S.R.L.", "SAC"}


def logo_url(nombre: str, logo_web) -> str:
    """Logo de la institución tomado de su web oficial (data/obtener_logos.py).
    Si no hay: un círculo azul con sus iniciales (SVG en línea), para que todas tengan imagen."""
    if tiene_web(logo_web):
        return logo_web
    iniciales = "".join(w[0] for w in str(nombre).upper().split() if w not in PALABRAS_NOMBRE and w[0].isalpha())[:2]
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' width='64' height='64'><circle cx='32' cy='32' r='32' "
           f"fill='#059669'/><text x='32' y='41' font-family='Arial' font-size='24' font-weight='700' "
           f"fill='white' text-anchor='middle'>{iniciales or '?'}</text></svg>")
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def logo_html(r, alto: int = 56, ancho_max: int = 170) -> str:
    """Logo con alto fijo y ancho proporcional (los logos horizontales no se encogen)."""
    return (f"<img src='{r.logo}' style='height:{alto}px;width:auto;max-width:{ancho_max}px;min-width:{alto}px;"
            f"object-fit:contain;border-radius:10px;background:#fff;border:1px solid #d1fae5;padding:4px;"
            f"vertical-align:middle'>")


COLUMNAS_TABLA = ["logo", "institucion", "tipo", "gestion", "programa", "departamento", "provincia", "distrito",
                  "perfil_link", "web", "buscar"]
CONFIG_TABLA = {
    "logo": st.column_config.ImageColumn("Logo", width="small"),
    "institucion": "Institución", "tipo": "Tipo", "gestion": "Gestión", "programa": "Carrera",
    "departamento": "Región", "provincia": "Provincia", "distrito": "Distrito",
    "perfil_link": st.column_config.LinkColumn("Perfil de egreso", display_text="Ver perfil ↗",
                                               help="Perfil de egreso oficial de esta carrera en la web de la institución"),
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
    regiones_geo = [f["properties"]["NOMBDEP"] for f in GEO["features"]]
    if df.empty:  # sin resultados: todas las regiones en cero
        agg = pd.DataFrame(0, index=regiones_geo, columns=["ofertas", "instituciones", "publica"])
    else:
        agg = (df.groupby("departamento")
                 .agg(ofertas=("programa", "size"), instituciones=("institucion", "nunique"),
                      publica=("gestion", lambda s: round((s == "Pública").mean() * 100, 1)))
                 .reindex(regiones_geo).fillna(0))
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
                .agg(programas=("programa", list), perfiles=("perfil_link", list), web=("web", "first"),
                     buscar=("buscar", "first"), logo=("logo", "first"))
                .reset_index())
    mapa = folium.Map(tiles="OpenStreetMap", control_scale=True)
    mapa.fit_bounds([[sedes["lat"].min(), sedes["lon"].min()], [sedes["lat"].max(), sedes["lon"].max()]],
                    max_zoom=13)
    Fullscreen(position="topright", title="Pantalla completa", title_cancel="Salir").add_to(mapa)
    grupo = MarkerCluster(options={"showCoverageOnHover": False}).add_to(mapa)
    for r in sedes.itertuples():
        carreras = sorted(dict(zip(r.programas, r.perfiles)).items())
        lista = "".join(f'<li>{p.title()} · <a href="{link}" target="_blank">perfil de egreso ↗</a></li>'
                        for p, link in carreras[:6])
        extra = f"<li>… y {len(carreras) - 6} más</li>" if len(carreras) > 6 else ""
        enlaces = ((f'<a href="{r.web}" target="_blank">Ir a la web ↗</a> · ' if tiene_web(r.web) else "")
                   + f'<a href="{r.buscar}" target="_blank">Buscar ↗</a>')
        folium.CircleMarker(
            [r.lat, r.lon], radius=8, color="#ffffff", weight=2, fill=True,
            fill_color=COLOR_GESTION[r.gestion], fill_opacity=0.95,
            tooltip=f"{r.institucion} · {r.gestion}",
            popup=folium.Popup(f"<div style='font-family:Inter,sans-serif;font-size:13px'>"
                               f"<div style='margin-bottom:4px'>{logo_html(r, 30, 90)}</div>"
                               f"<div style='font-weight:800;font-size:15px;color:{AZUL_OSCURO};"
                               f"line-height:1.25;margin-bottom:2px'>{r.institucion}</div>"
                               f"<span style='color:{GRIS}'>{r.tipo} · {r.gestion}<br>"
                               f"{r.distrito.title()}, {r.provincia.title()}</span>"
                               f"<ul style='padding-left:16px;margin:6px 0'>{lista}{extra}</ul>{enlaces}</div>",
                               max_width=340),
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
    for k in ("d_prog", "d_region", "d_gestion", "d_similares", "nav_sec"):
        ss.pop(k, None)
    ss["sec"] = 0


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


SECCIONES_RES = [
    ("Tu perfil de intereses", "Basado en el modelo RIASEC de John Holland"),
    ("Tus áreas más afines", "Qué tanto se parecen tus intereses a cada campo de estudio"),
    ("Carreras sugeridas para ti", "Primero las que puedes estudiar en {region}"),
    ("¿Dónde puedo estudiarlo?", "Instituciones públicas y privadas, con su web y su perfil de egreso"),
    ("Compara instituciones y perfil de egreso", "¿Qué obtienes al terminar en cada una?"),
    ("Comparte tu resultado", "Descarga el reporte y conversa con tu tutor o tu familia"),
]
ETIQUETAS_SEC = ["01 · Perfil", "02 · Áreas", "03 · Carreras", "04 · Dónde estudiar", "05 · Comparar", "06 · Reporte"]


def ir_sec(n: int):
    ss["sec"] = n
    ss["nav_sec"] = ETIQUETAS_SEC[n]


def nav_cambio():
    if ss.get("nav_sec") in ETIQUETAS_SEC:
        ss["sec"] = ETIQUETAS_SEC.index(ss["nav_sec"])
    else:  # si se vuelve a hacer clic en el paso activo, se mantiene
        ss["nav_sec"] = ETIQUETAS_SEC[ss.get("sec", 0)]


def ver_donde(programa: str):
    ss["d_prog"] = programa
    ir_sec(3)


@st.cache_data(show_spinner="Preparando el perfil de egreso...")
def perfil_cacheado(programa: str, nivel: str, area_id: str) -> dict:
    return perfil_egreso(programa, nivel, area_id)


# ============================================================
# Comparador
# ============================================================
@st.cache_data
def carreras_por_sector(version: float) -> dict:
    """Para cada sector (área), sus carreras ordenadas por cuántos lugares las ofrecen."""
    reales = oferta[~oferta["programa"].str.startswith(SIN_CARRERA)]
    return {a: reales[reales["area"] == a]["programa"].value_counts().to_dict() for a in AREAS}


def elegir_sector_y_carrera(k: str, prog_inicial: str | None = None, permitir_todas: bool = False):
    """Paso 1: el sector (Salud, Educación, …). Paso 2: la carrera dentro de ese sector."""
    por_sector = carreras_por_sector(ARCHIVO_OFERTA.stat().st_mtime)
    sector_inicial = oferta.loc[oferta["programa"] == prog_inicial, "area"].iloc[0] if prog_inicial else None
    sector = st.pills("1 · Elige un sector", list(AREAS), key=f"{k}_sector",
                      default=sector_inicial if sector_inicial in AREAS else None,
                      format_func=lambda a: f"{icono_area(a)} {nombre_area(a)}",
                      required=not permitir_todas)
    if not sector:
        st.caption("Elige un sector para ver sus carreras (o deja todos para explorar toda la oferta).")
        return None, None
    conteo = por_sector[sector]
    opciones = (["TODAS"] if permitir_todas else []) + list(conteo)
    indice = opciones.index(prog_inicial) if prog_inicial in opciones else 0
    carrera = st.selectbox(
        f"2 · Elige la carrera ({len(conteo)} carreras en {nombre_area(sector)})", opciones, index=indice,
        key=f"{k}_carrera_{sector}",
        format_func=lambda p: "Todas las carreras del sector" if p == "TODAS"
        else f"{p.title()} · {conteo[p]:,} lugar{'es' if conteo[p] != 1 else ''}")
    return sector, (None if carrera == "TODAS" else carrera)


def comparador(prog_inicial: str, region_inicial: str, k: str):
    """Compara lado a lado hasta 4 instituciones que ofrecen una carrera, y el perfil de egreso por nivel."""
    _, prog = elegir_sector_y_carrera(k, prog_inicial)
    c2, c4, c3 = st.columns([1, 1, 1])
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
    sub = orden_prestigio(sub.drop_duplicates(["institucion", "tipo", "programa", "distrito"]))
    if sub.empty:
        st.info("No hay instituciones con esta carrera y filtros. Prueba con otra región o con «Ambas».")
        return
    # Por defecto: una de cada combinación tipo × gestión (universidad pública, instituto privado, ...)
    por_defecto = list(sub.groupby(["tipo", "gestion"], sort=False).head(1).index)[:4]
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
            # El nombre es lo principal; el logo va pequeño, como apoyo visual
            st.markdown(f"<div style='margin-bottom:8px'>{logo_html(r, 40, 120)}</div>"
                        f"<div class='inst-nombre'>{r.institucion}</div>"
                        f"<div style='color:{GRIS};font-size:.9rem;margin-bottom:6px'>{r.programa.title()}</div>"
                        f"{pill_gestion(r.gestion)}<span class='pill tipo'>{r.tipo}</span>{sello(r)}"
                        f"<div class='dato'><b>Al egresar:</b> {r.certificacion}</div>"
                        f"<div class='dato'><b>Duración:</b> {r.duracion}</div>"
                        f"<div class='dato'><b>Costo:</b> "
                        f"{'gratuita o de bajo costo' if r.gestion == 'Pública' else 'pensión, consultar'}</div>"
                        f"<div class='dato'><b>Ubicación:</b> {r.distrito.title()}, {r.departamento.title()}</div>",
                        unsafe_allow_html=True)
            adm = cargar_admision().get(r.codigo)
            if adm and adm["meses"]:
                st.markdown(f"<div class='dato adm'>📅 <b>Admisión:</b> {adm['meses']}"
                            + (f" · {adm['detalle']}" if adm["detalle"] else "")
                            + f"<br><small>Fuente: {adm['fuente']} (revisado {adm['revisado']})</small></div>",
                            unsafe_allow_html=True)
                st.link_button("📅 Confirmar fechas de admisión ↗", r.admision_link, width="stretch")
            else:
                st.link_button("📅 Ver fechas de admisión ↗", r.admision_link, width="stretch",
                               help="Busca el cronograma de admisión vigente en la web oficial de la institución")
            st.link_button("Ver su perfil de egreso oficial ↗", r.perfil_link, width="stretch", type="primary")
            if tiene_web(r.web):
                st.link_button("Ir a su web ↗", r.web, width="stretch")
            else:
                st.link_button("Buscar más información ↗", r.buscar, width="stretch")

    izq = st.container()
    with izq:
        st.caption(f"🏅 Los sellos se basan en datos oficiales: años de licencia SUNEDU y licenciamiento MINEDU. "
                   f"¿Quieres saber si una carrera está acreditada? Revísalo en el [buscador de SINEACE]({SINEACE}).")
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


# ============================================================
# Portada
# ============================================================
st.markdown(f"""
<div class="hero"><div class="dentro">
  <div class="top">
    <div class="marca"><img src="{LOGO_URI}" alt="Logo de Rumbo">
      <div><div class="nombre">Rumbo</div><div class="lema">ORIENTACIÓN VOCACIONAL · PERÚ</div></div></div>
    <div><span class="chip">Datos SUNEDU</span><span class="chip">Censo Educativo MINEDU 2025</span></div>
  </div>
  <h1>Encuentra qué estudiar y dónde, cerca de casa</h1>
  <p class="sub">Test vocacional gratuito que te muestra todas tus opciones reales en el Perú: universidades,
     institutos, escuelas superiores, pedagógicos y CETPRO, públicos y privados.</p>
  <div class="stats">
    <div class="stat"><b>{len(oferta):,}</b><span>ofertas de estudio</span></div>
    <div class="stat"><b>{oferta['institucion'].nunique():,}</b><span>instituciones</span></div>
    <div class="stat"><b>{oferta['departamento'].nunique()}</b><span>regiones</span></div>
    <div class="stat"><b>{(oferta['gestion'] == 'Pública').mean():.0%}</b><span>en instituciones públicas</span></div>
  </div>
</div></div>""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown(f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:6px'>"
                f"<img src='{LOGO_URI}' width='44'><span style='font-size:1.9rem;font-weight:800;"
                f"color:{AZUL_OSCURO}'>Rumbo</span></div>", unsafe_allow_html=True)
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

    # ---- Paso 0: portada del test ----
    if paso == 0:
        st.markdown('<div class="banda">Test de intereses vocacionales</div>', unsafe_allow_html=True)
        izq, der = st.columns([1, 2.2], gap="large")
        with izq:
            consejos = [(ICONOS_TIPS["reloj"], "Dura unos <b>5 minutos</b>."),
                        (ICONOS_TIPS["sinceridad"], "Responde con sinceridad. Así tus resultados serán confiables."),
                        (ICONOS_TIPS["privacidad"], "No guardamos tus respuestas ni tus datos personales."),
                        (ICONOS_TIPS["ubicacion"],
                         "Al final verás <b>dónde estudiar</b> cerca de casa, en instituciones públicas y privadas.")]
            st.markdown('<div class="tips">' + "".join(
                f'<div class="tip"><div class="ico" style="background:{COLORES_TIPS[n]}">{i}</div><div>{t}</div></div>'
                for n, (i, t) in enumerate(consejos)) + "</div>", unsafe_allow_html=True)
        with der:
            st.markdown(
                "<p class='intro'>Rumbo te ayuda a descubrir qué <b>carreras técnicas o universitarias</b> van con tus "
                "intereses y <b>dónde estudiarlas</b> en tu región: universidades, institutos, escuelas superiores "
                "y CETPRO, públicos y privados.</p>"
                f"<p class='intro'>El test tiene <b>{len(PREGUNTAS)} preguntas</b> divididas en "
                f"<b>{len(SECCIONES_TEST)} secciones</b>:</p>"
                '<div class="secs">' + "".join(
                    f'<div class="sec-card"><div class="etq">Sección {n}</div>'
                    f'<div class="cuerpo"><span class="ico">{ico}</span>{titulo}</div></div>'
                    for n, (titulo, ico, _) in enumerate(SECCIONES_TEST, start=1)) + "</div>",
                unsafe_allow_html=True)
            with st.container(border=True, key="card_inicio"):
                c1, c2 = st.columns([1, 2])
                ss["depto"] = c1.selectbox("¿En qué región vives?", departamentos,
                                           index=departamentos.index(ss["depto"]), format_func=str.title)
                ss["sobre_mi"] = c2.text_input("Cuéntanos qué te gusta hacer (opcional)", value=ss["sobre_mi"],
                                               max_chars=600, placeholder="Ej.: me gusta ayudar a mis compañeros…")
                b1, b2 = st.columns(2)
                b1.button("Iniciar el test →", type="primary", on_click=ir_a, args=(1,), width="stretch")
                b2.button("Ver un ejemplo (demo)", on_click=usar_demo, width="stretch")

    # ---- Secciones 1-4: preguntas ----
    elif 1 <= paso <= N_PASOS:
        titulo_sec, ico_sec, _ = SECCIONES_TEST[paso - 1]
        st.markdown('<div class="banda">Test de intereses vocacionales</div>', unsafe_allow_html=True)
        st.markdown('<div class="secs pasos">' + "".join(
            f'<div class="sec-card {"activa" if n == paso else "hecha" if n < paso else ""}">'
            f'<div class="etq">Sección {n}</div><div class="cuerpo"><span class="ico">{ico}</span>{t}</div></div>'
            for n, (t, ico, _) in enumerate(SECCIONES_TEST, start=1)) + "</div>", unsafe_allow_html=True)
        st.progress(paso / N_PASOS, text=f"Sección {paso} de {N_PASOS}")
        st.markdown(f"<div class='pregunta-sec'>{ico_sec} {titulo_sec}</div>"
                    "<div class='nota'>Marca cuánto te gustaría, aunque nunca lo hayas hecho. "
                    "No hay respuestas buenas ni malas.</div>", unsafe_allow_html=True)
        indices = list(range((paso - 1) * POR_SECCION, paso * POR_SECCION))
        cols = st.columns(2)
        for n, i in enumerate(indices):
            with cols[n % 2], st.container(border=True, key=f"card_q{i}"):
                actual = ss["resp"][i]
                valor = st.radio(f"**{PREGUNTAS[i][1]}**", list(OPCIONES), format_func=OPCIONES.get,
                                 horizontal=True, index=list(OPCIONES).index(actual) if actual else None,
                                 key=f"w{i}", help=AYUDAS[i] or None)
                ss["resp"][i] = valor
        faltan = sum(ss["resp"][i] is None for i in indices)
        b1, _, b2 = st.columns([1, 2, 1])
        b1.button("← Atrás", on_click=ir_a, args=(paso - 1,), width="stretch")
        if paso < N_PASOS:
            b2.button("Siguiente sección →", type="primary", disabled=faltan > 0, on_click=ir_a, args=(paso + 1,),
                      width="stretch")
        else:
            b2.button("Ver mis resultados →", type="primary", disabled=faltan > 0, on_click=calcular_resultado,
                      width="stretch")
        if faltan:
            st.caption(f"Responde las {faltan} preguntas que faltan para continuar.")

    # ---- Resultados: una sección a la vez, con Anterior / Siguiente ----
    elif ss.get("resultado"):
        res = ss["resultado"]
        punt, ranking, rec, depto_est = res["punt"], res["ranking"], res["rec"], res["depto"]
        if ss.pop("celebrar", False):
            st.balloons()
            st.toast("¡Listo! Este es tu perfil 🎉")
        en_region = oferta[oferta["departamento"] == depto_est]["programa"].value_counts()
        carreras = sorted(rec["carreras"], key=lambda c: -en_region.get(c["programa"], 0))
        opciones_prog = list(dict.fromkeys(c["programa"] for c in carreras))
        # Elecciones de "Dónde estudiar" guardadas aparte: se conservan al cambiar de sección
        if ss.get("d_prog") not in opciones_prog:
            ss["d_prog"] = opciones_prog[0]
        ss.setdefault("d_region", depto_est)
        ss.setdefault("d_gestion", "Ambas")
        ss.setdefault("d_similares", False)
        sec = ss.setdefault("sec", 0)

        # Barra de pasos (se puede saltar a cualquier sección)
        ss.setdefault("nav_sec", ETIQUETAS_SEC[sec])
        st.segmented_control("Tus resultados", ETIQUETAS_SEC, key="nav_sec", required=True,
                             on_change=nav_cambio, label_visibility="collapsed", width="stretch")
        st.progress((sec + 1) / len(SECCIONES_RES), text=f"Sección {sec + 1} de {len(SECCIONES_RES)}")

        def filtro_donde():
            prog, region, gestion = ss["d_prog"], ss["d_region"], ss["d_gestion"]
            area_prog = oferta.loc[oferta["programa"] == prog, "area"].iloc[0]
            base = oferta[oferta["area"] == area_prog] if ss["d_similares"] else oferta[oferta["programa"] == prog]
            if gestion != "Ambas":
                base = base[base["gestion"] == gestion]
            sel = base[base["departamento"] == region] if region != "TODAS" else base
            return prog, region, gestion, area_prog, base, sel

        titulo, subtitulo = SECCIONES_RES[sec]
        seccion(sec + 1, titulo, subtitulo.format(region=depto_est.title()), f"res{sec}")

        # 01 Perfil
        if sec == 0:
            izq, der = st.columns([1, 1], gap="large")
            with izq:
                st.markdown(f'<div class="perfil">{codigo_holland(punt)}</div>', unsafe_allow_html=True)
                st.write(rec["perfil"])
                st.markdown("".join(f"<span class='pill tipo'>{f}</span>" for f in rec["fortalezas"]),
                            unsafe_allow_html=True)
                st.info("**Siguiente paso:** " + rec["siguiente_paso"])
                st.caption("Recomendación generada con IA y validada contra los datos oficiales."
                           if rec.get("fuente") == "ia" else "Recomendación generada con reglas del modelo RIASEC.")
            with der, st.container(border=True, key="card_radar"):
                etiquetas = [DIMENSIONES[d][0] for d in punt] + [DIMENSIONES[next(iter(punt))][0]]
                valores = list(punt.values()) + [next(iter(punt.values()))]
                radar = go.Figure(go.Scatterpolar(
                    r=valores, theta=etiquetas, fill="toself", line={"color": AZUL, "width": 2.5},
                    fillcolor="rgba(52,211,153,.30)", marker={"size": 7, "color": AZUL_OSCURO},
                    hovertemplate="%{theta}: %{r:.0f}/100<extra></extra>"))
                radar.update_layout(polar={"radialaxis": {"range": [0, 100], "showticklabels": False,
                                                          "gridcolor": "#d1fae5"},
                                           "angularaxis": {"gridcolor": "#d1fae5"}, "bgcolor": "#fff"},
                                    margin={"l": 50, "r": 50, "t": 25, "b": 25}, height=330, showlegend=False,
                                    font={"family": "Inter", "size": 13})
                st.plotly_chart(radar, width="stretch", config={"displayModeBar": False})
                st.caption("Cuanto más lejos del centro, más te interesan ese tipo de actividades.")

        # 02 Áreas
        elif sec == 1:
            for col, (a, s_) in zip(st.columns(4), ranking[:4]):
                with col, st.container(border=True, key=f"card_area_{a}"):
                    st.markdown(f"<div style='font-size:2rem'>{icono_area(a)}</div>"
                                f"<div style='font-weight:700;color:{AZUL_OSCURO};min-height:2.6rem'>"
                                f"{AREAS[a]['nombre']}</div>", unsafe_allow_html=True)
                    st.progress(min(s_ / 100, 1.0), text=f"Afinidad {s_:.0f}/100")
            st.caption("La barra muestra qué tanto se parecen tus intereses a lo que se hace en cada área.")
            otras = ", ".join(AREAS[a]["nombre"] for a, _ in ranking[4:7])
            st.caption(f"Otras áreas con algo de afinidad: {otras}.")

        # 03 Carreras
        elif sec == 2:
            cols = st.columns(3)
            for n, c in enumerate(carreras):
                with cols[n % 3], st.container(border=True, key=f"card_prog_{n}"):
                    lugares = int(en_region.get(c["programa"], 0))
                    donde = (f"<div class='dato'><b>{lugares}</b> lugares en {depto_est.title()}</div>" if lugares
                             else f"<div class='dato'>No se ofrece en {depto_est.title()}: mira otras regiones</div>")
                    st.markdown(f"<div style='font-weight:800;font-size:1.05rem;color:{AZUL_OSCURO}'>"
                                f"{icono_area(c['area_id'])} {c['programa'].title()}</div>"
                                f"<span class='pill tipo'>{c['nivel'].capitalize()}</span>"
                                f"<span class='pill tipo'>{nombre_area(c['area_id'])}</span>"
                                f"<p style='margin:8px 0;font-size:.93rem'>{c['por_que']}</p>{donde}",
                                unsafe_allow_html=True)
                    st.button("Ver dónde estudiar →", key=f"ver_{n}", on_click=ver_donde, args=(c["programa"],),
                              width="stretch")

        # 04 Dónde estudiar
        elif sec == 3:
            f1, f2, f3, f4 = st.columns([2, 1, 1, 1])
            ss["d_prog"] = f1.selectbox(
                "Carrera", opciones_prog, index=opciones_prog.index(ss["d_prog"]), key="w_prog",
                format_func=lambda p: f"{p.title()} ({en_region.get(p, 0)} en {depto_est.title()})")
            regiones = ["TODAS"] + departamentos
            ss["d_region"] = f2.selectbox("Región", regiones, index=regiones.index(ss["d_region"]), key="w_reg",
                                          format_func=str.title)
            gestiones = ["Ambas", "Pública", "Privada"]
            ss["d_gestion"] = f3.selectbox("Gestión", gestiones, index=gestiones.index(ss["d_gestion"]),
                                           key="w_gest")
            f4.markdown("<div style='height:1.9rem'></div>", unsafe_allow_html=True)
            ss["d_similares"] = f4.toggle("Carreras parecidas", value=ss["d_similares"], key="w_sim",
                                          help="Incluye otras carreras de la misma área")
            prog, region, gestion, area_prog, base, sel = filtro_donde()
            kpis([(f"{len(sel):,}", "lugares encontrados"),
                  (f"{int((sel['gestion'] == 'Pública').sum()):,}", "en instituciones públicas"),
                  (f"{int((sel['gestion'] == 'Privada').sum()):,}", "en instituciones privadas"),
                  (f"{int(sel['web'].notna().sum()):,}", "con web oficial")], claro_desde=2)
            publicas = orden_prestigio(sel[sel["gestion"] == "Pública"]).drop_duplicates("institucion").head(3)
            if not publicas.empty:
                st.markdown("<div class='destacadas'><div class='tit'>🏛️ Opciones públicas cerca de ti</div>"
                            "<div class='sub'>Educación gratuita o de bajo costo, ordenadas por prestigio oficial</div>"
                            "<div class='lista'>" + "".join(
                                f"<div class='op'>{logo_html(r, 34, 90)}<div><b>{r.institucion}</b><br>"
                                f"<small>{r.distrito.title()} · {r.tipo}</small><br>{sello(r)}</div></div>"
                                for r in publicas.itertuples()) + "</div></div>", unsafe_allow_html=True)
            izq, der = st.columns([3, 2], gap="large")
            with izq, st.container(border=True, key="mapa_donde"):
                st.markdown(f"**Mapa de instituciones · {region.title()}**")
                if sel.empty:
                    st.warning("No hay oferta con esos filtros. Prueba con «Carreras parecidas» o con otra región.")
                else:
                    mapa_instituciones(sel, key=f"mapa_donde_{prog}_{region}_{gestion}_{ss['d_similares']}")
            with der, st.container(border=True, key="card_otras_regiones"):
                st.markdown(f"**¿En qué regiones se ofrece?**")
                st.caption("Las regiones con más lugares para estudiar esta carrera.")
                por_region = base["departamento"].value_counts().head(8)
                maximo = int(por_region.max()) if len(por_region) else 1
                st.markdown("".join(
                    f"<div class='fila-region{' actual' if dep == region else ''}'>"
                    f"<span class='nom'>{dep.title()}</span>"
                    f"<span class='barra'><i style='width:{100 * n / maximo:.0f}%'></i></span>"
                    f"<span class='num'>{n}</span></div>" for dep, n in por_region.items()),
                    unsafe_allow_html=True)
            if not sel.empty:
                tabla = orden_prestigio(sel)[COLUMNAS_TABLA]
                tabla["programa"] = tabla["programa"].str.title()
                st.dataframe(tabla, hide_index=True, width="stretch", column_config=CONFIG_TABLA, row_height=56,
                             height=320)

        # 05 Comparar
        elif sec == 4:
            prog, region, *_ = filtro_donde()
            comparador(prog if prog in programas_reales else programas_reales[0], region, "res")

        # 06 Reporte
        else:
            prog, region, gestion, _, _, sel = filtro_donde()
            tabla_rep = orden_prestigio(sel).head(30)
            reporte = (f"# Reporte vocacional - Rumbo\n\nPerfil: {codigo_holland(punt)}\n\n{rec['perfil']}\n\n"
                       "## Carreras sugeridas\n" + "\n".join(f"- {c['programa'].title()} ({c['nivel']})"
                                                             for c in carreras)
                       + f"\n\n## Dónde estudiar {prog.title()} ({region.title()}, {gestion})\n"
                       + "\n".join(f"- {r.institucion} - {r.tipo} - {r.gestion} - {r.distrito.title()} - "
                                   f"{r.perfil_link}" for r in tabla_rep.itertuples()))
            izq, der = st.columns([3, 2], gap="large")
            with izq, st.container(border=True, key="card_reporte"):
                st.markdown(f"**Tu perfil:** {codigo_holland(punt)}  \n**Carrera elegida:** {prog.title()}  \n"
                            f"**Región:** {region.title()} · **Gestión:** {gestion}  \n"
                            f"**Instituciones en el reporte:** {len(tabla_rep)}")
                st.download_button("Descargar reporte para el tutor", reporte, file_name="reporte_rumbo.md",
                                   mime="text/markdown", width="stretch", type="primary")
            with der, st.container(border=True, key="card_reinicio"):
                st.markdown("**¿Quieres probar de nuevo?**")
                st.caption("Puedes repetir el test con otras respuestas o con otra región.")
                st.button("Hacer el test de nuevo", on_click=reiniciar, width="stretch")

        # Navegación inferior
        st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
        b1, _, b2 = st.columns([1, 2, 1])
        if sec > 0:
            b1.button(f"← {ETIQUETAS_SEC[sec - 1][5:]}", on_click=ir_sec, args=(sec - 1,), width="stretch",
                      key="btn_ant")
        if sec < len(SECCIONES_RES) - 1:
            b2.button(f"{ETIQUETAS_SEC[sec + 1][5:]} →", on_click=ir_sec, args=(sec + 1,), width="stretch",
                      type="primary", key="btn_sig")
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
                                    marker={"colors": ["#064e3b", "#059669", "#10b981", "#34d399", "#6ee7b7",
                                                       "#a7f3d0", "#34d399", "#14b8a6"]},
                                    textinfo="none", hovertemplate="%{label}: %{value}<extra></extra>"))
            dona.update_layout(title={"text": "Instituciones por tipo", "font": {"size": 14}}, height=230,
                               margin={"l": 10, "r": 10, "t": 40, "b": 10}, font={"family": "Inter", "size": 11},
                               legend={"font": {"size": 10}})
            st.plotly_chart(dona, width="stretch", config={"displayModeBar": False})

    st.markdown("##### Comparación entre regiones")
    st.caption("Ordena cualquier columna con un clic para ver qué regiones tienen más o menos oferta.")
    tabla_reg = (oferta.groupby("departamento")
                 .agg(ofertas=("programa", "size"), instituciones=("institucion", "nunique"),
                      universidades=("tipo", lambda t: int((t == "Universidad").sum())),
                      publica=("gestion", lambda g: round((g == "Pública").mean() * 100, 1)))
                 .reset_index().sort_values("ofertas", ascending=False))
    tabla_reg["departamento"] = tabla_reg["departamento"].str.title()
    st.dataframe(tabla_reg, hide_index=True, width="stretch", height=420, column_config={
        "departamento": "Región", "ofertas": "Ofertas de estudio", "instituciones": "Instituciones",
        "universidades": "Ofertas universitarias",
        "publica": st.column_config.ProgressColumn("% oferta pública", min_value=0, max_value=100, format="%.0f%%")})

# ============================================================
# EXPLORAR
# ============================================================
with tab_explorar:
    seccion("Explorar", "Toda la oferta de educación superior del Perú",
            "Busca una carrera o una institución y mira dónde está, con su web y su perfil de egreso", "explorar")
    # Primero el sector, luego la carrera; la institución es un filtro aparte y opcional
    sector_e, carrera_e = elegir_sector_y_carrera("exp", permitir_todas=True)
    texto = carrera_e or sector_e or ""
    texto_inst = st.text_input("Institución (opcional)", placeholder="San Marcos, SENATI, Monterrico...")
    e3, e4, e5 = st.columns([1, 1, 2])
    region_e = e3.selectbox("Región ", ["TODAS"] + departamentos, format_func=str.title)
    gestion_e = e4.selectbox("Gestión ", ["Ambas", "Pública", "Privada"])
    tipos = e5.multiselect("Tipo de institución", sorted(oferta["tipo"].unique()))
    q = oferta
    sin_t = str.maketrans("ÁÉÍÓÚ", "AEIOU")
    if sector_e:
        q = q[q["area"] == sector_e]
    if carrera_e:
        q = q[q["programa"] == carrera_e]
    if texto_inst:
        buscado = texto_inst.upper().translate(sin_t)
        q = q[q["institucion"].str.upper().str.translate(sin_t).str.contains(buscado, regex=False, na=False)]
    if gestion_e != "Ambas":
        q = q[q["gestion"] == gestion_e]
    if tipos:
        q = q[q["tipo"].isin(tipos)]
    if region_e != "TODAS":
        q = q[q["departamento"] == region_e]

    kpis([(f"{len(q):,}", "ofertas encontradas"), (f"{q['institucion'].nunique():,}", "instituciones"),
          (f"{(q['gestion'] == 'Pública').sum():,}", "ofertas públicas"),
          (f"{(q['gestion'] == 'Privada').sum():,}", "ofertas privadas")], claro_desde=3)

    # Explorar es el buscador: dónde está cada carrera o institución (el análisis por región está en Panorama)
    v1, v2 = st.tabs(["🗺️ Mapa", "📋 Lista"])
    with v1:
        sedes = q.drop_duplicates(["institucion", "lat", "lon"])
        if q.empty:
            st.info("No hay resultados con esos filtros.")
        elif len(sedes) > 1500:
            st.info(f"Hay {len(sedes):,} sedes. Escribe una carrera o elige una región para ver el mapa.")
        else:
            with st.container(border=True, key="mapa_exp_pts"):
                mapa_instituciones(q, key=f"mapa_exp_{texto}_{texto_inst}_{region_e}_{gestion_e}_{len(q)}",
                                   height=520)
    with v2:
        st.dataframe(q[COLUMNAS_TABLA].head(1000), hide_index=True, width="stretch", column_config=CONFIG_TABLA,
                     row_height=56, height=480)
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
    pasos = [("🧭", "El estudiante hace el test", "24 preguntas en 4 secciones, desde el celular o la sala de cómputo."),
             ("🤖", "La IA interpreta su perfil", "Explica sus intereses y sugiere carreras reales del Perú."),
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

    seccion(4, "Sobre el test", "Cómo se construyeron las preguntas", "sobre_test")
    st.markdown("- Se basa en el **modelo RIASEC de John Holland**: seis tipos de interés (Realista, Investigador, "
                "Artístico, Social, Emprendedor y Convencional). Son **24 preguntas en 4 secciones** (actividades, lugares de trabajo, temas y otras actividades), con una pregunta de cada tipo por sección.\n"
                "- Las preguntas son de redacción propia y siguen el formato de los **marcadores RIASEC de dominio "
                "público (AFPD)**, validados en español por Cupani y otros (2019): **una sola actividad por "
                "pregunta**, cada una de un solo tipo y posible en la costa, la sierra o la selva.\n"
                "- **Es una herramienta de orientación, no un diagnóstico.** Conviene conversar el resultado con "
                "un tutor o psicólogo.")

st.markdown('<div class="pie">Rumbo · Orientación vocacional con datos abiertos del Perú · '
            'Proyecto final Diplomatura Q-Lab PUCP 2026</div>', unsafe_allow_html=True)
