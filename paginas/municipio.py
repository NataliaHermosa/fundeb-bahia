"""
Município: situação de um município em todos os indicadores legais, no ano
escolhido. Usa a mesma regra de classificação do Panorama.
"""

from datetime import date

import pandas as pd
import streamlit as st

from src.app.config import (
    CORES_SITUACOES,
    INDICADORES,
    ORDEM_SITUACOES,
    ROTULOS_SITUACOES,
)
from src.app.dados import (
    carregar_indicadores,
    carregar_municipios,
    indicadores_com_classificacao,
    regra_por_municipio,
    resumo_municipio,
    serie_municipio,
    tem_classificacao,
)
from src.app.graficos import linha_do_tempo
from src.app.formatacao import formatar_inteiro, formatar_percentual

# Cores escuras pedem texto branco; âmbar e cinza claro pedem texto escuro.
TEXTO_CLARO = {"Conforme", "Não conforme", "Sem mínimo definido", "Inconsistente"}

st.title("Município")
st.caption("Situação de um município em cada indicador legal do FUNDEB.")

df_mun = carregar_municipios()
df_ind = carregar_indicadores()

# --- Filtros -----------------------------------------------------------------
anos_disponiveis = sorted(
    {int(a) for a in df_ind["ano"].unique()
     if any(tem_classificacao(c, int(a)) for c in indicadores_com_classificacao())},
    reverse=True,
)
if not anos_disponiveis:
    st.warning("Não há dados com meta legal vigente.")
    st.stop()

nomes = df_mun.sort_values("municipio")
col1, col2 = st.columns([2, 1])
nome_escolhido = col1.selectbox(
    "Município",
    options=nomes["municipio"].tolist(),
    index=None,
    placeholder="Digite ou escolha um município",
)
encerrados = [a for a in anos_disponiveis if a < date.today().year]
indice_padrao = anos_disponiveis.index(encerrados[0]) if encerrados else 0
ano = col2.selectbox("Ano", options=anos_disponiveis, index=indice_padrao)

if nome_escolhido is None:
    st.info("Escolha um município para ver a situação em cada indicador.")
    st.stop()

linha_mun = nomes[nomes["municipio"] == nome_escolhido].iloc[0]
codigo_ibge = int(linha_mun["codigo_ibge"])
resumo = resumo_municipio(df_ind, df_mun, codigo_ibge, ano)

st.subheader(f"{nome_escolhido} · {ano}")
st.caption(f"Código IBGE {codigo_ibge}")

if ano >= date.today().year:
    st.info(
        f"{ano} ainda não terminou: os percentuais são parciais, e quem ainda não "
        "atingiu a meta aparece como “Em andamento”, não como “Não conforme”."
    )

if resumo.empty:
    st.warning("Este município não tem indicadores com meta legal vigente neste ano.")
    st.stop()

# --- Totais ------------------------------------------------------------------
contagem = resumo["situacao"].value_counts().reindex(ORDEM_SITUACOES, fill_value=0)
colunas = st.columns(len(ORDEM_SITUACOES))
for coluna, situacao in zip(colunas, ORDEM_SITUACOES):
    coluna.metric(ROTULOS_SITUACOES[situacao], formatar_inteiro(contagem[situacao]))

# --- Tabela por indicador ----------------------------------------------------
def texto_meta(linha) -> str:
    if linha["por_municipio"]:
        if pd.isna(linha["limite"]) or linha["limite"] <= 0:
            return "sem mínimo definido"
        return f"≥ {formatar_percentual(linha['limite'])} (IEI do município)"
    sinal = "≥" if linha["tipo_meta"] == "minimo" else "≤"
    return f"{sinal} {formatar_percentual(linha['limite'], 0)}"


tabela = resumo.copy()
tabela["Indicador"] = tabela["rotulo"] + " — " + tabela["nome"]
tabela["Valor declarado"] = tabela["valor_percentual"].apply(formatar_percentual)
tabela["Meta legal"] = tabela.apply(texto_meta, axis=1)
tabela["Bimestre"] = tabela["bimestre"].apply(
    lambda b: "—" if pd.isna(b) else f"{int(b)}º"
)
def base_da_meta(linha) -> str:
    if linha["por_municipio"]:
        return "decisão metodológica"
    return "validada na lei" if linha["validada"] else "não validada"


