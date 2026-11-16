"""
Gráficos do app (Plotly). Hoje: a linha do tempo de um município em um indicador.
"""

import plotly.graph_objects as go

from src.app.formatacao import formatar_percentual

# Cor da série: azul-esverdeado da paleta categórica, que não é usada para
# nenhuma situação (conforme/não conforme/etc.). A meta usa cinza neutro.
COR_VALOR = "#1baf7a"
COR_META = "#8a8985"
LARGURA_ANO = 0.85  # fração do eixo ocupada pelos 6 bimestres de cada ano


def _posicao(ano, bimestre):
    return ano + (bimestre - 1) * LARGURA_ANO / 5


def linha_do_tempo(serie, rotulo_meta="Meta legal"):
    """Linha do valor declarado por bimestre, com quebra entre anos (o valor
    do SIOPE é acumulado no ano e recomeça em janeiro) e a meta de cada ano
    como segmento tracejado. `serie` vem de dados.serie_municipio."""
    plotaveis = serie[~serie["inconsistente"]]
    x, y, textos = [], [], []
    anos = sorted(int(a) for a in plotaveis["ano"].unique())
    for ano in anos:
        do_ano = plotaveis[plotaveis["ano"] == ano]
        for _, linha in do_ano.iterrows():
            x.append(_posicao(ano, int(linha["bimestre"])))
            y.append(float(linha["valor_percentual"]))
            meta = formatar_percentual(linha["limite"]) if linha["limite"] == linha["limite"] else "—"
            textos.append([f"{ano} · {int(linha['bimestre'])}º bimestre",
                           formatar_percentual(linha["valor_percentual"]), meta])
        x.append(None); y.append(None); textos.append(["", "", ""])

    figura = go.Figure()
    figura.add_trace(go.Scatter(
        x=x, y=y, mode="lines+markers", name="Valor declarado",
        line=dict(color=COR_VALOR, width=2), marker=dict(size=8, color=COR_VALOR),
        customdata=textos, connectgaps=False,
        hovertemplate=("<b>%{customdata[0]}</b><br>Valor declarado: %{customdata[1]}"
                       f"<br>{rotulo_meta}: " "%{customdata[2]}<extra></extra>"),
    ))

    mx, my = [], []
    for ano in anos:
        limite = plotaveis.loc[plotaveis["ano"] == ano, "limite"].dropna()
        if limite.empty:
            continue
        mx += [ano, ano + LARGURA_ANO, None]
        my += [float(limite.iloc[0]), float(limite.iloc[0]), None]
    tem_meta = any(v is not None for v in my)
    if tem_meta:
        figura.add_trace(go.Scatter(
            x=mx, y=my, mode="lines", name=rotulo_meta,
            line=dict(color=COR_META, width=2, dash="dash"),
            hoverinfo="skip", connectgaps=False,
        ))

    figura.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        height=380,
        showlegend=tem_meta,
        legend=dict(orientation="h", x=0, y=1.12),
        yaxis=dict(title="% declarado", gridcolor="rgba(128,128,128,0.25)", zeroline=False),
        xaxis=dict(
            tickmode="array",
            tickvals=[a + LARGURA_ANO / 2 for a in anos],
            ticktext=[str(a) for a in anos],
            showgrid=False,
        ),
        hovermode="closest",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return figura