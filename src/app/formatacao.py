"""
Funções de formatação no padrão brasileiro (ponto no milhar, vírgula no
decimal -- o oposto do padrão que o Python usa por padrão).
"""

import pandas as pd


def formatar_moeda(valor) -> str:
    """22834314.85 -> 'R$ 22.834.314,85'"""
    if valor is None or pd.isna(valor):
        return "—"
    texto = f"{valor:,.2f}"          # formato americano: '22,834,314.85'
    texto = texto.replace(",", "X")  # protege a vírgula de milhar
    texto = texto.replace(".", ",")  # ponto decimal -> vírgula decimal
    texto = texto.replace("X", ".")  # a vírgula protegida -> ponto de milhar
    return f"R$ {texto}"


def formatar_inteiro(valor) -> str:
    """133746 -> '133.746'"""
    if valor is None or pd.isna(valor):
        return "—"
    return f"{valor:,.0f}".replace(",", ".")


def formatar_percentual(valor, casas: int = 1) -> str:
    """70.456 -> '70,5%'"""
    if valor is None or pd.isna(valor):
        return "—"
    return f"{valor:.{casas}f}".replace(".", ",") + "%"