tabela["Base da meta"] = tabela.apply(base_da_meta, axis=1)
tabela["Situação"] = tabela["situacao"].map(ROTULOS_SITUACOES)
mostrar = tabela[["Indicador", "Valor declarado", "Meta legal", "Bimestre", "Base da meta", "Situação"]]


def colorir(coluna):
    estilos = []
    for rotulo in coluna:
        situacao = next((s for s, r in ROTULOS_SITUACOES.items() if r == rotulo), None)
        if situacao is None:
            estilos.append("")
            continue
        cor_texto = "#ffffff" if situacao in TEXTO_CLARO else "#1a1a1a"
        estilos.append(f"background-color: {CORES_SITUACOES[situacao]}; color: {cor_texto}")
    return estilos


st.dataframe(
    mostrar.style.apply(colorir, subset=["Situação"]),
    hide_index=True,
    width="stretch",
)

# --- Avisos por indicador ----------------------------------------------------
pendentes = resumo[(~resumo["validada"]) & (~resumo["por_municipio"])]
if not pendentes.empty:
    nao_validados = ", ".join(pendentes["rotulo"])
    st.caption(
        f"**Meta não validada** ({nao_validados}): a base legal ainda não foi "
        "confirmada. Use a classificação apenas como referência."
    )

if (resumo["codigo_indicador"] == 90).any():
    regra = regra_por_municipio(90, ano)
    if regra is not None:
        with st.expander("Como o mínimo do 1.6 é definido para este município"):
            st.markdown(regra["nota_metodologica"])

if (resumo["situacao"] == "Sem declaração").any():
    st.caption(
        "**Sem declaração:** o município não declarou o 6º bimestre (fechamento do ano) "
        "para este indicador; pode ter declarado bimestres anteriores."
    )

# --- Linha do tempo ----------------------------------------------------------
st.divider()
st.subheader("Evolução ao longo do tempo")

codigos_serie = indicadores_com_classificacao()
codigo_serie = st.selectbox(
    "Indicador",
    options=codigos_serie,
    format_func=lambda c: f"{INDICADORES[c]['rotulo']} — {INDICADORES[c]['nome']}",
    key="indicador_linha_do_tempo",
)
serie = serie_municipio(df_ind, codigo_ibge, codigo_serie)

if serie.empty:
    st.info("Este município não tem valores declarados para este indicador.")
else:
    por_municipio_serie = INDICADORES[codigo_serie].get("minimo_por_municipio") is not None
    rotulo_meta = "Mínimo (IEI do município)" if por_municipio_serie else "Meta legal"
    st.plotly_chart(linha_do_tempo(serie, rotulo_meta), width="stretch")
    st.caption(
        "O valor do SIOPE é acumulado no ano e recomeça em janeiro, por isso a "
        "linha é interrompida entre os anos. A linha tracejada é a meta de cada ano."
    )
    inconsistentes = int(serie["inconsistente"].sum())
    if inconsistentes:
        st.caption(
            f"{inconsistentes} registro(s) fora de ±100% não aparecem no gráfico "
            "(tratados como inconsistentes)."
        )
    with st.expander("Ver os dados do gráfico"):
        dados_tabela = serie.copy()
        dados_tabela["Ano"] = dados_tabela["ano"].astype(int)
        dados_tabela["Bimestre"] = dados_tabela["bimestre"].astype(int).astype(str) + "º"
        dados_tabela["Valor declarado"] = dados_tabela["valor_percentual"].apply(formatar_percentual)
        dados_tabela["Meta"] = dados_tabela["limite"].apply(formatar_percentual)
        st.dataframe(
            dados_tabela[["Ano", "Bimestre", "Valor declarado", "Meta"]],
            hide_index=True, width="stretch",
        )