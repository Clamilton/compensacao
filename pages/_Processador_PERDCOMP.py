import streamlit as st
import pdfplumber
import pandas as pd
import re
import io
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.title("📂 Processador de PER/DCOMP (Excel Local)")
st.markdown("Ferramenta ajustada: Validação de PA baseada na **Periodicidade**.")

# --- BARRA LATERAL ---
st.sidebar.header("Validação")
cnpj_alvo_input = st.sidebar.text_input("CNPJ da Empresa (Obrigatório):", placeholder="Ex: 17.774.985/0001-05")

# --- LISTA DE TRADUÇÃO ---
DE_PARA_IMPOSTOS = {
    "0561": "IRRF", "0588": "IRRF", "1138": "CP PATRONAL",
    "1099": "CP SEGURADOS", "1082": "CP TERCEIROS", "2089": "IRPJ",
    "2372": "CSLL", "8109": "PIS", "2172": "COFINS",
    "6912": "PIS", "5952": "PIS/COFINS/CSLL"
}

# --- FUNÇÕES ---

def limpar_cnpj(cnpj): 
    return re.sub(r'[^\d]', '', str(cnpj)) if cnpj else ""

def limpar_valor(valor_str):
    if not valor_str: return 0.0
    limpo = re.sub(r'[^\d,\.]', '', str(valor_str))
    
    # Lógica para tratar 1.000,00 vs 1,000.00
    if ',' in limpo and '.' in limpo:
        if limpo.find(',') > limpo.find('.'): 
            # Formato Brasileiro (1.500,00) -> Remove ponto, troca vírgula por ponto
            limpo = limpo.replace('.', '').replace(',', '.')
        else: 
            # Formato Americano (1,500.00) -> Remove vírgula
            limpo = limpo.replace(',', '')
    elif ',' in limpo: 
        # Apenas vírgula (150,00) -> Troca por ponto
        limpo = limpo.replace(',', '.')
        
    try: 
        return float(limpo)
    except: 
        return 0.0

def padronizar_nome_imposto(codigo, descricao):
    if codigo and len(codigo) >= 4:
        raiz = codigo[:4]
        if raiz in DE_PARA_IMPOSTOS: return DE_PARA_IMPOSTOS[raiz]
    d = str(descricao).upper()
    if "PATRONAL" in d: return "CP PATRONAL"
    if "SEGURADOS" in d: return "CP SEGURADOS"
    if "IRRF" in d: return "IRRF"
    if "PIS" in d: return "PIS"
    if "COFINS" in d: return "COFINS"
    return str(descricao).strip().replace('"', '')

def extrair_cabecalho(texto_p1):
    cnpj = re.search(r'CNPJ\s*[:\.]?\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})', texto_p1)
    nome = re.search(r'Nome Empresarial(?:[^0-9A-Za-z]*)([^"\n]+)', texto_p1, re.IGNORECASE)
    return (cnpj.group(1) if cnpj else None), (nome.group(1).strip() if nome else "Desconhecida")

