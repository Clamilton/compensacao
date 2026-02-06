import streamlit as st
import pdfplumber
import pandas as pd
import re
import io
import time

st.title("📂 Processador de PER/DCOMP")

# Sidebar local para esta página
cnpj_alvo_input = st.sidebar.text_input("CNPJ da Empresa (Obrigatório):", placeholder="Ex: 17.774.985/0001-05")

DE_PARA_IMPOSTOS = {
    "0561": "IRRF", "0588": "IRRF", "1138": "CP PATRONAL",
    "1099": "CP SEGURADOS", "1082": "CP TERCEIROS", "2089": "IRPJ",
    "2372": "CSLL", "8109": "PIS", "2172": "COFINS",
    "6912": "PIS", "5952": "PIS/COFINS/CSLL"
}

def limpar_cnpj(cnpj): return re.sub(r'[^\d]', '', str(cnpj)) if cnpj else "" [cite: 17]

def limpar_valor(valor_str):
    if not valor_str: return 0.0
    limpo = re.sub(r'[^\d,\.]', '', str(valor_str))
    if ',' in limpo and '.' in limpo: [cite: 18]
        if limpo.find(',') > limpo.find('.'): limpo = limpo.replace('.', '').replace(',', '.')
        else: limpo = limpo.replace(',', '')
    elif ',' in limpo: limpo = limpo.replace(',', '.')
    try: return float(limpo)
    except: return 0.0

def padronizar_nome_imposto(codigo, descricao):
    if codigo and len(codigo) >= 4:
        raiz = codigo[:4]
        if raiz in DE_PARA_IMPOSTOS: return DE_PARA_IMPOSTOS[raiz]
    d = str(descricao).upper()
    if "PATRONAL" in d: return "CP PATRONAL" [cite: 19]
    return str(descricao).strip().replace('"', '')

def extrair_cabecalho(texto_p1):
    cnpj = re.search(r'CNPJ\s*[:\.]?\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})', texto_p1)
    nome = re.search(r'Nome Empresarial(?:[^0-9A-Za-z]*)([^"\n]+)', texto_p1, re.IGNORECASE)
    return (cnpj.group(1) if cnpj else None), (nome.group(1).strip() if nome else "Desconhecida")

def extrair_dados_pdf(arquivo, cnpj_alvo):
    with pdfplumber.open(arquivo) as pdf:
        if not pdf.pages: return [], None, "PDF Vazio" [cite: 20]
        p1 = pdf.pages[0].extract_text() or ""
        cnpj_pdf, nome_empresa = extrair_cabecalho(p1)
        if limpar_cnpj(cnpj_pdf) != cnpj_alvo: return [], None, f"CNPJ Divergente"
        texto = "\n".join([p.extract_text() or "" for p in pdf.pages]) [cite: 21]

    num_perd = re.search(r'(\d{5}\.\d{5}\.\d{6}\.\d\.\d\.\d{2}-\d{4})', texto)
    num_perd = num_perd.group(1) if num_perd else "N/A"
    blocos = re.split(r'\d{3}\.\s*Débito', texto)[1:] or [texto]
    
    linhas = []
    for bloco in blocos:
        def get(k, t='tx'):
            r = r'([\d\.,]+)' if t=='vl' else r'([^"\n]+)'
            m = re.search(f'{k}(?:[^0-9A-Za-z]*){r}', bloco, re.IGNORECASE | re.DOTALL) [cite: 23]
            return m.group(1).strip() if m else None

        match_cod = re.search(r'Código da Receita/Denominação(?:[^0-9]*)(\d{4}-\d{2})', bloco, re.IGNORECASE | re.DOTALL)
        cod = match_cod.group(1) if match_cod else "N/D" [cite: 24]
        
        tot = limpar_valor(get('Total','vl'))
        periodicidade = get('Periodicidade') or ""
        pa_bruto = get('Período de Apuração') or ""
        pa_final = (re.search(r'\d{4}', pa_bruto).group(0) if "ANUAL" in periodicidade.upper() else pa_bruto) [cite: 27]

        linhas.append({
            "PA": pa_final,
            "IMPOSTO": padronizar_nome_imposto(cod, get('Grupo de Tributo')), [cite: 28]
            "CÓDIGO": cod,
            "TOTAL": tot,
            "PERDCOMP VINCULADA": num_perd [cite: 29]
        })
    return linhas, nome_empresa, "OK"

# Interface
uploaded_files = st.file_uploader("Arraste os PDFs aqui", type="pdf", accept_multiple_files=True)
if uploaded_files and st.button("⚙️ Processar Arquivos"):
    if not cnpj_alvo_input:
        st.warning("⚠️ Digite o CNPJ.") [cite: 30]
        st.stop()
    
    validas = []
    for f in uploaded_files:
        d, n, s = extrair_dados_pdf(f, limpar_cnpj(cnpj_alvo_input))
        if s == "OK": validas.extend(d) [cite: 31]
    
    if validas:
        df = pd.DataFrame(validas)
        st.dataframe(df.head()) [cite: 32]
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='COMPENSAÇÕES')
        st.download_button("📥 Baixar Excel", buffer.getvalue(), f"Perdcomp_{int(time.time())}.xlsx") [cite: 33]