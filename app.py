"""
Conformidade com o FUNDEB — Bahia

Como rodar (na raiz do projeto, com o ambiente virtual ativo):
    streamlit run app.py

Este arquivo só monta a navegação; cada página mora em paginas/.
A versão anterior do app (Jussari) continua disponível em app_jussari.py.
"""

import streamlit as st

st.set_page_config(
    page_title="Conformidade com o FUNDEB — Bahia",
    page_icon="📊",
    layout="wide",
)

navegacao = st.navigation([
    st.Page("paginas/panorama.py", title="Panorama Bahia", icon="🗺️", default=True),
    st.Page("paginas/municipio.py", title="Município", icon="📍"),
    st.Page("paginas/qualidade.py", title="Qualidade dos dados", icon="🧪"),
])
navegacao.run()