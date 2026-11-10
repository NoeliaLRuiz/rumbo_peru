"""Rumbo: test vocacional + dónde estudiar en el Perú (público y privado).

Correr:  streamlit run app/streamlit_app.py
"""
import sys
from pathlib import Path
from urllib.parse import quote_plus

import folium
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from ai.areas import AREAS, icono_area, nombre_area  # noqa: E402
from ai.orientador import recomendar  # noqa: E402
from ai.test_vocacional import (DIMENSIONES, EJEMPLO, OPCIONES, PREGUNTAS,  # noqa: E402
                                codigo_holland, puntajes, ranking_areas)

st.set_page_config(page_title="Rumbo · Test vocacional", page_icon="🧭", layout="wide")

AZUL, AZUL_OSCURO, CELESTE, AZUL_SUAVE = "#1d4ed8", "#1e3a8a", "#38bdf8", "#eff6ff"
COLOR_GESTION = {"Pública": AZUL_OSCURO, "Privada": CELESTE}
ICONO_GESTION = {"Pública": "🏛️", "Privada": "🏢"}
N_PASOS = 4  # bloques de preguntas: 6 preguntas por bloque, una de cada tipo de interés

st.markdown(f"""
<style>
.stApp {{background: #ffffff;}}
.hero {{background: linear-gradient(120deg, {AZUL_OSCURO} 0%, {AZUL} 55%, {CELESTE} 100%); color: #fff;
       padding: 30px 34px; border-radius: 20px; margin-bottom: 14px; animation: aparecer .6s ease-out;
       box-shadow: 0 12px 30px rgba(29,78,216,.25);}}
.hero h1 {{color: #fff; margin: 0 0 6px 0; font-size: 2.5rem;}}
.hero p {{margin: 0; font-size: 1.1rem; opacity: .95;}}
.hero .stats {{display: flex; gap: 14px; flex-wrap: wrap; margin-top: 18px;}}
.hero .stat {{background: rgba(255,255,255,.15); border: 1px solid rgba(255,255,255,.3);
             border-radius: 14px; padding: 10px 16px; backdrop-filter: blur(4px);}}
.hero .stat b {{display: block; font-size: 1.6rem;}}
.seccion {{display: flex; align-items: center; gap: 14px; margin: 26px 0 12px 0; padding: 14px 18px;
          background: {AZUL_SUAVE}; border-left: 6px solid {AZUL}; border-radius: 12px;
          animation: aparecer .5s ease-out; scroll-margin-top: 70px;}}
.seccion .num {{background: {AZUL}; color: #fff; font-weight: 800; border-radius: 50%;
               min-width: 38px; height: 38px; display: flex; align-items: center; justify-content: center;}}
.seccion h3 {{margin: 0; color: {AZUL_OSCURO}; font-size: 1.35rem;}}
.seccion small {{color: #475569;}}
.nav {{display: flex; gap: 8px; flex-wrap: wrap; margin: 6px 0 4px 0;}}
.nav a {{background: #fff; border: 1.5px solid {AZUL}; color: {AZUL} !important; padding: 6px 14px;
        border-radius: 999px; text-decoration: none; font-weight: 600; font-size: .9rem; transition: all .2s;}}
.nav a:hover {{background: {AZUL}; color: #fff !important;}}
.perfil {{font-size: 3.2rem; font-weight: 800; letter-spacing: .35rem;
         background: linear-gradient(90deg, {AZUL_OSCURO}, {CELESTE}); -webkit-background-clip: text;
         -webkit-text-fill-color: transparent; animation: aparecer .8s ease-out;}}
.leyenda span {{display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin: 0 4px 0 10px;}}
[class*="st-key-card"] {{background: #fff; border-color: #bfdbfe !important; transition: transform .2s, box-shadow .2s;
                        animation: aparecer .5s ease-out;}}
[class*="st-key-card"]:hover {{transform: translateY(-4px); box-shadow: 0 12px 26px rgba(29,78,216,.18);
                              border-color: {AZUL} !important;}}
.stTabs [data-baseweb="tab"] {{font-weight: 600;}}
@keyframes aparecer {{from {{opacity: 0; transform: translateY(12px);}} to {{opacity: 1; transform: none;}}}}
</style>
""", unsafe_allow_html=True)


