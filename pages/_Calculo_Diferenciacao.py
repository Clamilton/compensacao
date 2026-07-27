import math
import streamlit as st
import pandas as pd

# Configuração da Página
st.set_page_config(page_title="Calc Tributária", layout="centered")

# --- Inicialização da Memória (Session State) ---
if 'fator_inversao' not in st.session_state:
    st.session_state.fator_inversao = 1

if 'valor_digitado' not in st.session_state:
    st.session_state.valor_digitado = "0,00"

# --- Constantes Tributárias ---
TAXA_PIS = 1.65
TAXA_COFINS = 7.60
TAXA_TOTAL = TAXA_PIS + TAXA_COFINS
FATOR_PIS = TAXA_PIS / TAXA_TOTAL

# --- Funções Auxiliares ---
def formatar_brl(valor):
    """Transforma float 1500.50 em string '1.500,50'"""
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def converter_input_br(valor_texto):
    """Limpa string '1.500,50' para float 1500.50"""
    if not valor_texto: return 0.0
    try:
        limpo = valor_texto.replace(".", "").replace(",", ".")
        return float(limpo)
    except ValueError:
        return 0.0

# --- CALLBACK: Auto-formatação ---
def atualizar_input():
    texto_atual = st.session_state.valor_digitado
    valor_float = converter_input_br(texto_atual)
    st.session_state.valor_digitado = formatar_brl(valor_float)

def montar_linha_mes(label, total_mes):
    v_pis = round(total_mes * FATOR_PIS, 2)
    v_cofins = round(total_mes - v_pis, 2)
    v_base_calculo = round(v_pis * 100 / TAXA_PIS, 2)

    return {
        "Mês": label,
        "Valor PIS (1,65%)": formatar_brl(v_pis),
        "Valor COFINS (7,60%)": formatar_brl(v_cofins),
        "Total do Mês": formatar_brl(total_mes),
        "Base de Cálculo": formatar_brl(v_base_calculo),
        "_total_raw": total_mes,
        "_pis_raw": v_pis,
        "_cofins_raw": v_cofins,
        "_base_calculo_raw": v_base_calculo
    }

def calcular_distribuicao_completa(valor_total, variacao_pct, inverter_logica, qtd_meses):
    # Define divisor base (2 ou 3)
    divisor = 3 if qtd_meses == "3 Meses (Trimestre)" else 2

    # 1. Base (Média)
    base_media = round(valor_total / divisor, 2)
    valor_variacao = round(base_media * (variacao_pct / 100), 2)

    totais_mensais = []
    meses_label = []

    # --- LÓGICA PARA 3 MESES ---
    if divisor == 3:
        total_m1 = base_media # Mês 1: Média Pura

        if not inverter_logica:
            total_m2 = round(base_media - valor_variacao, 2)
            tipo_distribuicao = "📉 Padrão: Mês 2 Baixo / Mês 3 Alto"
        else:
            total_m2 = round(base_media + valor_variacao, 2)
            tipo_distribuicao = "📈 Invertido: Mês 2 Alto / Mês 3 Baixo"

        total_m3 = round(valor_total - (total_m1 + total_m2), 2)

        totais_mensais = [total_m1, total_m2, total_m3]
        meses_label = ["Mês 1 (Média)", "Mês 2 (Variação)", "Mês 3 (Ajuste Final)"]

    # --- LÓGICA PARA 2 MESES ---
    else:
        if not inverter_logica:
            total_m1 = round(base_media - valor_variacao, 2)
            tipo_distribuicao = "📉 Padrão: Mês 1 Baixo / Mês 2 Alto"
        else:
            total_m1 = round(base_media + valor_variacao, 2)
            tipo_distribuicao = "📈 Invertido: Mês 1 Alto / Mês 2 Baixo"

        total_m2 = round(valor_total - total_m1, 2)

        totais_mensais = [total_m1, total_m2]
        meses_label = ["Mês 1 (Variação)", "Mês 2 (Ajuste Final)"]

    # Gera saída final (PIS/COFINS/Base de Cálculo)
    dados_finais = [montar_linha_mes(meses_label[i], total_mes) for i, total_mes in enumerate(totais_mensais)]

    return dados_finais, tipo_distribuicao, base_media

