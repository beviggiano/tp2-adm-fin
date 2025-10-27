import streamlit as st
import pandas as pd
from io import BytesIO

# --- IMPORTAÇÃO MODULARIZADA (Melhoria 3b) ---
from finance_logic import (
    calcular_cronograma_price,
    calcular_cronograma_sac,
    calcular_simulacao_extra,
    calcular_investimento,
    convert_to_excel
)

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Simulador Financeiro Avançado",
    page_icon="🏦",
    layout="wide"
)

# --- FUNÇÕES AUXILIARES (Frontend) ---
def formatar_moeda(valor):
    """Formata um número float como moeda BRL."""
    return f"R$ {valor:,.2f}"

def calcular_custo_total(df):
    """Calcula o custo total (Juros + Seguro + Taxa Adm) de um cronograma."""
    if df.empty:
        return 0
    return df['Juros'].sum() + df['Seguro'].sum() + df['Taxa Adm'].sum()

# --- INTERFACE DO USUÁRIO (STREAMLIT) ---

st.title("🏦 Simulador Financeiro Avançado (CET e Investimentos)")

# --- BARRA LATERAL (Inputs) ---
st.sidebar.header("Parâmetros do Financiamento")

principal = st.sidebar.number_input(
    "Valor do Financiamento (R$)", 
    min_value=1000.0, value=100000.0, step=1000.0, format="%.2f"
)

taxa_anual_perc = st.sidebar.slider(
    "Taxa de Juros Anual (%)", 
    min_value=0.0, max_value=30.0, value=10.0, step=0.1
)

prazo_meses = st.sidebar.slider(
    "Prazo (em Meses)", 
    min_value=12, max_value=480, value=120, step=12
)

# --- Inputs de CET (Melhoria 1a) ---
st.sidebar.subheader("Custos Adicionais (CET)")
taxa_adm_fixa = st.sidebar.number_input(
    "Taxa de Adm. Fixa (R$/mês)",
    min_value=0.0, value=25.0, step=1.0, format="%.2f"
)
seguro_perc_anual = st.sidebar.number_input(
    "Seguro Anual (% sobre Saldo Devedor)",
    min_value=0.0, value=0.5, step=0.01, format="%.2f",
    help="Ex: 0.5% a.a. Será dividido por 12 e aplicado ao saldo devedor mensal."
)

# Conversão de percentuais
taxa_anual = taxa_anual_perc / 100.0
seguro_perc_anual_calc = seguro_perc_anual / 100.0

# --- LÓGICA PRINCIPAL (Carregar Dados) ---
@st.cache_data
def carregar_cronogramas(principal, taxa_anual, prazo_meses, taxa_adm_fixa, seguro_perc_anual_calc):
    df_price = calcular_cronograma_price(
        principal, taxa_anual, prazo_meses, taxa_adm_fixa, seguro_perc_anual_calc
    )
    df_sac = calcular_cronograma_sac(
        principal, taxa_anual, prazo_meses, taxa_adm_fixa, seguro_perc_anual_calc
    )
    return df_price, df_sac

df_price, df_sac = carregar_cronogramas(
    principal, taxa_anual, prazo_meses, taxa_adm_fixa, seguro_perc_anual_calc
)

# --- ABAS DE FUNCIONALIDADES ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Comparador (SAC vs. Price)", 
    "🚀 Simulador de Amortização Extra",
    "💡 Amortizar vs. Investir?",
    "🧾 Relatório Completo (Excel)"
])


# --- ABA 1: COMPARADOR ---
with tab1:
    st.header("Comparativo: Sistema Price vs. Sistema SAC")
    st.markdown("Análise incluindo Juros, Taxa de Administração e Seguro (CET).")
    
    col1, col2 = st.columns(2)
    
    # Métricas Price
    with col1:
        st.subheader("Sistema Price")
        custo_total_price = calcular_custo_total(df_price)
        st.metric("Custo Total (Juros + Taxas)", formatar_moeda(custo_total_price))
        st.metric("Valor da 1ª Parcela", formatar_moeda(df_price.iloc[0]['Parcela']))
        st.metric("Valor da Última Parcela", formatar_moeda(df_price.iloc[-1]['Parcela']))

    # Métricas SAC
    with col2:
        st.subheader("Sistema SAC")
        custo_total_sac = calcular_custo_total(df_sac)
        st.metric("Custo Total (Juros + Taxas)", formatar_moeda(custo_total_sac))
        st.metric("Valor da 1ª Parcela", formatar_moeda(df_sac.iloc[0]['Parcela']))
        st.metric("Valor da Última Parcela", formatar_moeda(df_sac.iloc[-1]['Parcela']))

    st.warning(f"""
    **Conclusão:** No SAC, o custo total é **{formatar_moeda(custo_total_price - custo_total_sac)}** menor 
    que no Price para este cenário.
    """)
    
    # Gráficos de Evolução
    st.subheader("Evolução do Financiamento")
    df_chart_saldo = pd.DataFrame({
        'Mês': df_price['Mês'],
        'Saldo Devedor (Price)': df_price['Saldo Devedor'],
        'Saldo Devedor (SAC)': df_sac['Saldo Devedor']
    }).set_index('Mês')
    st.line_chart(df_chart_saldo)

    # Gráfico de Composição (Melhoria 2a)
    st.subheader("Composição da Parcela (Análise por Mês)")
    mes_selecionado = st.slider(
        "Escolha o mês para ver a composição:", 1, prazo_meses, 1
    )
    
    price_row = df_price.iloc[mes_selecionado - 1]
    sac_row = df_sac.iloc[mes_selecionado - 1]
    
    data_composicao = {
        'Juros': [price_row['Juros'], sac_row['Juros']],
        'Amortização': [price_row['Amortização'], sac_row['Amortização']],
        'Seguro': [price_row['Seguro'], sac_row['Seguro']],
        'Taxa Adm': [price_row['Taxa Adm'], sac_row['Taxa Adm']],
    }
    df_composicao = pd.DataFrame(data_composicao, index=['Price', 'SAC']).T
    
    st.bar_chart(df_composicao, height=400)
    st.caption("Gráfico de barras agrupadas mostrando os componentes de custo da parcela no mês selecionado.")


