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

# --- FUNÇÕES AUXILIARES (Mesma estrutura do seu processador) ---

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

def extrair_cno(texto):
    """Busca padrão de CNO no texto."""
    match = re.search(r'CNO\s*[:\.]?\s*(\d{2}\.\d{3}\.\d{5}/\d{2})', texto, re.IGNORECASE)
    if match:
        return match.group(1)
    # Tenta buscar CNO solto se estiver estruturado
    match_loose = re.search(r'(\d{2}\.\d{3}\.\d{5}/\d{2})', texto)
    return match_loose.group(1) if match_loose else None

# --- EXTRAÇÃO DO PER/DCOMP ---
def extrair_dados_perdcomp(pdf_file):
    dados = []
    with pdfplumber.open(pdf_file) as pdf:
        full_text = ""
        for page in pdf.pages:
            full_text += page.extract_text() + "\n"

    # Quebra o texto em blocos de "Débito" (Ex: 001. Débito CP Patronal)
    blocos = re.split(r'\d{3}\.\s*Débito', full_text)
    
    for bloco in blocos[1:]: # Pula o cabeçalho inicial antes do primeiro débito
        item = {}
        
        # Extração via Regex (ajustada para o formato do seu PDF com aspas/quebras)
        # Código
        m_cod = re.search(r'Código da Receita.*?(\d{4}(?:-\d{2})?)', bloco, re.DOTALL | re.IGNORECASE)
        item['Codigo'] = m_cod.group(1).split('-')[0] if m_cod else "N/A"
        
        # Período
        m_pa = re.search(r'Período de Apuração[^\n]*\n["\s]*([^"\n]+)', bloco, re.IGNORECASE)
        if not m_pa: # Tenta formato alternativo DCTFWeb
            m_pa = re.search(r'Período Apuração DCTFWeb[^\n]*\n["\s]*([^"\n]+)', bloco, re.IGNORECASE)
        item['PA'] = normalizar_periodo(m_pa.group(1)) if m_pa else "N/A"
        
        # CNO (Se houver)
        m_cno = re.search(r'CNO da Obra[^\n]*\n["\s]*([\d\./-]+)', bloco, re.IGNORECASE)
        item['CNO'] = m_cno.group(1).strip() if m_cno else "Geral"
        
        # Valores
        for campo in ['Principal', 'Multa', 'Juros', 'Total']:
            # Procura a label seguida de um valor numérico (lidando com aspas/quebras do PDF)
            regex_val = f'"{campo}[^"]*"\s*,\s*"([^"]+)"' # Padrão CSV-like visto no seu PDF
            m_val = re.search(regex_val, bloco, re.IGNORECASE)
            
            if not m_val: # Fallback para texto plano
                regex_val_alt = f'{campo}\s*[\n\r]+\s*([\d\.,]+)'
                m_val = re.search(regex_val_alt, bloco, re.IGNORECASE)
                
            item[campo] = limpar_valor(m_val.group(1)) if m_val else 0.0
            
        dados.append(item)
        
    return pd.DataFrame(dados)

# --- EXTRAÇÃO DA GUIA DARF ---
def extrair_dados_darf(pdf_file):
    dados = []
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            # Tenta extrair tabelas
            tabelas = page.extract_table()
            
            if tabelas:
                for row in tabelas:
                    # Limpa linhas vazias e None
                    row = [c if c else "" for c in row]
                    
                    # Verifica se a linha parece ter dados (Codigo, Denominação, Valores...)
                    # A estrutura da sua DARF agrupa linhas. Ex: Coluna 0 tem "1138\n1138", Coluna 1 tem as descrições
                    if len(row) >= 6:
                        codigos = row[0].split('\n')
                        descricoes = row[1].split('\n')
                        # As colunas de valor podem estar desalinhadas se houver células vazias no meio
                        # Ajuste baseado na sua DARF: Principal(2), Multa(3), Juros(4), Total(5)
                        principais = row[2].split('\n')
                        multas = row[3].split('\n')
                        juros = row[4].split('\n')
                        totais = row[5].split('\n')

                        # Tenta iterar pelo máximo de linhas encontradas na célula
                        max_lines = max(len(codigos), len(descricoes), len(principais))
                        
                        for i in range(max_lines):
                            try:
                                # Pega o valor ou string vazia se index out of range
                                txt_desc = descricoes[i] if i < len(descricoes) else ""
                                txt_princ = principais[i] if i < len(principais) else "0"
                                
                                # Pula linhas que são apenas cabeçalho ou vazias
                                if "CONTR PREVIDENCIÁRIA" in txt_desc and "PA" not in txt_desc:
                                    continue # Linha de título
                                if not txt_desc.strip():
                                    continue

                                item = {}
                                # Tenta pegar código da linha ou repete o anterior/primeiro
                                cod_cand = codigos[i] if i < len(codigos) and codigos[i].strip() else (codigos[0] if codigos else "")
                                item['Codigo'] = cod_cand.strip()
                                
                                # Extrai PA da descrição
                                m_pa = re.search(r'PA\s+(\d{2}/\d{4})', txt_desc)
                                item['PA'] = m_pa.group(1) if m_pa else "N/A"
                                
                                # Extrai CNO da descrição
                                m_cno = re.search(r'CNO\s+([\d\./-]+)', txt_desc)
                                item['CNO'] = m_cno.group(1).strip() if m_cno else "Geral"
                                
                                item['Principal'] = limpar_valor(txt_princ)
                                item['Multa'] = limpar_valor(multas[i]) if i < len(multas) else 0.0
                                item['Juros'] = limpar_valor(juros[i]) if i < len(juros) else 0.0
                                item['Total'] = limpar_valor(totais[i]) if i < len(totais) else 0.0
                                
                                # Só adiciona se tiver valor > 0 ou PA válido
                                if item['Total'] > 0 or item['PA'] != "N/A":
                                    dados.append(item)
                            except Exception as e:
                                continue # Ignora linhas problemáticas de parse

    # Consolida dados (agrupa por Codigo, PA, CNO para somar valores fragmentados se houver)
    if not dados:
        return pd.DataFrame()
        
    df = pd.DataFrame(dados)
    # Remove linhas vazias reais
    df = df[df['Total'] > 0]
    return df