def calcular_multiplos_meses(valor_total, variacao_pct, qtd_meses_total, teto_trimestre, fator_inversao_inicial):
    """
    Divide valor_total em N meses agrupados em trimestres (grupos de até 3 meses),
    aplicando a lógica de alternância (2/3 meses) dentro de cada trimestre e
    bloqueando o cálculo se algum trimestre estourar o teto.
    """
    # 1. Monta os grupos (trimestres) — último grupo pode sobrar com 1 ou 2 meses
    grupos = []
    restante = qtd_meses_total
    while restante > 0:
        tamanho = 3 if restante >= 3 else restante
        grupos.append(tamanho)
        restante -= tamanho

    # 2. Distribui valor_total entre os grupos, proporcional à qtd de meses de cada um,
    #    com o último grupo absorvendo o resto do arredondamento (fecha exato no centavo)
    totais_grupos = []
    acumulado = 0.0
    for i, tamanho in enumerate(grupos):
        if i < len(grupos) - 1:
            parte = round(valor_total * (tamanho / qtd_meses_total), 2)
            totais_grupos.append(parte)
            acumulado += parte
        else:
            totais_grupos.append(round(valor_total - acumulado, 2))

    # 3. Checa teto por trimestre — bloqueia se estourar
    estouros = [(i + 1, total) for i, total in enumerate(totais_grupos) if total > teto_trimestre]
    if estouros:
        qtd_trimestres_necessarios = math.ceil(valor_total / teto_trimestre)
        qtd_meses_sugerido = qtd_trimestres_necessarios * 3
        return {
            "ok": False,
            "estouros": estouros,
            "qtd_meses_sugerido": qtd_meses_sugerido
        }

    # 4. Gera a distribuição interna de cada trimestre reaproveitando a lógica atual
    fator_inversao = fator_inversao_inicial
    dados_finais = []

    for idx, (tamanho, total_grupo) in enumerate(zip(grupos, totais_grupos)):
        prefixo = f"Trimestre {idx + 1}"

        if tamanho == 1:
            dados_finais.append(montar_linha_mes(f"{prefixo} (Mês Único)", total_grupo))
            continue

        qtd_meses_label = "3 Meses (Trimestre)" if tamanho == 3 else "2 Meses (Bimestre)"
        usar_inversao = (fator_inversao == -1)

        dados_grupo, _, _ = calcular_distribuicao_completa(total_grupo, variacao_pct, usar_inversao, qtd_meses_label)
        fator_inversao *= -1

        for d in dados_grupo:
            d["Mês"] = f"{prefixo} - {d['Mês']}"

        dados_finais.extend(dados_grupo)

    return {
        "ok": True,
        "dados": dados_finais,
        "grupos": grupos,
        "totais_grupos": totais_grupos
    }

# --- Interface ---
st.title("📊 Distribuidor de Crédito")
st.markdown("Cálculo com alternância de padrão para evitar malha fina.")

with st.container(border=True):
    col1, col2 = st.columns(2)
    with col1:
        st.text_input(
            "Valor Total do Crédito (R$)",
            key="valor_digitado",
            on_change=atualizar_input,
            help="Digite o valor e aperte Enter. Ex: 1000 vira 1.000,00"
        )
        valor_input = converter_input_br(st.session_state.valor_digitado)

    with col2:
        pct_input = st.number_input("Variação (%)", value=12.3, step=0.1, format="%.2f")

    periodo_opcao = st.radio(
        "Período de Compensação:",
        ["3 Meses (Trimestre)", "2 Meses (Bimestre)", "Múltiplos Meses / SPEDs (Trimestral)"],
        horizontal=True
    )

    modo_multiplos = periodo_opcao == "Múltiplos Meses / SPEDs (Trimestral)"

    if modo_multiplos:
        col3, col4 = st.columns(2)
        with col3:
            qtd_meses_input = st.number_input(
                "Quantidade de Meses / SPEDs",
                min_value=1, value=9, step=1,
                help="Total de meses a distribuir. Serão agrupados em trimestres (grupos de 3)."
            )
        with col4:
            teto_trimestre_input = st.number_input(
                "Teto por Trimestre (R$)",
                min_value=0.01, value=1500000.00, step=50000.0, format="%.2f",
                help="Valor máximo permitido somando os meses de cada trimestre."
            )

