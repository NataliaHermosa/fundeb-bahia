"""
Leitura da malha municipal da Bahia (IBGE) para os mapas.

O arquivo vem do IBGE e identifica cada município pelo campo "codarea"
(código de 7 dígitos), o mesmo codigo_ibge usado no banco.
"""

import json
from pathlib import Path

import streamlit as st

RAIZ_PROJETO = Path(__file__).resolve().parents[2]
CAMINHO_GEOJSON = RAIZ_PROJETO / "data" / "geo" / "bahia_municipios.geojson"

# Caminho da propriedade do GeoJSON que casa com o codigo_ibge do banco.
CHAVE_GEOJSON = "properties.codarea"

# Enquadramento inicial do mapa: centro e zoom que mostram a Bahia inteira.
CENTRO_MAPA = {"lat": -12.9, "lon": -41.7}
ZOOM_MAPA = 4.9


@st.cache_data
def carregar_geojson_bahia() -> dict:
    with open(CAMINHO_GEOJSON, encoding="utf-8") as arquivo:
        return json.load(arquivo)