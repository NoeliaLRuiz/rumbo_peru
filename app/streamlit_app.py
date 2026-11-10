"""Rumbo: test vocacional + dónde estudiar en el Perú (público y privado).

Correr:  streamlit run app/streamlit_app.py
"""
import sys
from pathlib import Path
from urllib.parse import quote_plus

import folium
import pandas as pd
import streamlit as st
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from ai.areas import AREAS, nombre_area  # noqa: E402
from ai.orientador import recomendar  # noqa: E402
from ai.test_vocacional import (DIMENSIONES, EJEMPLO, OPCIONES, PREGUNTAS,  # noqa: E402
                                codigo_holland, puntajes, ranking_areas)

st.set_page_config(page_title="Rumbo · Test vocacional", page_icon="🧭", layout="wide")

COLOR_GESTION = {"Pública": "#1a7f5a", "Privada": "#2f5bd3"}


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

# ---------------- Encabezado ----------------
st.title("🧭 Rumbo")
st.markdown("**Descubre qué estudiar y dónde, cerca de casa:** universidades, institutos tecnológicos, "
            "pedagógicos, escuelas de arte y CETPRO, **públicos y privados**.")
c1, c2, c3 = st.columns(3)
c1.metric("Ofertas de estudio", f"{len(oferta):,}")
c2.metric("Instituciones", f"{oferta['institucion'].nunique():,}")
c3.metric("Ofertas en instituciones públicas", f"{(oferta['gestion'] == 'Pública').mean():.0%}")

with st.sidebar:
    st.header("Sobre Rumbo")
    st.write("Datos abiertos de **SUNEDU** (universidades licenciadas) y del **Censo Educativo 2025 "
             "del MINEDU** (institutos, pedagógicos, escuelas de arte y CETPRO).")
    st.caption("No guardamos tus respuestas ni datos personales.")
    if st.button("Reiniciar test"):
        st.session_state.clear()
        st.rerun()

tab_test, tab_explorar = st.tabs(["1 · Test vocacional", "2 · Explorar toda la oferta"])