def seccion(num, titulo: str, subtitulo: str = "", ancla: str = ""):
    """Encabezado de sección numerado (con ancla para el menú de navegación)."""
    st.markdown(f'<div class="seccion" id="{ancla}"><div class="num">{num}</div>'
                f'<div><h3>{titulo}</h3><small>{subtitulo}</small></div></div>', unsafe_allow_html=True)


LEYENDA = (f'<div class="leyenda"><span style="background:{COLOR_GESTION["Pública"]}"></span>Pública'
           f'<span style="background:{COLOR_GESTION["Privada"]}"></span>Privada</div>')


@st.cache_data
def cargar_oferta() -> pd.DataFrame:
    df = pd.read_csv(RAIZ / "data" / "oferta.csv")
    df["web"] = df["web"].where(df["web"].notna() & (df["web"] != ""), None)
    # Para todas las instituciones: búsqueda en Google con nombre + distrito (por si no hay web oficial)
    prefijo = df["tipo"].map({"Instituto tecnológico": "Instituto", "Instituto / escuela pedagógica":
                              "Instituto pedagógico", "Escuela de arte": "Escuela", "CETPRO (técnico-productiva)":
                              "CETPRO"}).fillna("")
    consulta = prefijo + " " + df["institucion"] + " " + df["distrito"].fillna("").str.title() + " admisión"
    df["buscar"] = "https://www.google.com/search?q=" + consulta.map(lambda q: quote_plus(q))
    return df


COLUMNAS_TABLA = ["institucion", "tipo", "gestion", "programa", "departamento", "provincia", "distrito",
                  "web", "buscar"]
CONFIG_TABLA = {
    "institucion": "Institución", "tipo": "Tipo", "gestion": "Gestión", "programa": "Carrera",
    "departamento": "Región", "provincia": "Provincia", "distrito": "Distrito",
    "web": st.column_config.LinkColumn("Sitio web", display_text="🌐 Ir a la web"),
    "buscar": st.column_config.LinkColumn("Más info", display_text="🔎 Buscar"),
}

oferta = cargar_oferta()
departamentos = sorted(oferta["departamento"].dropna().unique())

# ---------------- Estado de la sesión ----------------
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


