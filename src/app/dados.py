"""
Camada de dados do app: conexão com o Postgres, consultas em cache e a regra
que classifica cada município (conforme / não conforme / ...).

Nenhuma consulta depende de "primeira linha da tabela": tudo cobre os
municípios da Bahia ou recebe o código IBGE como parâmetro.

Fonte dos dados: o app lê do Postgres quando há DB_PASSWORD no ambiente (.env
local). Sem ela, ou com FUNDEB_FONTE=arquivos, lê os arquivos Parquet de
data/app/ (gerados por src/etl/exportar_dados.py), que é o caso da publicação
no Streamlit Community Cloud.
"""

import os
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from src.app.config import (
    BIMESTRE_FECHAMENTO,
    EXIGIR_FECHAMENTO,
    INDICADORES,
    LIMITE_PLAUSIVEL,
    meta_vigente,
)

# src/app/dados.py -> parents[2] é a raiz do projeto (onde fica o .env)
RAIZ_PROJETO = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ_PROJETO / ".env")

# Pasta com os arquivos Parquet exportados do banco.
DIRETORIO_DADOS = RAIZ_PROJETO / "data" / "app"

# Primeiro ano da análise: o novo FUNDEB (Lei 14.113/2020) vale a partir de
# 1º/1/2021, quando a Lei 11.494/2007 foi revogada (art. 53). Os anos
# anteriores continuam no banco, mas não entram no app.
ANO_INICIAL = 2021


# ---------------------------------------------------------------------------
# Conexão e consultas
# ---------------------------------------------------------------------------

def usar_arquivos() -> bool:
    """True quando o app deve ler os arquivos Parquet em vez do Postgres."""
    return os.getenv("FUNDEB_FONTE") == "arquivos" or not os.getenv("DB_PASSWORD")


def _ler_parquet(nome: str) -> pd.DataFrame:
    return pd.read_parquet(DIRETORIO_DADOS / f"{nome}.parquet")


@st.cache_resource
def obter_engine():
    """Cria a conexão com o Postgres uma única vez."""
    url = URL.create(
        drivername="postgresql+psycopg2",
        username=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "observatorio_fundeb"),
    )
    return create_engine(url)


def _consultar(sql: str, parametros: dict | None = None) -> pd.DataFrame:
    with obter_engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=parametros)


@st.cache_data(ttl=600)
def carregar_municipios() -> pd.DataFrame:
    """Os 417 municípios da Bahia: codigo_ibge (7 dígitos) e nome."""
    if usar_arquivos():
        df = _ler_parquet("municipios").sort_values("nome")
    else:
        df = _consultar("SELECT codigo_ibge, nome FROM municipios ORDER BY nome")
    df["codigo_ibge"] = df["codigo_ibge"].astype(int)
    return df.rename(columns={"nome": "municipio"})


@st.cache_data(ttl=600)
def carregar_indicadores() -> pd.DataFrame:
    """Indicadores legais do SIOPE (% acumulado no ano, por bimestre)."""
    if usar_arquivos():
        df = _ler_parquet("indicadores")
        df = df[df["ano"] >= ANO_INICIAL].copy()
    else:
        df = _consultar("""
            SELECT codigo_ibge, ano, bimestre, codigo_indicador, indicador,
                   valor_percentual
            FROM siope_indicadores_legais
            WHERE ano >= :ano_inicial
        """, {"ano_inicial": ANO_INICIAL})
    df["codigo_ibge"] = df["codigo_ibge"].astype(int)
    df["valor_percentual"] = pd.to_numeric(df["valor_percentual"], errors="coerce")
    return df


@st.cache_data(ttl=600)
def carregar_receita_mensal() -> pd.DataFrame:
    """Receita mensal de FUNDEB e AJUSTE FUNDEB (R$), da STN."""
    if usar_arquivos():
        df = _ler_parquet("receita_mensal")
    else:
        df = _consultar("""
            SELECT codigo_ibge, ano, mes, transferencia, valor_reais
            FROM stn_fundeb_mensal
        """)
    df["codigo_ibge"] = df["codigo_ibge"].astype(int)
    df["valor_reais"] = pd.to_numeric(df["valor_reais"], errors="coerce")
    return df