# ---------------- Test ----------------
with tab_test:
    # Valores iniciales de los widgets (se definen aquí para poder llenarlos con la demo)
    for i in range(len(PREGUNTAS)):
        st.session_state.setdefault(f"p{i}", None)
    st.session_state.setdefault("depto", "LIMA")

    if st.button("⚡ Llenar con respuestas de ejemplo (demo)"):
        for i, v in enumerate(EJEMPLO):
            st.session_state[f"p{i}"] = v
        st.session_state["sobre_mi"] = ("Me gusta ayudar a mis compañeros con biología y quiero "
                                        "trabajar cerca de mi familia en Ayacucho.")
        st.session_state["depto"] = "AYACUCHO"

    with st.form("test"):
        st.subheader("¿Cuánto te gustaría hacer cada actividad?")
        respuestas = []
        cols = st.columns(2)
        for i, (_, texto) in enumerate(PREGUNTAS):
            with cols[i % 2]:
                respuestas.append(st.radio(texto, list(OPCIONES), format_func=OPCIONES.get,
                                           horizontal=True, key=f"p{i}"))
        sobre_mi = st.text_area("Cuéntanos con tus palabras qué te gusta o qué te imaginas haciendo (opcional)",
                                key="sobre_mi", max_chars=600)
        st.selectbox("¿En qué región vives?", departamentos, key="depto")
        enviado = st.form_submit_button("Ver mis resultados", type="primary")

    if enviado:
        if None in respuestas:
            st.warning(f"Te faltan {respuestas.count(None)} preguntas por responder.")
        else:
            punt = puntajes(respuestas)
            ranking = ranking_areas(punt)
            with st.spinner("Analizando tus intereses..."):
                st.session_state["resultado"] = {
                    "punt": punt, "ranking": ranking,
                    "rec": recomendar(punt, ranking, oferta, sobre_mi, st.session_state["depto"]),
                    "depto": st.session_state["depto"],
                }

    res = st.session_state.get("resultado")
    if res:
        punt, ranking, rec = res["punt"], res["ranking"], res["rec"]
        st.divider()
        st.header(f"Tu perfil: {codigo_holland(punt)}")
        izq, der = st.columns([1, 1])
        with izq:
            st.write(rec["perfil"])
            st.markdown("**Tus fortalezas:** " + " · ".join(rec["fortalezas"]))
            graf = pd.DataFrame({"Interés": [f"{DIMENSIONES[d][0]} ({d})" for d in punt],
                                 "Puntaje": list(punt.values())}).set_index("Interés")
            st.bar_chart(graf, horizontal=True, height=260)
        with der:
            st.markdown("**Áreas más afines**")
            for a, s in ranking[:4]:
                st.progress(min(s / 100, 1.0), text=f"{AREAS[a]['nombre']} · {s:.0f}/100")
            st.info("👣 **Siguiente paso:** " + rec["siguiente_paso"])
            if rec.get("fuente") == "ia":
                st.caption("Recomendación generada con IA (Claude) y validada contra los datos oficiales.")
            else:
                st.caption("Recomendación generada con reglas del modelo RIASEC.")

        st.subheader("Carreras sugeridas para ti")
        for c in rec["carreras"]:
            st.markdown(f"- **{c['programa'].title()}** · _{c['nivel']}_ · {nombre_area(c['area_id'])}  \n"
                        f"  {c['por_que']}")

        # ---------------- Dónde estudiar ----------------
        st.divider()
        st.header("📍 ¿Dónde puedo estudiarlo?")
        f1, f2, f3 = st.columns([2, 1, 1])
        depto_est = res["depto"]
        en_region = oferta[oferta["departamento"] == depto_est]["programa"].value_counts()
        # Primero las carreras que sí se ofrecen en la región del estudiante
        opciones_prog = sorted(dict.fromkeys(c["programa"] for c in rec["carreras"]),
                               key=lambda p: -en_region.get(p, 0))
        prog = f1.selectbox("Carrera", opciones_prog,
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

        m1, m2, m3 = st.columns(3)
        m1.metric("Lugares encontrados", len(sel))
        m2.metric("Públicos", int((sel["gestion"] == "Pública").sum()))
        m3.metric("Privados", int((sel["gestion"] == "Privada").sum()))

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
                        [r.lat, r.lon], radius=7, color=COLOR_GESTION[r.gestion], fill=True, fill_opacity=0.85,
                        popup=folium.Popup(f"<b>{r.institucion}</b><br>{r.tipo} · {r.gestion}<br>"
                                           f"{r.programa.title()}<br>{r.distrito}, {r.provincia}<br>"
                                           + (f'<a href="{r.web}" target="_blank">🌐 Ir a la web</a> · '
                                              if r.web else "")
                                           + f'<a href="{r.buscar}" target="_blank">🔎 Buscar</a>',
                                           max_width=280),
                    ).add_to(grupo)
                st_folium(mapa, height=430, use_container_width=True, returned_objects=[])
                st.caption("🟢 Pública · 🔵 Privada")

            tabla = sel[COLUMNAS_TABLA].sort_values(["gestion", "tipo", "institucion"])
            tabla["programa"] = tabla["programa"].str.title()
            st.dataframe(tabla, hide_index=True, width="stretch", column_config=CONFIG_TABLA)

            # Reporte para el tutor (lo que paga el colegio)
            reporte = (f"# Reporte vocacional - Rumbo\n\nPerfil: {codigo_holland(punt)}\n\n{rec['perfil']}\n\n"
                       "## Carreras sugeridas\n" + "\n".join(f"- {c['programa'].title()} ({c['nivel']})"
                                                             for c in rec["carreras"])
                       + f"\n\n## Dónde estudiar {prog.title()} ({region}, {gestion})\n"
                       + "\n".join(f"- {r.institucion} - {r.tipo} - {r.gestion} - {r.distrito} - {r.web or r.buscar}"
                                   for r in tabla.head(30).itertuples()))
            st.download_button("📄 Descargar reporte para el tutor", reporte,
                               file_name="reporte_rumbo.md", mime="text/markdown")

# ---------------- Explorar ----------------
with tab_explorar:
    st.subheader("Busca cualquier carrera")
    e1, e2, e3, e4 = st.columns([2, 1, 1, 1])
    texto = e1.text_input("Carrera o palabra clave", placeholder="enfermería, mecánica, diseño...")
    region_e = e2.selectbox("Región ", ["TODAS"] + departamentos)
    gestion_e = e3.selectbox("Gestión ", ["Ambas", "Pública", "Privada"])
    tipos = e4.multiselect("Tipo", sorted(oferta["tipo"].unique()))
    q = oferta
    if texto:
        q = q[q["programa"].str.contains(texto.upper(), regex=False, na=False)
              | q["programa"].str.contains(texto.upper().replace("Í", "I").replace("Á", "A")
                                           .replace("É", "E").replace("Ó", "O").replace("Ú", "U"),
                                           regex=False, na=False)]
    if region_e != "TODAS":
        q = q[q["departamento"] == region_e]
    if gestion_e != "Ambas":
        q = q[q["gestion"] == gestion_e]
    if tipos:
        q = q[q["tipo"].isin(tipos)]
    st.write(f"{len(q):,} resultados")
    resumen = q.groupby(["tipo", "gestion"]).size().unstack(fill_value=0)
    if not resumen.empty:
        st.bar_chart(resumen, color=[COLOR_GESTION[g] for g in resumen.columns], horizontal=True)
    st.dataframe(q[COLUMNAS_TABLA].head(500), hide_index=True, width="stretch", column_config=CONFIG_TABLA)
