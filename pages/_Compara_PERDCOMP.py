import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Comparador de Guias vs PER/DCOMP", layout="wide")
st.title("⚖️ Comparador: PER/DCOMP vs DARF (Guias)")
st.markdown("""
Esta ferramenta cruza os dados extraídos do **Comprovante PER/DCOMP** com a **Guia DARF/DCTFWeb**.
O objetivo é validar se os débitos compensados conferem com a guia, identificando retificações ou divergências de valores.
""")

# --- FUNÇÕES AUXILIARES ---

def limpar_valor(valor_str):
    """Converte string de valor (ex: '1.234,56') para float."""
    if not valor_str: return 0.0
    # Remove tudo que não for dígito ou vírgula
    limpo = re.sub(r'[^\d,]', '', str(valor_str))
    # Troca vírgula por ponto
    limpo = limpo.replace(',', '.')
    try:
        return float(limpo)
    except ValueError:
        return 0.0

def normalizar_periodo(texto):
    """
    Normaliza períodos para o formato MM/AAAA.
    Converte 'Junho de 2025' -> '06/2025'.
    """
    if not texto: return ""
    texto = texto.lower().strip()
    
    meses = {
        'janeiro': '01', 'fevereiro': '02', 'março': '03', 'abril': '04',
        'maio': '05', 'junho': '06', 'julho': '07', 'agosto': '08',
        'setembro': '09', 'outubro': '10', 'novembro': '11', 'dezembro': '12'
    }
    
    # Tenta padrão 'junho de 2025'
    for mes_nome, mes_num in meses.items():
        if mes_nome in texto:
            ano = re.search(r'\d{4}', texto)
            if ano:
                return f"{mes_num}/{ano.group(0)}"
    
    # Tenta padrão '06/2025' ou '062025'
    match_num = re.search(r'(\d{2})/?(\d{4})', texto)
    if match_num:
        return f"{match_num.group(1)}/{match_num.group(2)}"
            
    return texto

# --- EXTRAÇÃO DO PER/DCOMP ---
def extrair_dados_perdcomp(pdf_file):
    dados = []
    try:
        with pdfplumber.open(pdf_file) as pdf:
            full_text = ""
            for page in pdf.pages:
                txt = page.extract_text()
                if txt:
                    full_text += txt + "\n"
    except Exception as e:
        st.error(f"Erro ao ler PDF PER/DCOMP: {e}")
        return pd.DataFrame()

    # Quebra o texto em blocos de "Débito" (Ex: 001. Débito CP Patronal)
    blocos = re.split(r'\d{3}\.\s*Débito', full_text)
    
    for bloco in blocos[1:]: # Pula o cabeçalho inicial antes do primeiro débito
        item = {}
        
        # Código da Receita
        m_cod = re.search(r'Código da Receita.*?(\d{4}(?:-\d{