# Botão de Ação
if st.button("Calcular Distribuição (Alternar Padrão)", type="primary"):

    if valor_input == 0:
        st.warning("Por favor, digite um valor maior que zero.")

    elif modo_multiplos:
        st.session_state.fator_inversao *= -1

        resultado = calcular_multiplos_meses(
            valor_input, pct_input, int(qtd_meses_input),
            teto_trimestre_input, st.session_state.fator_inversao
        )

        if not resultado["ok"]:
            st.error("🚫 Cálculo bloqueado: um ou mais trimestres estouraram o teto.")
            for num_trimestre, total in resultado["estouros"]:
                st.write(f"- Trimestre {num_trimestre}: R$ {formatar_brl(total)} (acima do teto de R$ {formatar_brl(teto_trimestre_input)})")
            st.info(f"Aumente para pelo menos **{resultado['qtd_meses_sugerido']} meses** para respeitar esse teto.")

        else:
            dados = resultado["dados"]
            df_visual = pd.DataFrame(dados)[["Mês", "Valor PIS (1,65%)", "Valor COFINS (7,60%)", "Total do Mês", "Base de Cálculo"]]

            st.success(f"✅ Distribuído em {len(dados)} meses / {len(resultado['grupos'])} trimestre(s), todos dentro do teto.")

            st.subheader("Resumo por Trimestre")
            for idx, (tamanho, total_grupo) in enumerate(zip(resultado["grupos"], resultado["totais_grupos"])):
                pct_teto = (total_grupo / teto_trimestre_input) * 100
                st.caption(f"Trimestre {idx + 1} ({tamanho} mês(es)): R$ {formatar_brl(total_grupo)} — {pct_teto:.1f}% do teto")

            st.subheader("Resultado (Copie e Cole)")
            st.dataframe(df_visual, use_container_width=True, hide_index=True)

            # Prova Real
            total_geral = sum(d['_total_raw'] for d in dados)
            dif = total_geral - valor_input

            st.markdown("---")
            if abs(dif) < 0.01:
                st.caption(f"Validação Matemática: R$ {formatar_brl(total_geral)} (Perfeito)")
            else:
                st.error(f"Erro de arredondamento: {dif}")

    else:
        st.session_state.fator_inversao *= -1
        usar_inversao = (st.session_state.fator_inversao == -1)

        dados, status_msg, base_media = calcular_distribuicao_completa(valor_input, pct_input, usar_inversao, periodo_opcao)

        df_visual = pd.DataFrame(dados)[["Mês", "Valor PIS (1,65%)", "Valor COFINS (7,60%)", "Total do Mês", "Base de Cálculo"]]

        if usar_inversao:
            st.info(status_msg, icon="🔄")
        else:
            st.success(status_msg, icon="✅")

        # Base de cálculo visível
        st.metric(label="Base de Cálculo (Média por Mês)", value=f"R$ {formatar_brl(base_media)}")

        st.subheader("Resultado (Copie e Cole)")
        st.dataframe(df_visual, use_container_width=True, hide_index=True)

        # Prova Real
        total_geral = sum(d['_total_raw'] for d in dados)
        dif = total_geral - valor_input

        st.markdown("---")
        if abs(dif) < 0.01:
            st.caption(f"Validação Matemática: R$ {formatar_brl(total_geral)} (Perfeito)")
        else:
            st.error(f"Erro de arredondamento: {dif}")