# ---------------------------------------------------------------------------
# Classificação de conformidade
# ---------------------------------------------------------------------------

def regra_por_municipio(codigo_indicador, ano):
    """Regra de mínimo por município (caso do 1.6, cuja meta é o IEI/1.7 de
    cada município), ou None se o indicador não tem essa regra no ano."""
    regra = INDICADORES.get(codigo_indicador, {}).get("minimo_por_municipio")
    if regra is None:
        return None
    if regra["de"] <= ano and (regra["ate"] is None or ano <= regra["ate"]):
        return regra
    return None


def indicadores_com_classificacao():
    """Códigos que o app consegue classificar: os que têm meta legal única
    (config.metas) e os que têm mínimo por município."""
    return [
        cod for cod, ind in INDICADORES.items()
        if ind["metas"] or ind.get("minimo_por_municipio")
    ]


def tem_classificacao(codigo_indicador, ano) -> bool:
    return (
        meta_vigente(codigo_indicador, ano) is not None
        or regra_por_municipio(codigo_indicador, ano) is not None
    )


def _classificar(valor, meta, em_andamento: bool) -> str:
    if pd.isna(valor):
        return "Sem declaração"
    if abs(valor) > LIMITE_PLAUSIVEL:
        return "Inconsistente"
    if meta["tipo"] == "minimo":
        cumpre = valor >= meta["limite"]
    else:
        cumpre = valor <= meta["limite"]
    if cumpre:
        return "Conforme"
    # No ano corrente os percentuais ainda são parciais: quem ainda não
    # atingiu a meta está "em andamento", não "não conforme".
    return "Em andamento" if em_andamento else "Não conforme"


def _classificar_por_municipio(valor, minimo, em_andamento: bool) -> str:
    # Sem mínimo (IEI zero, ausente ou fora da Portaria): não se classifica.
    if pd.isna(minimo) or minimo <= 0:
        return "Sem mínimo definido"
    return _classificar(valor, {"tipo": "minimo", "limite": minimo}, em_andamento)


def situacao_municipios(df_ind, df_mun, ano: int, codigo_indicador: int) -> pd.DataFrame:
    """Uma linha por município (todos os 417), com o valor de referência do
    indicador no ano e a situação de conformidade.

    - Ano encerrado: avalia o 6º bimestre (fechamento). Se
      EXIGIR_FECHAMENTO for False, usa o último bimestre declarado.
    - Ano corrente: usa o último bimestre declarado, e quem ainda não
      atingiu a meta aparece como "Em andamento".
    - Indicador com mínimo por município (1.6): o mínimo de cada município é
      o 1.7 do bimestre definido em config (minimo_por_municipio: 6º bimestre).
    """
    meta = meta_vigente(codigo_indicador, ano)
    regra = None if meta is not None else regra_por_municipio(codigo_indicador, ano)
    if meta is None and regra is None:
        raise ValueError(
            f"Indicador {codigo_indicador} não tem meta legal vigente em {ano}."
        )

    em_andamento = ano >= date.today().year

    base = df_ind[
        (df_ind["ano"] == ano) & (df_ind["codigo_indicador"] == codigo_indicador)
    ]
    if em_andamento or not EXIGIR_FECHAMENTO:
        referencia = base.sort_values("bimestre").drop_duplicates("codigo_ibge", keep="last")
    else:
        referencia = base[base["bimestre"] == BIMESTRE_FECHAMENTO]

    referencia = referencia[["codigo_ibge", "bimestre", "valor_percentual"]]
    resultado = df_mun.merge(referencia, on="codigo_ibge", how="left")

    if regra is None:
        resultado["situacao"] = resultado["valor_percentual"].apply(
            lambda v: _classificar(v, meta, em_andamento)
        )
        resultado["limite"] = meta["limite"]
        resultado["tipo_meta"] = meta["tipo"]
        return resultado

    minimos = df_ind[
        (df_ind["ano"] == ano)
        & (df_ind["codigo_indicador"] == regra["indicador_minimo"])
        & (df_ind["bimestre"] == regra["bimestre_minimo"])
    ][["codigo_ibge", "valor_percentual"]].rename(columns={"valor_percentual": "limite"})
    minimos = minimos.drop_duplicates("codigo_ibge")
    resultado = resultado.merge(minimos, on="codigo_ibge", how="left")
    resultado["situacao"] = [
        _classificar_por_municipio(v, m, em_andamento)
        for v, m in zip(resultado["valor_percentual"], resultado["limite"])
    ]
    resultado["tipo_meta"] = "minimo"
    return resultado


