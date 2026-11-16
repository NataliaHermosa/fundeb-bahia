"""
Qualidade dos dados: descreve o que há nos indicadores legais do SIOPE no
banco, de 2021 em diante (novo FUNDEB). Só contagens e valores: a página não
explica causas, porque nenhuma fonte consultada as explica.
"""

from datetime import date

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.app.config import BIMESTRE_FECHAMENTO, INDICADORES, LIMITE_PLAUSIVEL
from src.app.dados import ANO_INICIAL, carregar_indicadores, carregar_municipios
from src.app.formatacao import formatar_inteiro, formatar_percentual

COR_NEGATIVO = "#1baf7a"
COR_ACIMA = "#2a78d6"
ANO_ATUAL = date.today().year

st.title("Qualidade dos dados")
st.caption(
    f"Indicadores legais do SIOPE de {ANO_INICIAL} em diante, quando passou a valer o "
    "novo FUNDEB (Lei 14.113/2020, art. 53). A página descreve o que está no banco; "
    "a causa de cada inconsistência não foi apurada."
)

df_ind = carregar_indicadores().copy()
df_mun = carregar_municipios()
n_mun = len(df_mun)

ROTULO = {c: d["rotulo"] for c, d in INDICADORES.items()}
NOME = {c: f"{d['rotulo']} — {d['nome']}" for c, d in INDICADORES.items()}
df_ind["ind"] = df_ind["codigo_indicador"].map(ROTULO)
df_ind["negativo"] = df_ind["valor_percentual"] < 0
df_ind["acima"] = df_ind["valor_percentual"] > LIMITE_PLAUSIVEL
df_ind["fora"] = df_ind["negativo"] | df_ind["acima"]
df_ind = df_ind.merge(df_mun, on="codigo_ibge", how="left")

def texto_valor(v) -> str:
    """-0.97 -> '-0,97' (vírgula decimal, como no resto do app)."""
    return "—" if pd.isna(v) else f"{v:.2f}".replace(".", ",")


fechados = df_ind[df_ind["ano"] < ANO_ATUAL]
fechamento = df_ind[df_ind["bimestre"] == BIMESTRE_FECHAMENTO]

# --- Resumo ------------------------------------------------------------------
fora = df_ind[df_ind["fora"]]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Registros", formatar_inteiro(len(df_ind)))
c2.metric(
    f"Fora de 0–100 ({formatar_percentual(100 * len(fora) / len(df_ind), 2)} dos registros)",
    formatar_inteiro(len(fora)),
)
c3.metric(
    "Municípios com algum registro fora",
    f"{formatar_inteiro(fora['codigo_ibge'].nunique())} de {formatar_inteiro(n_mun)}",
)
c4.metric(
    f"Fora de 0–100 no {BIMESTRE_FECHAMENTO}º bimestre",
    formatar_inteiro(int(fechamento["fora"].sum())),
)
st.caption(
    f"Negativos: {formatar_inteiro(int(df_ind['negativo'].sum()))} · "
    f"acima de {LIMITE_PLAUSIVEL:.0f}%: {formatar_inteiro(int(df_ind['acima'].sum()))} · "
    "valores vazios: "
    f"{formatar_inteiro(int(df_ind['valor_percentual'].isna().sum()))} · "
    "registros repetidos (mesmo município, ano, bimestre e indicador): "
    f"{formatar_inteiro(int(df_ind.duplicated(['codigo_ibge', 'ano', 'bimestre', 'codigo_indicador']).sum()))}."
)

st.divider()

# --- 1. O que entra na classificação -----------------------------------------
st.subheader(f"1. O que entra na classificação ({BIMESTRE_FECHAMENTO}º bimestre)")
st.caption(
    f"A situação de cada município em anos encerrados usa o {BIMESTRE_FECHAMENTO}º bimestre. "
    "Por isso esta é a parte que afeta o Panorama e a página Município."
)

fora_fech = fechamento[fechamento["fora"]]
if fora_fech.empty:
    st.success(f"Nenhum valor fora de 0–100 no {BIMESTRE_FECHAMENTO}º bimestre.")
