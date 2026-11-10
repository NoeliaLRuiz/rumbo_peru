"""Orientador vocacional con IA: convierte el resultado del test en una recomendación personalizada.

Usa Claude con salida estructurada (JSON validado contra un esquema): la sesión 08 del curso.
Si no hay API key o la llamada falla, devuelve una recomendación hecha con reglas, para que
la app nunca se quede sin respuesta.
"""
import json
import os

from ai.areas import AREAS
from ai.test_vocacional import DIMENSIONES, codigo_holland

MODELO = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")

ESQUEMA = {
    "type": "object",
    "properties": {
        "perfil": {"type": "string", "description": "2-3 oraciones, en segunda persona, cálidas y concretas"},
        "fortalezas": {"type": "array", "items": {"type": "string"}},
        "carreras": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "programa": {"type": "string", "description": "Copiado EXACTO de la lista de programas"},
                    "area_id": {"type": "string"},
                    "por_que": {"type": "string"},
                    "nivel": {"type": "string", "enum": ["universitaria", "técnica", "técnico-productiva"]},
                },
                "required": ["programa", "area_id", "por_que", "nivel"],
                "additionalProperties": False,
            },
        },
        "siguiente_paso": {"type": "string"},
    },
    "required": ["perfil", "fortalezas", "carreras", "siguiente_paso"],
    "additionalProperties": False,
}

SISTEMA = """Eres un orientador vocacional peruano que acompaña a estudiantes de 5.º de secundaria.
Hablas claro, cálido y sin jerga, en español del Perú. No inventas datos.
Reglas:
- Recomienda de 5 a 6 programas, elegidos SOLO de la lista que se te da (copia el nombre exacto).
- Mezcla opciones universitarias y técnicas: una carrera técnica en un instituto público
  es una opción valiosa y suele ser gratuita o de bajo costo.
- Prioriza programas con 'lugares_en_tu_region' > 0: el estudiante quiere estudiar cerca de casa.
  Puedes incluir uno que no esté en su región si encaja mucho; dilo en 'por_que'.
- Si el estudiante cuenta algo de sí, úsalo para justificar.
- 'fortalezas': 3 frases cortas.
- 'siguiente_paso': una acción concreta para esta semana (hablar con alguien, visitar una institución, etc.)."""


def _candidatos(oferta, areas_top: list[str], por_area: int = 12, depto: str = "") -> dict[str, list[dict]]:
    """Programas de cada área, primero los que se ofrecen en la región del estudiante."""
    res = {}
    for a in areas_top:
        sub = oferta[oferta["area"] == a].assign(nivel=lambda d: d["tipo"].map(_nivel),
                                                 en_region=lambda d: d["departamento"] == depto)
        top = (sub.groupby(["programa", "nivel"])
                  .agg(en_tu_region=("en_region", "sum"), en_el_peru=("en_region", "size"))
                  .sort_values(["en_tu_region", "en_el_peru"], ascending=False)
                  .head(por_area).reset_index())
        res[a] = [{"programa": r.programa, "nivel": r.nivel,
                   "lugares_en_tu_region": int(r.en_tu_region)} for r in top.itertuples()]
    return res


def _nivel(tipo: str) -> str:
    if tipo == "Universidad":
        return "universitaria"
    if tipo.startswith("CETPRO"):
        return "técnico-productiva"
    return "técnica"


def recomendar_reglas(punt, ranking, oferta, sobre_mi: str = "", depto: str = "") -> dict:
    """Plan B sin IA: en cada una de las 3 áreas más afines, la carrera universitaria y la técnica
    más ofrecidas en la región del estudiante."""
    top = [a for a, _ in ranking[:3]]
    cands = _candidatos(oferta, top, por_area=30, depto=depto)
    carreras = []
    for a in top:
        uni = [c for c in cands[a] if c["nivel"] == "universitaria"][:1]
        tec = [c for c in cands[a] if c["nivel"] != "universitaria"][:1]
        for c in uni + tec:
            carreras.append({**c, "area_id": a,
                             "por_que": f"Encaja con tu interés en {AREAS[a]['nombre'].lower()}."})
    dims = codigo_holland(punt)
    return {
        "perfil": (f"Tu código de intereses es {dims}: "
                   + "; ".join(DIMENSIONES[d][1].lower() for d in dims[:2]) + "."),
        "fortalezas": [DIMENSIONES[d][0] for d in dims],
        "carreras": carreras,
        "siguiente_paso": "Elige una carrera de la lista y mira abajo dónde puedes estudiarla cerca de casa.",
        "fuente": "reglas",
    }


def recomendar(punt, ranking, oferta, sobre_mi: str = "", depto: str = "") -> dict:
    if not os.getenv("ANTHROPIC_API_KEY"):
        return recomendar_reglas(punt, ranking, oferta, sobre_mi, depto)
    try:
        import anthropic

        top = [a for a, _ in ranking[:4]]
        cands = _candidatos(oferta, top, depto=depto)
        entrada = {
            "region_del_estudiante": depto,
            "puntajes_riasec_0_100": punt,
            "codigo_holland": codigo_holland(punt),
            "areas_mas_afines": [{"area_id": a, "nombre": AREAS[a]["nombre"], "afinidad": s}
                                 for a, s in ranking[:4]],
            "lo_que_cuenta_el_estudiante": sobre_mi.strip()[:600] or "(no escribió nada)",
            "programas_disponibles_por_area": cands,
        }
        client = anthropic.Anthropic()
        resp = client.beta.messages.create(
            model=MODELO,
            max_tokens=4000,
            system=SISTEMA,
            messages=[{"role": "user", "content": json.dumps(entrada, ensure_ascii=False)}],
            output_config={"effort": "low", "format": {"type": "json_schema", "schema": ESQUEMA}},
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )
        if resp.stop_reason != "end_turn":
            raise RuntimeError(f"stop_reason={resp.stop_reason}")
        data = json.loads(next(b.text for b in resp.content if b.type == "text"))
        # Validación: solo programas que existen de verdad en la oferta
        validos = set(oferta["programa"])
        data["carreras"] = [c for c in data["carreras"] if c["programa"] in validos and c["area_id"] in AREAS]
        if not data["carreras"]:
            raise RuntimeError("sin carreras válidas")
        data["fuente"] = "ia"
        return data
    except Exception as e:  # la demo nunca se cae: plan B con reglas
        data = recomendar_reglas(punt, ranking, oferta, sobre_mi, depto)
        data["error_ia"] = str(e)[:200]
        return data
