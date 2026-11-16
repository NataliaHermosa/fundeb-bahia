"""
Configuração central do app: indicadores legais do FUNDEB, metas (limites)
com base legal e vigência, regras de leitura dos dados e cores.

Tudo que é "regra de pesquisa" mora aqui, num lugar só, para poder ser
revisado (e citado no método do artigo) sem mexer nas páginas.
"""

# ---------------------------------------------------------------------------
# Regras de leitura dos dados
# ---------------------------------------------------------------------------

# Os percentuais do SIOPE são acumulados desde janeiro; a meta legal só vale
# no fechamento do exercício, ou seja, no 6º bimestre.
BIMESTRE_FECHAMENTO = 6

# True  -> em anos já encerrados, só avalia a conformidade se o município
#          declarou o 6º bimestre (senão: "Sem declaração").
# False -> em anos encerrados, usa o último bimestre declarado (menos rigoroso).
EXIGIR_FECHAMENTO = True

# Valores fora de -100% a 100% são tratados como inconsistentes
# (provável erro de autodeclaração do município ao SIOPE).
LIMITE_PLAUSIVEL = 100.0

# ---------------------------------------------------------------------------
# Indicadores legais do SIOPE (grupo 1) e suas metas
# ---------------------------------------------------------------------------
# Cada meta tem: tipo ("minimo" ou "maximo"), limite (em %), vigência
# (de/ate, em anos; ate=None significa "até hoje"), base legal e se a
# base legal já foi conferida ("validada").
#
# Indicadores sem meta única nacional (metas=[]) aparecem nas séries, mas
# não são classificados como conforme/não conforme.

INDICADORES = {
    24: {
        "rotulo": "1.1",
        "nome": "Aplicação em MDE",
        "descricao": "% da receita de impostos e transferências aplicado em manutenção e desenvolvimento do ensino (MDE)",
        "metas": [
            {"tipo": "minimo", "limite": 25.0, "de": 2017, "ate": None,
             "base_legal": "CF/1988, art. 212", "validada": True},
        ],
    },
    67: {
        "rotulo": "1.2",
        "nome": "Remuneração dos profissionais",
        "descricao": "% do FUNDEB aplicado na remuneração dos profissionais da educação básica",
        "metas": [
            {"tipo": "minimo", "limite": 60.0, "de": 2017, "ate": 2020,
             "base_legal": "Lei 11.494/2007, art. 22 (revogada)", "validada": True},
            {"tipo": "minimo", "limite": 70.0, "de": 2021, "ate": None,
             "base_legal": "Lei 14.113/2020, art. 26", "validada": True},
        ],
    },
    68: {
        "rotulo": "1.3",
        "nome": "Outras despesas de MDE",
        "descricao": "% do FUNDEB aplicado em despesas de MDE que não são remuneração",
        # Os limites vêm do nome do indicador no SIOPE ("máx. 30-40%"). A
        # Lei 14.113/2020 (art. 26) fixa só o mínimo de 70% em remuneração e
        # não traz um teto equivalente: por isso "validada" é False.
        "metas": [
            {"tipo": "maximo", "limite": 40.0, "de": 2017, "ate": 2020,
             "base_legal": "Limite indicado pelo SIOPE (indicador 1.3); a lei não traz teto equivalente",
             "validada": False},
            {"tipo": "maximo", "limite": 30.0, "de": 2021, "ate": None,
             "base_legal": "Limite indicado pelo SIOPE (indicador 1.3); a lei não traz teto equivalente",
             "validada": False},
        ],
    },
    27: {
        "rotulo": "1.4",
        "nome": "Saldo não aplicado",
        "descricao": "% das receitas do FUNDEB não aplicadas no exercício",
        "metas": [
            {"tipo": "maximo", "limite": 5.0, "de": 2017, "ate": 2020,
             "base_legal": "Lei 11.494/2007, art. 21, §2º (revogada)", "validada": True},
            {"tipo": "maximo", "limite": 10.0, "de": 2021, "ate": None,
             "base_legal": "Lei 14.113/2020, art. 25, §3º", "validada": True},
        ],
    },
    89: {
        "rotulo": "1.5",
        "nome": "VAAT em despesas de capital",
        "descricao": "% da complementação-VAAT aplicado em despesas de capital",
        "metas": [
            {"tipo": "minimo", "limite": 15.0, "de": 2021, "ate": None,
             "base_legal": "Lei 14.113/2020, art. 27", "validada": True},
        ],
    },
    90: {
        "rotulo": "1.6",
        "nome": "VAAT na educação infantil",
        "descricao": "% de aplicação em despesas na educação infantil com a complementação-VAAT (no SIOPE: proporção de 50% do VAAT total, §3º do art. 212-A da CF)",
        # Sem meta única nacional: a meta é o IEI de cada município (indicador
        # 1.7). Por isso "metas" fica vazio e a regra está em
        # "minimo_por_municipio", lida só pelas funções específicas.
        "metas": [],
        "minimo_por_municipio": {
            "indicador_minimo": 92,      # código do 1.7 (IEI)
            "bimestre_minimo": 6,        # valor do 6º bimestre do ano
            "de": 2021, "ate": None,
            "base_legal": "Lei 14.113/2020, art. 28, parágrafo único (o IEI fixa o percentual mínimo por município)",
            # False: a comparação 1.6 >= 1.7 é decisão metodológica da pesquisa.
            "validada": False,
            "nota_metodologica": (
                "**Decisão metodológica da pesquisa.** A Lei 14.113/2020 (art. 28 e "
                "parágrafo único) diz que o Indicador de Educação Infantil (IEI) fixa o "
                "percentual mínimo da complementação-VAAT que cada município beneficiado "
                "deve aplicar em educação infantil, de modo que o conjunto atinja 50%. "
                "A lei não manda comparar o indicador 1.6 com o 1.7 e não diz qual "
                "publicação do IEI prevalece. Essas duas escolhas são da pesquisa.\n\n"
                "**Base legal por ano.** Nos exercícios de 2021 a 2023 o art. 43, §1º, III, "
                "permitiu metodologia provisória do Inep. A metodologia do indicador foi "
                "aprovada pela Resolução MEC nº 1/2021 (vigência em 2022), reaprovada pela "
                "Resolução CIF nº 6/2022 (vigência em 2023) e aprovada pela Resolução CIF "
                "nº 1/2023, art. 9º (cuja ementa trata da vigência em 2024). Para 2025, a "
                "aprovação consta da Resolução nº 4, de 26 de julho de 2024.\n\n"
                "**Como o mínimo é obtido.** O mínimo de cada município é o valor do "
                "indicador 1.7 registrado no SIOPE no 6º bimestre do ano. O art. 16, VII e §1º, "
                "prevê a publicação dos mínimos até 31/12 e atualizações a cada quatro meses; "
                "por isso há várias listas por ano. O SIOPE copia essas listas em blocos de "
                "dois bimestres. O 6º bimestre foi conferido contra a última lista de agosto "
                "de cada ano (2021 a 2025, portarias interministeriais): para os municípios "
                "que constam nela, os valores são iguais.\n\n"
                "**Limitações.** (1) Alguns municípios têm IEI no 6º bimestre sem constar "
                "na lista de agosto (2022: 2; 2023: 27; 2024: 9; 2025: 3). Em 39 desses 41 "
                "casos o valor é igual ao de outra lista oficial; em 2 casos de 2022 o valor "
                "não bate com nenhuma lista consultada. Nesses casos a pesquisa usa o valor "
                "do SIOPE, e a causa da diferença não foi verificada. (2) Municípios com IEI "
                "igual a zero ou ausente no SIOPE ficam como 'Sem mínimo definido'. "
                "(3) Nenhuma fonte consultada diz qual publicação do IEI vale para a "
                "fiscalização; usar outro bimestre pode mudar a classificação de alguns municípios."
            ),
        },
    },
    92: {
        "rotulo": "1.7",
        "nome": "Indicador de Educação Infantil (IEI)",
        "descricao": "Percentual mínimo da complementação-VAAT a ser aplicado em educação infantil (nome do indicador no SIOPE)",
        # É a meta do 1.6; não é classificado por si só.
        "metas": [],
    },
    95: {
        "rotulo": "1.9",
        "nome": "Fomento ao tempo integral (ETI)",
        "descricao": "% do FUNDEB vinculado ao fomento à educação em tempo integral",
        "metas": [
            # CF art. 212-A, XV (incluído pela EC 135/2024): a partir de 2026,
            # no mínimo 4% dos recursos dos fundos na criação de matrículas em
            # tempo integral. O SIOPE cita o mesmo inciso no nome do indicador.
            {"tipo": "minimo", "limite": 4.0, "de": 2026, "ate": None,
             "base_legal": "CF/1988, art. 212-A, XV (EC 135/2024)", "validada": True},
        ],
    },
}