else:
    st.markdown(
        f"**{len(fora_fech)} registro(s) fora de 0–100 no {BIMESTRE_FECHAMENTO}º bimestre:**"
    )
    tabela = fora_fech[["ano", "ind", "municipio", "valor_percentual"]].sort_values(
        ["ano", "ind", "municipio"]
    )
    tabela.columns = ["Ano", "Indicador", "Município", "Valor (%)"]
    tabela["Valor (%)"] = tabela["Valor (%)"].apply(texto_valor)
    st.dataframe(tabela, hide_index=True, width="stretch")

st.markdown(f"**Municípios com registro no {BIMESTRE_FECHAMENTO}º bimestre (de {n_mun})**")
cobertura = (
    fechamento[fechamento["ano"] < ANO_ATUAL]
    .groupby(["ind", "ano"])["codigo_ibge"].nunique()
    .unstack("ano", fill_value=0)
)
cobertura.index.name = "Indicador"
cobertura.columns = [str(c) for c in cobertura.columns]
st.dataframe(cobertura, width="stretch")
st.caption(
    "Número menor que o total significa município sem o indicador no 6º bimestre, o que o "
    "app mostra como “Sem declaração” (ou “Sem mínimo definido”, no caso do 1.6)."
)

# --- 2. Fora de 0–100 por bimestre -------------------------------------------
st.divider()
st.subheader("2. Valores fora de 0–100, por bimestre")

f1, f2 = st.columns([2, 1])
indicadores_presentes = sorted(df_ind["codigo_indicador"].unique(), key=lambda c: ROTULO[c])
escolha_ind = f1.selectbox(
    "Indicador", options=["Todos"] + indicadores_presentes,
    format_func=lambda c: c if c == "Todos" else NOME[c], key="q_ind",
)
anos = sorted(df_ind["ano"].unique())
escolha_ano = f2.selectbox("Ano", options=["Todos"] + [int(a) for a in anos], key="q_ano")

base = fora.copy()
if escolha_ind != "Todos":
    base = base[base["codigo_indicador"] == escolha_ind]
if escolha_ano != "Todos":
    base = base[base["ano"] == escolha_ano]

por_bim = base.groupby("bimestre").agg(
    negativos=("negativo", "sum"), acima=("acima", "sum")
).reindex(range(1, 7), fill_value=0)

if por_bim.sum().sum() == 0:
    st.info("Nenhum valor fora de 0–100 nesta seleção.")
