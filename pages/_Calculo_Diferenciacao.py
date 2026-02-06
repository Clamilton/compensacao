import streamlit as st
import pandas as pd

# --- Inicialização da Memória (Session State) ---
if 'fator_inversao' not in st.session_state:
    st.session_state.fator_inversao = 1
if 'valor_digitado' not in st.session_state:
    st.session_state.valor_digitado = "0,00"

# Funções Auxiliares
def formatar_brl(valor):
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def converter_input_br(valor_texto):
    if not valor_texto: return 0.0
    try:
        limpo = valor_texto.replace(".", "").replace(",", ".")
        return float(limpo) [cite: 2]
    except ValueError:
        return 0.0

def atualizar_input():
    texto_atual = st.session_state.valor_digitado
    valor_float = converter_input_br(texto_atual)
    st.session_state.valor_digitado = formatar_brl(valor_float)

def calcular_distribuicao_completa(valor_total, variacao_pct, inverter_logica, qtd_meses):
    taxa_pis, taxa_cofins = 1.65, 7.60
    taxa_total = taxa_pis + taxa_cofins
    fator_pis = taxa_pis / taxa_total
    divisor = 3 if qtd_meses == "3 Meses (Trimestre)" else 2 [cite: 3]
    
    base_media = round(valor_total / divisor, 2)
    valor_variacao = round(base_media * (variacao_pct / 100), 2)
    
    if divisor == 3:
        total_m1 = base_media
        if not inverter_logica:
            total_m2 = round(base_media - valor_variacao, 2)
            tipo_distribuicao = "📉 Padrão: Mês 2 Baixo / Mês 3 Alto" [cite: 4]
        else:
            total_m2 = round(base_media + valor_variacao, 2)
            tipo_distribuicao = "📈 Invertido: Mês 2 Alto / Mês 3 Baixo" [cite: 4]
        total_m3 = round(valor_total - (total_m1 + total_m2), 2) [cite: 5]
        totais_mensais = [total_m1, total_m2, total_m3]
        meses_label = ["Mês 1 (Média)", "Mês 2 (Variação)", "Mês 3 (Ajuste Final)"]
    else:
        if not inverter_logica:
            total_m1 = round(base_media - valor_variacao, 2)
            tipo_distribuicao = "📉 Padrão: Mês 1 Baixo / Mês 2 Alto" [cite: 6]
        else:
            total_m1 = round(base_media + valor_variacao, 2)
            tipo_distribuicao = "📈 Invertido: Mês 1 Alto / Mês 2 Baixo" [cite: 7]
        total_m2 = round(valor_total - total_m1, 2)
        totais_mensais = [total_m1, total_m2]
        meses_label = ["Mês 1 (Variação)", "Mês 2 (Ajuste Final)"]

    dados_finais = []
    for i, total_mes in enumerate(totais_mensais):
        v_pis = round(total_mes * fator_pis, 2)
        v_cofins = round(total_mes - v_pis, 2)
        dados_finais.append({
            "Mês": meses_label[i],
            "Valor PIS (1,65%)": formatar_brl(v_pis),
            "Valor COFINS (7,60%)": formatar_brl(v_cofins),
            "Total do Mês": formatar_brl(total_mes), [cite: 9]
            "_total_raw": total_mes
        })
    return dados_finais, tipo_distribuicao

# Interface
st.title("📊 Distribuidor de Crédito")
with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Valor Total do Crédito (R$)", key="valor_digitado", on_change=atualizar_input) [cite: 10]
        valor_input = converter_input_br(st.session_state.valor_digitado)
    with col2:
        pct_input = st.number_input("Variação (%)", value=12.3, step=0.1, format="%.2f")
    periodo_opcao = st.radio("Período de Compensação:", ["3 Meses (Trimestre)", "2 Meses (Bimestre)"], horizontal=True)

if st.button("Calcular Distribuição", type="primary"): [cite: 12]
    if valor_input > 0:
        st.session_state.fator_inversao *= -1
        usar_inversao = (st.session_state.fator_inversao == -1)
        dados, status_msg = calcular_distribuicao_completa(valor_input, pct_input, usar_inversao, periodo_opcao)
        df_visual = pd.DataFrame(dados)[["Mês", "Valor PIS (1,65%)", "Valor COFINS (7,60%)", "Total do Mês"]]
        st.info(status_msg) if usar_inversao else st.success(status_msg)
        st.dataframe(df_visual, use_container_width=True, hide_index=True) [cite: 14]
    else:
        st.warning("Digite um valor maior que zero.")