# --- ABA 2: SIMULADOR DE AMORTIZAÇÃO EXTRA ---
with tab2:
    st.header("Simulador de Amortização Extraordinária")
    st.markdown("Simule pagamentos únicos ou recorrentes (ex: 13º salário).")
    
    col_sim1, col_sim2 = st.columns(2)
    with col_sim1:
        tipo_sistema = st.radio("Sistema de Financiamento", ("Price", "SAC"), horizontal=True)
        estrategia = st.radio(
            "Estratégia de Abatimento",
            ("Reduzir Prazo", "Reduzir Valor da Parcela"),
            help="Reduzir o Prazo economiza mais juros."
        )
        estrategia_val = 'prazo' if estrategia == 'Reduzir Prazo' else 'parcela'
    
    with col_sim2:
        # Inputs para Melhoria 1c
        tipo_amort_extra = st.radio(
            "Tipo de Amortização Extra", 
            ("Pagamento Único", "Pagamento Anual (Recorrente)"), 
            horizontal=True
        )
        tipo_amort_val = 'unico' if tipo_amort_extra == 'Pagamento Único' else 'anual'
        
        valor_extra = st.number_input("Valor da Amortização (R$)", min_value=1.0, value=10000.0, step=500.0)
        mes_inicio_extra = st.slider(
            "Mês do Pagamento (ou Início Recorrente)", 
            min_value=1, max_value=prazo_meses, value=12
        )

    if st.button("Executar Simulação"):
        df_original = df_price if tipo_sistema == 'Price' else df_sac
        
        df_simulado = calcular_simulacao_extra(
            tipo_sistema, principal, taxa_anual, prazo_meses, estrategia_val,
            taxa_adm_fixa, seguro_perc_anual_calc,
            tipo_amort_val, valor_extra, mes_inicio_extra
        )
        
        # Salva no cache da sessão para outras abas
        st.session_state['df_simulado'] = df_simulado
        st.session_state['df_original_sim'] = df_original
        st.session_state['sim_params'] = {
            'valor_extra': valor_extra, 
            'mes_inicio_extra': mes_inicio_extra,
            'tipo_amort_extra': tipo_amort_val
        }

    # Exibe resultados se a simulação já foi rodada
    if 'df_simulado' in st.session_state:
        st.subheader("Resultados da Simulação")
        
        df_original = st.session_state['df_original_sim']
        df_simulado = st.session_state['df_simulado']
        
        custo_total_original = calcular_custo_total(df_original)
        custo_total_simulado = calcular_custo_total(df_simulado)
        economia_custo = custo_total_original - custo_total_simulado
        
        prazo_original = len(df_original)
        prazo_simulado = len(df_simulado)
        
        col_res1, col_res2, col_res3 = st.columns(3)
        col_res1.metric("Economia Total de Custo", formatar_moeda(economia_custo))
        col_res2.metric("Prazo Original", f"{prazo_original} meses")
        col_res3.metric("Novo Prazo", f"{prazo_simulado} meses", delta=f"{prazo_simulado - prazo_original} meses")
        
        # Gráfico Comparativo de Saldo Devedor
        df_chart_sim = df_original[['Mês', 'Saldo Devedor']].copy().rename(columns={'Saldo Devedor': 'Saldo Original'})
        df_simulado_chart = df_simulado[['Mês', 'Saldo Devedor']].rename(columns={'Saldo Devedor': 'Saldo Simulado'})
        df_chart_final = pd.merge(df_chart_sim, df_simulado_chart, on='Mês', how='outer').set_index('Mês')
        
        st.line_chart(df_chart_final.fillna(0))