def extrair_dados_pdf(arquivo, cnpj_alvo):
    with pdfplumber.open(arquivo) as pdf:
        if not pdf.pages: return [], None, "PDF Vazio"
        p1 = pdf.pages[0].extract_text(layout=False) or ""
        cnpj_pdf, nome_empresa = extrair_cabecalho(p1)
        
        if not cnpj_pdf: return [], None, "CNPJ não encontrado"
        if limpar_cnpj(cnpj_pdf) != cnpj_alvo: return [], None, f"CNPJ Divergente: {cnpj_pdf}"
        
        texto = ""
        for p in pdf.pages: 
            p_text = p.extract_text(layout=False)
            if p_text:
                texto += p_text + "\n"
         
    num_perd = re.search(r'(\d{5}\.\d{5}\.\d{6}\.\d\.\d\.\d{2}-\d{4})', texto)
    num_perd = num_perd.group(1) if num_perd else "N/A"
    
    # Divide por blocos de débito
    blocos = re.split(r'\d{3}\.\s*Débito', texto)[1:] or [texto]
    
    linhas = []
    for bloco in blocos:
        # Função auxiliar de regex
        def get(k, t='tx'):
            # t='tx' (padrão) pega o texto inteiro até a próxima aspa/enter
            # t='vl' pega apenas números e vírgulas (valores)
            r = r'([\d\.,]+)' if t=='vl' else r'([^"\n]+)'
            
            # Regex: Chave + (lixo não alfanumérico) + Valor
            # Ajuste de robustez no regex
            m = re.search(f'{k}(?:[^0-9A-Za-z]*){r}', bloco, re.IGNORECASE | re.DOTALL)
            return m.group(1).strip() if m else None

        # 1. Busca Código da Receita
        match_cod = re.search(r'Código da Receita/Denominação(?:[^0-9]*)(\d{4}-\d{2})', bloco, re.IGNORECASE | re.DOTALL)
        if match_cod:
            cod = match_cod.group(1)
        else:
            match_fallback = re.search(r'(\d{4}-\d{2})', bloco)
            cod = match_fallback.group(1) if match_fallback else "N/D"
        
        # Filtro de segurança (Lixo de rodapé)
        if cod == "N/D" and not get('Total','vl'): continue
        
        # 2. Tratamento de Valores
        tot = limpar_valor(get('Total','vl'))
        if tot == 0: 
            tot = limpar_valor(get('Principal','vl')) + limpar_valor(get('Multa','vl')) + limpar_valor(get('Juros','vl'))
            
        desc_bruta = get('Grupo de Tributo') or ""
        
        # --- LÓGICA: PERIODICIDADE ---
        # 1. Extrai a Periodicidade (Mensal, Trimestral, Anual)
        periodicidade = get('Periodicidade') or ""
        
        # 2. Extrai o PA bruto (Texto completo)
        pa_bruto = get('Período de Apuração') or ""
        
        # 3. Aplica a Regra
        if "ANUAL" in periodicidade.upper():
            # Se for ANUAL: Pega apenas os 4 dígitos do ano (ex: "2024" de "Ano 2024")
            match_ano = re.search(r'\d{4}', pa_bruto)
            pa_final = match_ano.group(0) if match_ano else pa_bruto
        else:
            # Se for MENSAL ou TRIMESTRAL: Mantém o texto original (ex: "Janeiro de 2026")
            pa_final = pa_bruto

        linhas.append({
            "PA": pa_final,
            "VENCIMENTO": get('Data de Vencimento do Tributo/Quota'), 
            "IMPOSTO": padronizar_nome_imposto(cod, desc_bruta),
            "CÓDIGO": cod,
            "VALOR PRINCIPAL": limpar_valor(get('Principal','vl')),
            "MULTA": limpar_valor(get('Multa','vl')),
            "JUROS": limpar_valor(get('Juros','vl')),
            "TOTAL": tot,
            "VALOR COMPENSADO": tot,
            "SALDO DÉBITO": 0.0,
            "PERDCOMP VINCULADA": num_perd,
            "PROCESSO FISCAL": ""
        })
        
    return linhas, nome_empresa, "OK"

# --- INTERFACE ---
uploaded_files = st.file_uploader("Arraste os PDFs aqui", type="pdf", accept_multiple_files=True)

if uploaded_files and st.button("⚙️ Processar Arquivos"):
    if not cnpj_alvo_input:
        st.warning("⚠️ Digite o CNPJ.")
        st.stop()
        
    cnpj_limpo = limpar_cnpj(cnpj_alvo_input)
    validas, erros, nome_final = [], [], "Empresa"
    bar = st.progress(0)
    
    for i, f in enumerate(uploaded_files):
        d, n, s = extrair_dados_pdf(f, cnpj_limpo)
        if s == "OK": 
            validas.extend(d)
            nome_final = n
        else: 
            erros.append(f"{f.name}: {s}")
        bar.progress((i+1)/len(uploaded_files))
        
    if erros:
        with st.expander("Erros"): 
            for e in erros: st.write(e)
            
    if validas:
        df = pd.DataFrame(validas)
        st.success(f"✅ {len(validas)} registros encontrados!")
        st.dataframe(df.head())
        
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='COMPENSAÇÕES')
            # Ajuste de largura das colunas
            worksheet = writer.sheets['COMPENSAÇÕES']
            for idx, col in enumerate(df.columns):
                worksheet.set_column(idx, idx, 18)
                
        st.download_button("📥 Baixar Excel", buffer.getvalue(), f"Perdcomp_{int(time.time())}.xlsx")
    else:
        st.error("Nenhum dado encontrado.")