else:
    fig = go.Figure()
    fig.add_bar(x=[f"{b}º" for b in por_bim.index], y=por_bim["negativos"],
                name="Negativos", marker_color=COR_NEGATIVO,
                hovertemplate="%{x} bimestre<br>Negativos: %{y}<extra></extra>")
    fig.add_bar(x=[f"{b}º" for b in por_bim.index], y=por_bim["acima"],
                name=f"Acima de {LIMITE_PLAUSIVEL:.0f}%", marker_color=COR_ACIMA,
                hovertemplate="%{x} bimestre<br>Acima de 100%: %{y}<extra></extra>")
    fig.update_layout(
        barmode="stack", height=320, margin=dict(l=10, r=10, t=10, b=10),
        xaxis_title="Bimestre", yaxis_title="Registros",
        legend=dict(orientation="h", y=1.12, x=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_traces(marker_line_color="rgba(0,0,0,0)", selector=dict(type="bar"))
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(128,128,128,0.2)")
    st.plotly_chart(fig, width="stretch")

st.markdown("**O que acontece no 6º bimestre quando há valor fora de 0–100 antes dele**")
intermediarios = fechados[fechados["fora"] & (fechados["bimestre"] < BIMESTRE_FECHAMENTO)]
chave = ["codigo_ibge", "ano", "codigo_indicador"]
b6 = fechamento[chave + ["fora"]].rename(columns={"fora": "fora6"})
cruz = intermediarios.merge(b6, on=chave, how="left")
cruz["situação do 6º bimestre"] = "ausente"
cruz.loc[cruz["fora6"].eq(False), "situação do 6º bimestre"] = "dentro de 0–100"
cruz.loc[cruz["fora6"].eq(True), "situação do 6º bimestre"] = "fora de 0–100"
if cruz.empty:
    st.caption("Sem registros fora de 0–100 nos bimestres 1 a 5 dos anos encerrados.")
else:
    resumo_cruz = cruz.groupby(["ind", "situação do 6º bimestre"]).size().unstack(fill_value=0)
    resumo_cruz["total"] = resumo_cruz.sum(axis=1)
    resumo_cruz.index.name = "Indicador"
    st.dataframe(resumo_cruz, width="stretch")
    st.caption(
        "Cada linha conta registros dos bimestres 1 a 5 (anos encerrados) fora de 0–100 e diz "
        "como está o 6º bimestre do mesmo município, ano e indicador."
    )

# --- 3. Ausências no 6º bimestre ---------------------------------------------
st.divider()
st.subheader(f"3. Indicador ausente no {BIMESTRE_FECHAMENTO}º bimestre")
linhas = []
for ano in sorted(int(a) for a in fechados["ano"].unique()):
    for codigo in indicadores_presentes:
        d = fechados[(fechados["ano"] == ano) & (fechados["codigo_indicador"] == codigo)]
        if d.empty:
            continue
        com6 = set(d.loc[d["bimestre"] == BIMESTRE_FECHAMENTO, "codigo_ibge"])
        sem6 = n_mun - len(com6)
        if sem6 == 0:
            continue
        ultimo = d[~d["codigo_ibge"].isin(com6)].groupby("codigo_ibge")["bimestre"].max()
        linha = {
            "Ano": ano, "Indicador": NOME[codigo], f"Sem o {BIMESTRE_FECHAMENTO}º bimestre": sem6,
            "Com registro em outros bimestres": len(ultimo),
            "Sem nenhum registro no ano": sem6 - len(ultimo),
        }
        for b in range(1, BIMESTRE_FECHAMENTO):
            linha[f"Último = {b}º"] = int((ultimo == b).sum())
        linhas.append(linha)
if linhas:
    st.dataframe(pd.DataFrame(linhas), hide_index=True, width="stretch",
                 height=35 * (len(linhas) + 1) + 3)
    st.caption(
        "“Último” é o último bimestre em que o município tem o indicador. Todo município tem "
        f"registro no {BIMESTRE_FECHAMENTO}º bimestre de algum indicador em todos os anos encerrados; "
        "a ausência é do indicador, não do município inteiro."
    )
else:
    st.success("Todos os municípios têm todos os indicadores no 6º bimestre.")

# --- 4. Quedas ---------------------------------------------------------------
with st.expander("Valores que caem de um bimestre para o seguinte"):
    d = df_ind.dropna(subset=["valor_percentual"]).sort_values(
        ["codigo_ibge", "ano", "codigo_indicador", "bimestre"])
    d["anterior"] = d.groupby(chave)["valor_percentual"].shift()
    d = d.dropna(subset=["anterior"])
    d["queda"] = d["valor_percentual"] < d["anterior"]
    d["queda10"] = (d["anterior"] - d["valor_percentual"]) > 10
    g = d.groupby(["ind", "ano"]).agg(
        pares=("queda", "size"), quedas=("queda", "sum"), mais_de_10pp=("queda10", "sum")
    ).reset_index()
    g["% com queda"] = (100 * g["quedas"] / g["pares"]).round(1)
    g.columns = ["Indicador", "Ano", "Pares de bimestres", "Quedas", "Quedas > 10 p.p.", "% com queda"]
    st.dataframe(g, hide_index=True, width="stretch")
    st.caption(
        "Os indicadores são acumulados no ano, então uma queda é um fato a descrever. "
        "Os dados não dizem se é erro ou ajuste da declaração."
    )

# --- 5. Registros ------------------------------------------------------------
with st.expander("Ver os registros fora de 0–100 desta seleção (seção 2)"):
    lista = base[["ano", "bimestre", "ind", "municipio", "valor_percentual"]].sort_values(
        ["ano", "ind", "bimestre", "municipio"])
    lista.columns = ["Ano", "Bimestre", "Indicador", "Município", "Valor (%)"]
    st.dataframe(lista.assign(**{"Valor (%)": lista["Valor (%)"].apply(texto_valor)}),
                 hide_index=True, width="stretch", height=400)
    st.download_button(
        "Baixar CSV", lista.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig"),
        file_name="registros_fora_de_0_100.csv", mime="text/csv",
    )