# ---------------- Encabezado ----------------
st.markdown(f"""
<div class="hero">
  <h1>🧭 Rumbo</h1>
  <p>Descubre qué estudiar y <b>dónde</b>, cerca de casa: universidades, institutos, pedagógicos,
     escuelas de arte y CETPRO, <b>públicos y privados</b>.</p>
  <div class="stats">
    <div class="stat"><b>{len(oferta):,}</b>ofertas de estudio</div>
    <div class="stat"><b>{oferta['institucion'].nunique():,}</b>instituciones</div>
    <div class="stat"><b>{oferta['departamento'].nunique()}</b>regiones</div>
    <div class="stat"><b>{(oferta['gestion'] == 'Pública').mean():.0%}</b>en instituciones públicas</div>
  </div>
</div>""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Sobre Rumbo")
    st.write("Datos abiertos de **SUNEDU** (universidades licenciadas) y del **Censo Educativo 2025 "
             "del MINEDU** (institutos, pedagógicos, escuelas de arte y CETPRO).")
    st.caption("No guardamos tus respuestas ni datos personales.")
    st.button("🔄 Reiniciar test", on_click=reiniciar)

tab_test, tab_explorar, tab_colegios = st.tabs(["🧭 Test vocacional", "🔎 Explorar la oferta",
                                                "🏫 Para colegios"])

# ================= TEST =================
with tab_test:
    paso = ss["paso"]

    # ---- Paso 0: bienvenida ----
    if paso == 0:
        seccion("👋", "¿No sabes qué estudiar? Empecemos", "4 pasos cortos · unos 3 minutos", "inicio")
        izq, der = st.columns([3, 2])
        with izq:
            st.write("Son **24 actividades** en 4 pasos cortos. Marca cuánto te gustaría hacer cada una. "
                     "No hay respuestas buenas ni malas. Te toma unos 3 minutos.")
            ss["depto"] = st.selectbox("¿En qué región vives?", departamentos,
                                       index=departamentos.index(ss["depto"]))
            ss["sobre_mi"] = st.text_area("Cuéntanos con tus palabras qué te gusta o qué te imaginas haciendo "
                                          "(opcional)", value=ss["sobre_mi"], max_chars=600)
            b1, b2 = st.columns(2)
            b1.button("Empezar el test →", type="primary", on_click=ir_a, args=(1,), width="stretch")
            b2.button("⚡ Ver un ejemplo (demo)", on_click=usar_demo, width="stretch")
        with der, st.container(border=True, key="card_beneficios"):
            st.markdown("#### Lo que vas a obtener")
            st.markdown("✨ Tu **perfil de intereses** (modelo RIASEC)\n\n"
                        "🎯 **Carreras sugeridas**, universitarias y técnicas\n\n"
                        "📍 **Dónde estudiarlas** en tu región, en un mapa\n\n"
                        "🏛️ Opciones **públicas** y 🏢 **privadas**, con enlace a su web\n\n"
                        "📄 Un **reporte** para compartir con tu tutor")

    # ---- Pasos 1-4: preguntas ----
    elif 1 <= paso <= N_PASOS:
        seccion(f"{paso}/{N_PASOS}", "¿Cuánto te gustaría hacer cada actividad?",
                "No hay respuestas buenas ni malas: responde lo que sientes", "preguntas")
        st.progress(paso / N_PASOS, text=f"Paso {paso} de {N_PASOS}")
        indices = [paso - 1 + N_PASOS * d for d in range(len(DIMENSIONES))]  # una pregunta de cada tipo
        cols = st.columns(2)
        for n, i in enumerate(indices):
            with cols[n % 2], st.container(border=True):
                actual = ss["resp"][i]
                valor = st.radio(PREGUNTAS[i][1], list(OPCIONES), format_func=OPCIONES.get, horizontal=True,
                                 index=list(OPCIONES).index(actual) if actual else None, key=f"w{i}")
                ss["resp"][i] = valor
        faltan = sum(ss["resp"][i] is None for i in indices)
        b1, _, b2 = st.columns([1, 2, 1])
        b1.button("← Atrás", on_click=ir_a, args=(paso - 1,), width="stretch")
        if paso < N_PASOS:
            b2.button("Siguiente →", type="primary", disabled=faltan > 0, on_click=ir_a, args=(paso + 1,),
                      width="stretch")
        else:
            b2.button("✨ Ver mis resultados", type="primary", disabled=faltan > 0, on_click=calcular_resultado,
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

        st.markdown('<div class="nav"><a href="#perfil">1 · Tu perfil</a><a href="#areas">2 · Áreas afines</a>'
                    '<a href="#carreras">3 · Carreras</a><a href="#donde">4 · Dónde estudiar</a>'
                    '<a href="#reporte">5 · Reporte</a></div>', unsafe_allow_html=True)

        seccion(1, "Tu perfil de intereses", "Basado en el modelo RIASEC de John Holland", "perfil")
        izq, der = st.columns([1, 1])
        with izq:
            st.markdown(f'<div class="perfil">{codigo_holland(punt)}</div>', unsafe_allow_html=True)
            st.write(rec["perfil"])
            st.markdown(" ".join(f"`{f}`" for f in rec["fortalezas"]))
            st.info("👣 **Siguiente paso:** " + rec["siguiente_paso"])
            st.caption("Recomendación generada con IA (Claude) y validada contra los datos oficiales."
                       if rec.get("fuente") == "ia" else "Recomendación generada con reglas del modelo RIASEC.")
        with der:
            etiquetas = [DIMENSIONES[d][0] for d in punt] + [DIMENSIONES[next(iter(punt))][0]]
            valores = list(punt.values()) + [next(iter(punt.values()))]
            radar = go.Figure(go.Scatterpolar(
                r=valores, theta=etiquetas, fill="toself", line_color=AZUL,
                fillcolor="rgba(56,189,248,.35)",
                hovertemplate="%{theta}: %{r:.0f}/100<extra></extra>"))
            radar.update_layout(polar={"radialaxis": {"range": [0, 100], "showticklabels": False}},
                                margin={"l": 40, "r": 40, "t": 20, "b": 20}, height=320, showlegend=False)
            st.plotly_chart(radar, width="stretch")

        seccion(2, "Tus áreas más afines", "Qué tanto se parecen tus intereses a cada campo de estudio", "areas")
        cols = st.columns(4)
        for col, (a, s) in zip(cols, ranking[:4]):
            with col, st.container(border=True, key=f"card_area_{a}"):
                st.markdown(f"### {icono_area(a)}")
                st.markdown(f"**{AREAS[a]['nombre']}**")
                st.progress(min(s / 100, 1.0), text=f"Afinidad {s:.0f}/100")

        # ---- Carreras sugeridas ----
        seccion(3, "Carreras sugeridas para ti",
                f"Primero las que puedes estudiar en {depto_est.title()}", "carreras")
        en_region = oferta[oferta["departamento"] == depto_est]["programa"].value_counts()
        carreras = sorted(rec["carreras"], key=lambda c: -en_region.get(c["programa"], 0))
        cols = st.columns(3)
        for n, c in enumerate(carreras):
            with cols[n % 3], st.container(border=True, key=f"card_prog_{n}"):
                st.markdown(f"**{icono_area(c['area_id'])} {c['programa'].title()}**")
                st.caption(f"{c['nivel'].capitalize()} · {nombre_area(c['area_id'])}")
                st.write(c["por_que"])
                lugares = int(en_region.get(c["programa"], 0))
                st.markdown(f"📍 **{lugares}** lugares en {depto_est.title()}" if lugares
                            else f"📍 No hay en {depto_est.title()}: mira otras regiones")
                st.button("Ver dónde estudiar ↓", key=f"ver_{n}", on_click=ver_donde, args=(c["programa"],),
                          width="stretch")

        # ---- Dónde estudiar ----
        seccion(4, "¿Dónde puedo estudiarlo?", "Instituciones públicas y privadas, con enlace a su web",
                "donde")
        opciones_prog = [c["programa"] for c in carreras]
        opciones_prog = list(dict.fromkeys(opciones_prog))
        if ss.get("prog_sel") not in opciones_prog:
            ss["prog_sel"] = opciones_prog[0]
        f1, f2, f3 = st.columns([2, 1, 1])
        prog = f1.selectbox("Carrera", opciones_prog, key="prog_sel",
                            format_func=lambda p: f"{p.title()} ({en_region.get(p, 0)} en {depto_est.title()})")
        region = f2.selectbox("Región", ["TODAS"] + departamentos, index=1 + departamentos.index(depto_est))
        gestion = f3.radio("Gestión", ["Ambas", "Pública", "Privada"], horizontal=True)

        area_prog = oferta.loc[oferta["programa"] == prog, "area"].iloc[0]
        ver_similares = st.toggle(f"Incluir carreras parecidas ({nombre_area(area_prog)})", value=False)
        sel = oferta[oferta["area"] == area_prog] if ver_similares else oferta[oferta["programa"] == prog]
        if region != "TODAS":
            sel = sel[sel["departamento"] == region]
        if gestion != "Ambas":
            sel = sel[sel["gestion"] == gestion]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Lugares encontrados", len(sel))
        m2.metric("🏛️ Públicos", int((sel["gestion"] == "Pública").sum()))
        m3.metric("🏢 Privados", int((sel["gestion"] == "Privada").sum()))
        m4.metric("🌐 Con web oficial", int(sel["web"].notna().sum()))

        if sel.empty:
            st.warning("No hay oferta con esos filtros. Prueba con 'Incluir carreras parecidas' o con otra región.")
        else:
            mapa_df = sel.dropna(subset=["lat", "lon"])
            if not mapa_df.empty:
                mapa = folium.Map(location=[mapa_df["lat"].mean(), mapa_df["lon"].mean()],
                                  zoom_start=6 if region == "TODAS" else 8, tiles="OpenStreetMap")
                grupo = MarkerCluster().add_to(mapa)
                for r in mapa_df.itertuples():
                    folium.CircleMarker(
                        [r.lat, r.lon], radius=8, color="#ffffff", weight=2, fill=True,
                        fill_color=COLOR_GESTION[r.gestion], fill_opacity=0.95,
                        tooltip=f"{ICONO_GESTION[r.gestion]} {r.institucion} ({r.gestion})",
                        popup=folium.Popup(f"<b>{r.institucion}</b><br>{r.tipo} · {r.gestion}<br>"
                                           f"{r.programa.title()}<br>{r.distrito}, {r.provincia}<br>"
                                           + (f'<a href="{r.web}" target="_blank">🌐 Ir a la web</a> · '
                                              if r.web else "")
                                           + f'<a href="{r.buscar}" target="_blank">🔎 Buscar</a>',
                                           max_width=280),
                    ).add_to(grupo)
                st_folium(mapa, height=450, use_container_width=True, returned_objects=[])
                st.markdown(LEYENDA, unsafe_allow_html=True)
                st.caption("Haz clic en un punto para ver la institución y su web")

            tabla = sel[COLUMNAS_TABLA].sort_values(["gestion", "tipo", "institucion"])
            tabla["programa"] = tabla["programa"].str.title()
            st.dataframe(tabla, hide_index=True, width="stretch", column_config=CONFIG_TABLA)

            # Reporte para el tutor (lo que paga el colegio)
            reporte = (f"# Reporte vocacional - Rumbo\n\nPerfil: {codigo_holland(punt)}\n\n{rec['perfil']}\n\n"
                       "## Carreras sugeridas\n" + "\n".join(f"- {c['programa'].title()} ({c['nivel']})"
                                                             for c in carreras)
                       + f"\n\n## Dónde estudiar {prog.title()} ({region}, {gestion})\n"
                       + "\n".join(f"- {r.institucion} - {r.tipo} - {r.gestion} - {r.distrito} - {r.web or r.buscar}"
                                   for r in tabla.head(30).itertuples()))
            seccion(5, "Comparte tu resultado", "Descarga el reporte y conversa con tu tutor o tu familia", "reporte")
            b1, b2 = st.columns(2)
            b1.download_button("📄 Descargar reporte para el tutor", reporte, file_name="reporte_rumbo.md",
                               mime="text/markdown", width="stretch")
            b2.button("🔄 Hacer el test de nuevo", on_click=reiniciar, width="stretch")
    else:
        ss["paso"] = 0
        st.rerun()

# ================= EXPLORAR =================
with tab_explorar:
    seccion("🔎", "Busca cualquier carrera", "Toda la oferta de educación superior del Perú en un solo lugar",
            "explorar")
    e1, e2, e3, e4 = st.columns([2, 1, 1, 1])
    texto = e1.text_input("Carrera o palabra clave", placeholder="enfermería, mecánica, diseño...")
    region_e = e2.selectbox("Región ", ["TODAS"] + departamentos)
    gestion_e = e3.selectbox("Gestión ", ["Ambas", "Pública", "Privada"])
    tipos = e4.multiselect("Tipo", sorted(oferta["tipo"].unique()))
    q = oferta
    if texto:
        sin_tildes = texto.upper().translate(str.maketrans("ÁÉÍÓÚ", "AEIOU"))
        q = q[q["programa"].str.contains(texto.upper(), regex=False, na=False)
              | q["programa"].str.upper().str.translate(str.maketrans("ÁÉÍÓÚ", "AEIOU"))
                 .str.contains(sin_tildes, regex=False, na=False)]
    if region_e != "TODAS":
        q = q[q["departamento"] == region_e]
    if gestion_e != "Ambas":
        q = q[q["gestion"] == gestion_e]
    if tipos:
        q = q[q["tipo"].isin(tipos)]

    k1, k2, k3 = st.columns(3)
    k1.metric("Resultados", f"{len(q):,}")
    k2.metric("🏛️ Públicos", f"{(q['gestion'] == 'Pública').sum():,}")
    k3.metric("🏢 Privados", f"{(q['gestion'] == 'Privada').sum():,}")
    resumen = q.groupby(["tipo", "gestion"]).size().reset_index(name="n")
    if not resumen.empty:
        fig = go.Figure([go.Bar(y=resumen[resumen["gestion"] == g]["tipo"], x=resumen[resumen["gestion"] == g]["n"],
                                name=g, orientation="h", marker_color=COLOR_GESTION[g],
                                hovertemplate="%{y}: %{x}<extra>" + g + "</extra>")
                         for g in ["Pública", "Privada"]])
        fig.update_layout(barmode="stack", height=280, margin={"l": 10, "r": 10, "t": 10, "b": 10},
                          legend={"orientation": "h", "y": -0.15})
        st.plotly_chart(fig, width="stretch")
    st.dataframe(q[COLUMNAS_TABLA].head(500), hide_index=True, width="stretch", column_config=CONFIG_TABLA)

# ================= PARA COLEGIOS =================
with tab_colegios:
    seccion(1, "Cómo funciona", "De la duda a un plan concreto en una clase de tutoría", "como")
    pasos = [("🧭", "El estudiante hace el test", "24 actividades en 4 pasos, desde el celular o la sala de cómputo."),
             ("🤖", "La IA interpreta su perfil", "Claude explica sus intereses y sugiere carreras reales del Perú."),
             ("📍", "Ve dónde estudiar", "Mapa con instituciones públicas y privadas de su región y su web."),
             ("📄", "El tutor recibe el reporte", "Para conversar con el estudiante y su familia.")]
    for col, (ic, tit, txt) in zip(st.columns(4), pasos):
        with col, st.container(border=True, key=f"card_paso_{tit[:6]}"):
            st.markdown(f"### {ic}")
            st.markdown(f"**{tit}**")
            st.caption(txt)

    seccion(2, "Planes", "El estudiante siempre usa Rumbo gratis", "planes")
    planes = [("Estudiante", "Gratis", ["Test vocacional", "Carreras sugeridas", "Mapa y enlaces"]),
              ("Colegio", "S/ 8 por estudiante al año", ["Todo lo del plan Estudiante", "Reportes por aula",
                                                         "Charla guiada para tutores"]),
              ("UGEL / DRE", "S/ 2,500 por UGEL al año", ["Panel de tendencias vocacionales",
                                                         "Brechas de oferta por provincia", "Soporte"])]
    for col, (nombre, precio, items) in zip(st.columns(3), planes):
        with col, st.container(border=True, key=f"card_plan_{nombre[:5]}"):
            st.markdown(f"#### {nombre}")
            st.markdown(f"<h3 style='color:{AZUL};margin:0'>{precio}</h3>", unsafe_allow_html=True)
            st.markdown("\n".join(f"- {i}" for i in items))

    seccion(3, "Datos y privacidad", "Información oficial y abierta", "datos")
    st.markdown("- **SUNEDU:** programas de las universidades licenciadas.\n"
                "- **MINEDU, Censo Educativo 2025:** institutos tecnológicos, pedagógicos, escuelas de arte "
                "y CETPRO, con su gestión y ubicación.\n"
                "- **Privacidad:** no guardamos respuestas ni datos personales de los estudiantes.")