def meta_vigente(codigo_indicador, ano):
    """Devolve a meta legal em vigor para o indicador naquele ano, ou None
    (indicador sem meta classificável, ou ano fora da vigência)."""
    indicador = INDICADORES.get(codigo_indicador)
    if indicador is None:
        return None
    for meta in indicador["metas"]:
        if meta["de"] <= ano and (meta["ate"] is None or ano <= meta["ate"]):
            return meta
    return None


def indicadores_classificaveis():
    """Códigos dos indicadores que têm pelo menos uma meta legal."""
    return [cod for cod, ind in INDICADORES.items() if ind["metas"]]


# ---------------------------------------------------------------------------
# Situações e cores
# ---------------------------------------------------------------------------
# Azul/vermelho em vez de verde/vermelho: o par verde/vermelho some para quem
# tem daltonismo (testado com o validador de paleta: ΔE 4,1 na deuteranopia).
# Azul, vermelho e âmbar passam juntos nos testes de daltonismo; o âmbar tem
# contraste baixo contra o fundo, por isso toda situação aparece também com
# rótulo (legenda, dica ao passar o mouse e tabela).

SITUACOES = {
    "Conforme":       {"cor": "#2a78d6", "rotulo": "✔ Conforme"},
    "Não conforme":   {"cor": "#e34948", "rotulo": "✖ Não conforme"},
    "Em andamento":   {"cor": "#eda100", "rotulo": "◔ Em andamento"},
    "Sem declaração": {"cor": "#c3c2b7", "rotulo": "– Sem declaração"},
    "Sem mínimo definido": {"cor": "#7b3294", "rotulo": "? Sem mínimo definido"},
    "Inconsistente":  {"cor": "#52514e", "rotulo": "! Inconsistente"},
}

ORDEM_SITUACOES = list(SITUACOES)
CORES_SITUACOES = {nome: dados["cor"] for nome, dados in SITUACOES.items()}
ROTULOS_SITUACOES = {nome: dados["rotulo"] for nome, dados in SITUACOES.items()}

COR_PRINCIPAL = "#2a78d6"   # séries de um município (uma só série)
COR_LIMITE = "#52514e"      # linha do limite legal