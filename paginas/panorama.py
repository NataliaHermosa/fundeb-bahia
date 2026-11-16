"""
Panorama Bahia: situação de conformidade dos 417 municípios, por indicador
legal e por ano.
"""

from datetime import date

import plotly.express as px
import streamlit as st

from src.app.config import (
    BIMESTRE_FECHAMENTO,
    CORES_SITUACOES,
    EXIGIR_FECHAMENTO,
    INDICADORES,
    ORDEM_SITUACOES,
    ROTULOS_SITUACOES,
    meta_vigente,
)
from src.app.dados import (
    carregar_indicadores,
    carregar_municipios,
    indicadores_com_classificacao,
    regra_por_municipio,
    situacao_municipios,
    tem_classificacao,
)
from src.app.formatacao import formatar_inteiro, formatar_percentual
from src.app.mapa import CENTRO_MAPA, CHAVE_GEOJSON, ZOOM_MAPA, carregar_geojson_bahia

st.title("Panorama da Bahia")
st.caption("Situação de conformidade com o FUNDEB nos 417 municípios baianos.")

df_mun = carregar_municipios()
df_ind = carregar_indicadores()

# --- Filtros -----------------------------------------------------------------
codigos = indicadores_com_classificacao()
col_filtro1, col_filtro2 = st.columns([2, 1])

codigo = col_filtro1.selectbox(
    "Indicador legal",
    options=codigos,
    format_func=lambda c: f"{INDICADORES[c]['rotulo']} — {INDICADORES[c]['nome']}",
)

anos_do_indicador = sorted(
    {int(a) for a in df_ind.loc[df_ind["codigo_indicador"] == codigo, "ano"].unique()
     if tem_classificacao(codigo, int(a))},
    reverse=True,
)
if not anos_do_indicador:
    st.warning("Não há dados com meta legal vigente para este indicador.")
    st.stop()

# Padrão: último ano já encerrado (se houver); senão o mais recente.
encerrados = [a for a in anos_do_indicador if a < date.today().year]
indice_padrao = anos_do_indicador.index(encerrados[0]) if encerrados else 0
ano = col_filtro2.selectbox("Ano", options=anos_do_indicador, index=indice_padrao)

meta = meta_vigente(codigo, ano)
regra = None if meta is not None else regra_por_municipio(codigo, ano)
por_municipio = regra is not None
resultado = situacao_municipios(df_ind, df_mun, ano, codigo)

if por_municipio:
    st.markdown(
        "**Meta legal:** mínimo definido para cada município "
        f"(IEI, indicador 1.7, do {regra['bimestre_minimo']}º bimestre do ano) "
        f"· {regra['base_legal']}"
    )
else:
    sinal = "≥" if meta["tipo"] == "minimo" else "≤"
    st.markdown(
        f"**Meta legal:** {sinal} {formatar_percentual(meta['limite'], 0)} "
        f"· {meta['base_legal']}"
    )
st.caption(INDICADORES[codigo]["descricao"])

if por_municipio:
    st.warning(regra["nota_metodologica"])
elif not meta["validada"]:
    st.warning(
        "A base legal desta meta ainda não foi confirmada. "
        "Use esta classificação apenas como referência."
    )
if ano >= date.today().year:
    st.info(
        f"{ano} ainda não terminou: os percentuais são parciais, e quem ainda não "
        "atingiu a meta aparece como “Em andamento”, não como “Não conforme”."
    )

# --- Totais ------------------------------------------------------------------
contagem = resultado["situacao"].value_counts().reindex(ORDEM_SITUACOES, fill_value=0)
avaliados = int(contagem["Conforme"] + contagem["Não conforme"])
colunas = st.columns(len(ORDEM_SITUACOES))
for coluna, situacao in zip(colunas, ORDEM_SITUACOES):
    coluna.metric(ROTULOS_SITUACOES[situacao], formatar_inteiro(contagem[situacao]))

if contagem["Sem declaração"] > 0:
    if ano >= date.today().year or not EXIGIR_FECHAMENTO:
        explicacao = "o município não declarou este indicador no ano."
    else:
        explicacao = (
            f"o município não declarou o {BIMESTRE_FECHAMENTO}º bimestre "
            "(fechamento do ano) para este indicador; pode ter declarado "
            "bimestres anteriores."
        )
    st.caption(f"**Sem declaração:** {explicacao}")

if contagem["Sem mínimo definido"] > 0:
    st.caption(
        "**Sem mínimo definido:** o município não tem IEI (indicador 1.7) maior "
        f"que zero no {regra['bimestre_minimo']}º bimestre do ano (zero ou ausente "
        "no SIOPE); por isso não é classificado."
    )

if avaliados:
    st.caption(
        f"Entre os {formatar_inteiro(avaliados)} municípios avaliados "
        f"(conformes + não conformes), {formatar_percentual(100 * contagem['Conforme'] / avaliados)} "
        "cumprem a meta."
    )

st.divider()

# --- Mapa e tabela -----------------------------------------------------------
resultado = resultado.copy()
resultado["situacao_rotulo"] = resultado["situacao"].map(ROTULOS_SITUACOES)
resultado["valor_texto"] = resultado["valor_percentual"].apply(formatar_percentual)
resultado["codigo_texto"] = resultado["codigo_ibge"].astype(str)
if por_municipio:
    resultado["limite_texto"] = resultado["limite"].apply(formatar_percentual)

aba_mapa, aba_tabela = st.tabs(["🗺️ Mapa", "📋 Tabela"])

hover_data = {"situacao_rotulo": True, "valor_texto": True, "codigo_texto": False}
if por_municipio:
    hover_data["limite_texto"] = True

with aba_mapa:
    figura = px.choropleth_map(
        resultado,
        geojson=carregar_geojson_bahia(),
        locations="codigo_texto",
        featureidkey=CHAVE_GEOJSON,
        color="situacao_rotulo",
        color_discrete_map={ROTULOS_SITUACOES[s]: CORES_SITUACOES[s] for s in ORDEM_SITUACOES},
        category_orders={"situacao_rotulo": [ROTULOS_SITUACOES[s] for s in ORDEM_SITUACOES]},
        hover_name="municipio",
        hover_data=hover_data,
        labels={"situacao_rotulo": "Situação", "valor_texto": "Valor declarado",
                "limite_texto": "Mínimo (IEI)"},
        center=CENTRO_MAPA,
        zoom=ZOOM_MAPA,
        map_style="carto-positron",
        opacity=0.85,
    )
    figura.update_traces(marker_line_width=0.4, marker_line_color="#ffffff")
    figura.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        height=620,
        legend=dict(title="Situação", orientation="v", x=0.01, y=0.01, yanchor="bottom"),
    )
    st.plotly_chart(figura, width="stretch")

with aba_tabela:
    escolhidas = st.multiselect(
        "Filtrar por situação",
        options=ORDEM_SITUACOES,
        default=ORDEM_SITUACOES,
        format_func=lambda s: ROTULOS_SITUACOES[s],
    )
    colunas_tabela = ["municipio", "situacao_rotulo", "valor_percentual", "bimestre"]
    if por_municipio:
        colunas_tabela.insert(3, "limite")
    tabela = resultado[resultado["situacao"].isin(escolhidas)][colunas_tabela].rename(columns={
        "municipio": "Município",
        "situacao_rotulo": "Situação",
        "valor_percentual": "Valor declarado (%)",
        "limite": "Mínimo (IEI, %)",
        "bimestre": "Bimestre",
    })
    st.dataframe(tabela, hide_index=True, width="stretch")