# --- ABA 3: AMORTIZAR vs. INVESTIR? (Melhoria 1b) ---
with tab3:
    st.header("Análise: Amortizar Dívida vs. Investir")
    
    if 'df_simulado' not in st.session_state:
        st.warning("Por favor, execute uma simulação na Aba 2 primeiro.")
        st.info("Esta análise funciona melhor com 'Pagamento Único' para uma comparação direta.")
    else:
        # Carrega dados da simulação
        df_original = st.session_state['df_original_sim']
        df_simulado = st.session_state['df_simulado']
        sim_params = st.session_state['sim_params']
        
        # Só permite esta análise para "Pagamento Único" para ser uma comparação justa
        if sim_params['tipo_amort_extra'] != 'unico':
            st.error("Esta análise de 'Amortizar vs. Investir' foi projetada apenas para 'Pagamento Único'.")
            st.info("Por favor, rode uma nova simulação na Aba 2 com o tipo 'Pagamento Único'.")
        else:
            valor_investido = sim_params['valor_extra']
            mes_investimento = sim_params['mes_inicio_extra']
            prazo_restante = len(df_original) - mes_investimento
            
            taxa_invest_anual_perc = st.number_input(
                "Rendimento Líquido Anual da Aplicação (%)", 
                min_value=0.0, max_value=50.0, value=12.0, step=0.1,
                help="Taxa de juros compostos, líquida de impostos e taxas."
            )
            taxa_invest_anual = taxa_invest_anual_perc / 100.0
            
            # 1. Ganho ao Amortizar
            custo_total_original = calcular_custo_total(df_original)
            custo_total_simulado = calcular_custo_total(df_simulado)
            ganho_amortizacao = custo_total_original - custo_total_simulado
            
            # 2. Ganho ao Investir
            ganho_investimento, df_invest = calcular_investimento(
                valor_investido, taxa_invest_anual, prazo_restante
            )
            
            # 3. Exibir Comparação
            st.subheader("Comparativo de Ganhos")
            col1, col2 = st.columns(2)
            col1.metric("Opção 1: Ganho ao Amortizar", 
                        formatar_moeda(ganho_amortizacao),
                        help="Economia total em Juros, Seguros e Taxas ao quitar parte da dívida.")
            
            col2.metric(f"Opção 2: Ganho ao Investir por {prazo_restante} meses",
                        formatar_moeda(ganho_investimento),
                        help="Rendimento total obtido ao investir o mesmo valor.")
            
            if ganho_amortizacao > ganho_investimento:
                st.success(f"""
                **Recomendação: Amortizar a dívida é mais vantajoso.**
                Você economiza {formatar_moeda(ganho_amortizacao - ganho_investimento)} a mais do que ganharia investindo.
                """)
            else:
                st.info(f"""
                **Recomendação: Investir o dinheiro é mais vantajoso.**
                Você ganha {formatar_moeda(ganho_investimento - ganho_amortizacao)} a mais investindo do que economizaria amortizando.
                """)

            with st.expander("Ver Evolução do Investimento"):
                st.line_chart(df_invest.set_index('Mês')['Valor Acumulado'])


# --- ABA 4: RELATÓRIO COMPLETO (Melhoria 2b) ---
with tab4:
    st.header("Geração de Relatório (Cronogramas Completos)")
    st.markdown("Visualize todos os dados e baixe um arquivo Excel com todas as simulações.")

    # Dicionário para exportação
    dfs_to_export = {
        "Price_Original": df_price,
        "SAC_Original": df_sac
    }
    
    # Formatação para exibição
    df_price_display = df_price.style.format(formatar_moeda, subset=pd.IndexSlice[:, ['Parcela', 'Juros', 'Amortização', 'Seguro', 'Saldo Devedor']])
    df_sac_display = df_sac.style.format(formatar_moeda, subset=pd.IndexSlice[:, ['Parcela', 'Juros', 'Amortização', 'Seguro', 'Saldo Devedor']])
    
    with st.expander("Ver Cronograma Price (Original)"):
        st.dataframe(df_price_display, height=300)
        
    with st.expander("Ver Cronograma SAC (Original)"):
        st.dataframe(df_sac_display, height=300)

    if 'df_simulado' in st.session_state:
        st.subheader("Cronograma Simulado")
        df_simulado = st.session_state['df_simulado']
        df_simulado_display = df_simulado.style.format(formatar_moeda, subset=pd.IndexSlice[:, ['Parcela', 'Juros', 'Amortização', 'Seguro', 'Saldo Devedor']])
        
        st.dataframe(df_simulado_display, height=300)
        
        # Adiciona ao dicionário de exportação
        dfs_to_export["Simulacao"] = df_simulado

    # Botão de Download Único para Excel
    excel_data = convert_to_excel(dfs_to_export)
    
    st.download_button(
        label="Download Relatório Completo (.xlsx)",
        data=excel_data,
        file_name=f"relatorio_financeiro_{int(principal)}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Baixa um arquivo Excel com os cronogramas Price, SAC e Simulado em abas separadas."
    )