def resumo_municipio(df_ind, df_mun, codigo_ibge, ano: int) -> pd.DataFrame:
    """Situação de UM município em cada indicador que tem classificação no ano.

    Usa a mesma regra do Panorama (situacao_municipios), então os dois nunca
    divergem. Uma linha por indicador; indicadores sem meta no ano ficam de fora.
    """
    linhas = []
    for codigo in indicadores_com_classificacao():
        if not tem_classificacao(codigo, ano):
            continue
        resultado = situacao_municipios(df_ind, df_mun, ano, codigo)
        do_municipio = resultado[resultado["codigo_ibge"] == codigo_ibge]
        if do_municipio.empty:
            continue
        linha = do_municipio.iloc[0]
        meta = meta_vigente(codigo, ano)
        regra = None if meta is not None else regra_por_municipio(codigo, ano)
        origem = meta if meta is not None else regra
        linhas.append({
            "codigo_indicador": codigo,
            "rotulo": INDICADORES[codigo]["rotulo"],
            "nome": INDICADORES[codigo]["nome"],
            "valor_percentual": linha["valor_percentual"],
            "bimestre": linha["bimestre"],
            "situacao": linha["situacao"],
            "limite": linha["limite"],
            "tipo_meta": linha["tipo_meta"],
            "por_municipio": regra is not None,
            "validada": bool(origem["validada"]),
        })
    return pd.DataFrame(linhas)


def serie_municipio(df_ind, codigo_ibge, codigo_indicador) -> pd.DataFrame:
    """Valores de UM município em UM indicador, por ano e bimestre, com a meta
    que valia no ano (a mesma usada na classificação).

    - Indicador com meta única: `limite` é a meta vigente do ano.
    - Indicador com mínimo por município (1.6): `limite` é o 1.7 do município
      no bimestre definido em config (6º), repetido em todos os bimestres do ano.
    - `limite` fica NaN quando o ano não tem meta ou o mínimo é zero/ausente.
    - Valores fora de ±LIMITE_PLAUSIVEL ficam marcados em `inconsistente`.
    """
    base = df_ind[
        (df_ind["codigo_ibge"] == codigo_ibge)
        & (df_ind["codigo_indicador"] == codigo_indicador)
    ][["ano", "bimestre", "valor_percentual"]]
    base = base.sort_values(["ano", "bimestre"]).drop_duplicates(["ano", "bimestre"], keep="last")
    base = base.reset_index(drop=True)

    limites = []
    tipos = []
    for ano in base["ano"]:
        ano = int(ano)
        meta = meta_vigente(codigo_indicador, ano)
        if meta is not None:
            limites.append(float(meta["limite"]))
            tipos.append(meta["tipo"])
            continue
        regra = regra_por_municipio(codigo_indicador, ano)
        if regra is None:
            limites.append(float("nan"))
            tipos.append(None)
            continue
        minimo = df_ind[
            (df_ind["codigo_ibge"] == codigo_ibge)
            & (df_ind["ano"] == ano)
            & (df_ind["codigo_indicador"] == regra["indicador_minimo"])
            & (df_ind["bimestre"] == regra["bimestre_minimo"])
        ]["valor_percentual"]
        valor = float(minimo.iloc[0]) if len(minimo) else float("nan")
        limites.append(valor if valor == valor and valor > 0 else float("nan"))
        tipos.append("minimo")
    base["limite"] = limites
    base["tipo_meta"] = tipos
    base["inconsistente"] = base["valor_percentual"].abs() > LIMITE_PLAUSIVEL
    return base