# --- INTERFACE ---

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Upload do Comprovante (PER/DCOMP)")
    file_perdcomp = st.file_uploader("Arraste o PDF do PER/DCOMP", type=["pdf"], key="up_perdcomp")

with col2:
    st.subheader("2. Upload da Guia (DARF/DCTFWeb)")
    file_darf = st.file_uploader("Arraste o PDF da Guia", type=["pdf"], key="up_darf")

if st.button("🔍 Processar e Comparar Documentos"):
    if file_perdcomp and file_darf:
        try:
            with st.spinner("Lendo PER/DCOMP..."):
                df_perd = extrair_dados_perdcomp(file_perdcomp)
                
            with st.spinner("Lendo Guia DARF..."):
                df_darf = extrair_dados_darf(file_darf)

            if df_perd.empty or df_darf.empty:
                st.error("Não foi possível extrair dados de um dos arquivos. Verifique se são PDFs válidos de texto (não imagem).")
            else:
                # --- VISUALIZAÇÃO DOS DADOS BRUTOS ---
                with st.expander("Ver Dados Extraídos (Detalhes)"):
                    c1, c2 = st.columns(2)
                    c1.write("**PER/DCOMP (Extraído):**")
                    c1.dataframe(df_perd)
                    c2.write("**DARF (Extraído):**")
                    c2.dataframe(df_darf)

                # --- LÓGICA DE COMPARAÇÃO ---
                # Agrupa ambos para garantir unicidade na chave (Codigo, PA, CNO)
                chave = ['Codigo', 'PA', 'CNO']
                
                # Normaliza CNOs para comparação (remove pontuação)
                df_perd['CNO_Clean'] = df_perd['CNO'].apply(lambda x: re.sub(r'[^\d]', '', x) if x != "Geral" else "Geral")
                df_darf['CNO_Clean'] = df_darf['CNO'].apply(lambda x: re.sub(r'[^\d]', '', x) if x != "Geral" else "Geral")
                
                chave_clean = ['Codigo', 'PA', 'CNO_Clean']
                
                df_perd_grp = df_perd.groupby(chave_clean)[['Principal', 'Multa', 'Juros', 'Total']].sum().reset_index()
                df_darf_grp = df_darf.groupby(chave_clean)[['Principal', 'Multa', 'Juros', 'Total']].sum().reset_index()

                # Merge (Outer Join para pegar sobras de ambos os lados)
                df_merge = pd.merge(
                    df_perd_grp, 
                    df_darf_grp, 
                    on=chave_clean, 
                    how='outer', 
                    suffixes=('_PERD', '_GUIA')
                )
                
                # Preenche NaN com 0
                df_merge = df_merge.fillna(0)

                # Calcula Diferenças
                df_merge['Dif_Principal'] = df_merge['Principal_PERD'] - df_merge['Principal_GUIA']
                df_merge['Dif_Total'] = df_merge['Total_PERD'] - df_merge['Total_GUIA']
                
                # Flag de Status
                def get_status(row):
                    tol = 0.05 # Tolerância de 5 centavos
                    if abs(row['Dif_Total']) < tol:
                        return "✅ OK"
                    elif row['Total_PERD'] > 0 and row['Total_GUIA'] == 0:
                        return "⚠️ Só no PERDCOMP"
                    elif row['Total_PERD'] == 0 and row['Total_GUIA'] > 0:
                        return "⚠️ Só na Guia"
                    else:
                        return "❌ Divergente"

                df_merge['Status'] = df_merge.apply(get_status, axis=1)

                # --- EXIBIÇÃO ---
                st.markdown("---")
                st.subheader("📊 Resultado da Comparação")
                
                # Filtros de visualização
                filtro = st.radio("Mostrar:", ["Tudo", "Apenas Divergências"], horizontal=True)
                
                df_final = df_merge.copy()
                if filtro == "Apenas Divergências":
                    df_final = df_final[df_final['Status'] != "✅ OK"]

                # Formatação visual
                st.dataframe(
                    df_final.style.format({
                        'Principal_PERD': 'R$ {:,.2f}', 'Principal_GUIA': 'R$ {:,.2f}',
                        'Total_PERD': 'R$ {:,.2f}', 'Total_GUIA': 'R$ {:,.2f}',
                        'Dif_Total': 'R$ {:,.2f}'
                    }).applymap(
                        lambda x: 'background-color: #ffcccc' if x == "❌ Divergente" else \
                                  ('background-color: #ccffcc' if x == "✅ OK" else 'background-color: #ffffcc'),
                        subset=['Status']
                    )
                )
                
                if not df_final.empty:
                    # Totais Gerais
                    st.metric(
                        "Diferença Total (PERDCOMP - Guia)", 
                        f"R$ {df_final['Dif_Total'].sum():,.2f}"
                    )

    else:
        st.info("Por favor, faça o upload de ambos os arquivos para iniciar.")
