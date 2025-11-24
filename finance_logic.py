import pandas as pd
import numpy_financial as npf
from io import BytesIO
from typing import List, Dict, Tuple, Optional

# --- FUNÇÕES DE CÁLCULO FINANCEIRO (BACKEND) ---

def calcular_cronograma_price(
    principal: float, 
    taxa_anual: float, 
    prazo_meses: int, 
    taxa_adm_fixa: float = 0.0, 
    seguro_perc_anual: float = 0.0,
    inflacao_anual: float = 0.0  
) -> pd.DataFrame:
    """
    Gera o Fluxo de Caixa pelo Sistema Francês de Amortização (Tabela Price).
    
    Características Financeiras:
    1. Prestações (PMT) periódicas, iguais e sucessivas.
    2. A Amortização é crescente e os Juros são decrescentes.
    """

    # Conversão de Taxa Nominal Anual para Mensal (Convenção Linear, padrão bancário)
    taxa_mensal = taxa_anual / 12
    seguro_perc_mensal = seguro_perc_anual / 12
    
    # Taxa Equivalente para Inflação (Cálculo de Juros Compostos para Valor Presente)
    # Fórmula: (1 + i_anual)^(1/12) - 1
    taxa_inflacao_mensal = (1 + inflacao_anual)**(1/12) - 1 if inflacao_anual > 0 else 0.0
    
    # Cálculo da Prestação Base (PMT) sem taxas acessórias
    # Utiliza a fórmula da Anuidade Ordinária: PMT = PV * [ i / (1 - (1+i)^-n) ]
    if taxa_mensal > 0:
        pmt_base = npf.pmt(taxa_mensal, prazo_meses, -principal)
    else:
        pmt_base = principal / prazo_meses # Caso raro de juros zero

    cronograma = []
    saldo_devedor = principal

    # Iteração para construção do Fluxo de Caixa mensal
    for mes in range(1, prazo_meses + 1):
        # 1. Juros são calculados sobre o Saldo Devedor ANTERIOR (J = SD * i)
        juros = saldo_devedor * taxa_mensal
        
        # 2. Amortização é o que sobra da parcela após pagar os juros
        if taxa_mensal > 0:
            amortizacao = pmt_base - juros
        else:
            amortizacao = pmt_base
        
        # 3. Cálculo de componentes do CET (Custo Efetivo Total)
        seguro_valor = saldo_devedor * seguro_perc_mensal
        parcela_total = pmt_base + taxa_adm_fixa + seguro_valor
        
        # 4. Atualização do Saldo Devedor
        saldo_devedor -= amortizacao
        
        # Tratamento de resíduo financeiro na última parcela (arredondamentos)
        if mes == prazo_meses and saldo_devedor > 0.01:
            amortizacao += saldo_devedor
            parcela_total += saldo_devedor
            saldo_devedor = 0.0

        # Cálculo do Valor Presente (VP)
        # Traz o fluxo futuro a valor presente descontando a inflação acumulada.
        # VP = VF / (1 + taxa)^n
        vp_parcela = parcela_total / ((1 + taxa_inflacao_mensal) ** mes)

        cronograma.append({
            "Mês": mes,
            "Parcela": parcela_total,
            "Juros": juros,
            "Amortização": amortizacao,
            "Seguro": seguro_valor,
            "Taxa Adm": taxa_adm_fixa,
            "Saldo Devedor": saldo_devedor,
            "VP Parcela": vp_parcela
        })

    return pd.DataFrame(cronograma)

def calcular_cronograma_sac(
    principal: float, 
    taxa_anual: float, 
    prazo_meses: int, 
    taxa_adm_fixa: float = 0.0, 
    seguro_perc_anual: float = 0.0,
    inflacao_anual: float = 0.0  # <-- MELHORIA 1: Inflação
) -> pd.DataFrame:
    """
    Gera o Fluxo de Caixa pelo Sistema de Amortização Constante (SAC).
    
    Características Financeiras:
    1. Amortização é fixa mensalmente (Principal / Prazo).
    2. A Prestação é decrescente ao longo do tempo.
    """

    taxa_mensal = taxa_anual / 12
    seguro_perc_mensal = seguro_perc_anual / 12
    taxa_inflacao_mensal = (1 + inflacao_anual)**(1/12) - 1 if inflacao_anual > 0 else 0.0
    amortizacao_fixa = principal / prazo_meses

    cronograma = []
    saldo_devedor = principal

    for mes in range(1, prazo_meses + 1):
        # Juros sobre o saldo devedor
        juros = saldo_devedor * taxa_mensal
        seguro_valor = saldo_devedor * seguro_perc_mensal
        
        # A parcela é a soma da Amortização Fixa + Juros Variáveis + Taxas
        parcela_total = amortizacao_fixa + juros + taxa_adm_fixa + seguro_valor
        
        # O Saldo Devedor cai de forma linear
        saldo_devedor -= amortizacao_fixa
        
        if mes == prazo_meses:
            saldo_devedor = 0.0

        vp_parcela = parcela_total / ((1 + taxa_inflacao_mensal) ** mes)

        cronograma.append({
            "Mês": mes,
            "Parcela": parcela_total,
            "Juros": juros,
            "Amortização": amortizacao_fixa,
            "Seguro": seguro_valor,
            "Taxa Adm": taxa_adm_fixa,
            "Saldo Devedor": saldo_devedor,
            "VP Parcela": vp_parcela  
        })

    return pd.DataFrame(cronograma)

def calcular_simulacao_extra(
    tipo_sistema: str, 
    principal: float, 
    taxa_anual: float, 
    prazo_meses: int, 
    estrategia: str, 
    taxa_adm_fixa: float = 0.0, 
    seguro_perc_anual: float = 0.0,
    tipo_amort_extra: str = 'unico', 
    valor_extra: float = 0.0, 
    mes_inicio_extra: int = 1,
    inflacao_anual: float = 0.0 
) -> pd.DataFrame:
    """
    Simula o impacto de Amortizações Extraordinárias no Fluxo de Caixa.
    
    Regra de Negócio:
    Toda amortização extra deve abater diretamente o Saldo Devedor.
    A partir daí, existem duas estratégias de recálculo:
    A) Manter o prazo e reduzir o valor da parcela.
    B) Manter a parcela (aproximadamente) e reduzir o prazo total (Economia máxima de juros).
    """

    taxa_mensal = taxa_anual / 12
    seguro_perc_mensal = seguro_perc_anual / 12
    taxa_inflacao_mensal = (1 + inflacao_anual)**(1/12) - 1 if inflacao_anual > 0 else 0.0
    
    cronograma = []
    saldo_devedor = principal
    mes_atual = 1
    prazo_total_simulado = prazo_meses

    if tipo_sistema == 'Price':
        parcela_base_juros_amort = npf.pmt(taxa_mensal, prazo_meses, -principal) if taxa_mensal > 0 else (principal / prazo_meses)
    else: # SAC
        amortizacao_base = principal / prazo_meses

    while saldo_devedor > 0.01 and mes_atual <= prazo_total_simulado:
        
        # Verifica se há ocorrência de pagamento extra neste mês
        amortizacao_extra_mes = 0.0
        if valor_extra > 0:
            if tipo_amort_extra == 'unico' and mes_atual == mes_inicio_extra:
                amortizacao_extra_mes = valor_extra
            elif tipo_amort_extra == 'anual' and mes_atual >= mes_inicio_extra and (mes_atual - mes_inicio_extra) % 12 == 0:
                amortizacao_extra_mes = valor_extra

        juros = saldo_devedor * taxa_mensal
        seguro_valor = saldo_devedor * seguro_perc_mensal

        if tipo_sistema == 'Price':
            amortizacao_normal = parcela_base_juros_amort - juros
        else: # SAC
            amortizacao_normal = amortizacao_base
            
        if (amortizacao_normal + amortizacao_extra_mes) > saldo_devedor:
            amortizacao_total_mes = saldo_devedor + juros
            amortizacao_extra_mes = saldo_devedor - amortizacao_normal
        else:
            amortizacao_total_mes = amortizacao_normal + amortizacao_extra_mes
            
        parcela_total = amortizacao_total_mes + juros + taxa_adm_fixa + seguro_valor
        
        saldo_devedor_anterior = saldo_devedor
        saldo_devedor -= (amortizacao_normal + amortizacao_extra_mes)
        
        if mes_atual == prazo_total_simulado and saldo_devedor > 0.01:
             amortizacao_total_mes += saldo_devedor
             parcela_total += saldo_devedor
             saldo_devedor = 0.0

        vp_parcela = parcela_total / ((1 + taxa_inflacao_mensal) ** mes_atual)

        cronograma.append({
            "Mês": mes_atual,
            "Parcela": parcela_total,
            "Juros": juros,
            "Amortização": amortizacao_total_mes,
            "Seguro": seguro_valor,
            "Taxa Adm": taxa_adm_fixa,
            "Saldo Devedor": saldo_devedor,
            "VP Parcela": vp_parcela 
        })

        # --- RECÁLCULO DO FINANCIAMENTO ---
        # Se houve amortização extra, o fluxo futuro muda. Recalculamos conforme a estratégia.
        if amortizacao_extra_mes > 0 and saldo_devedor > 0.01:
            prazo_restante = prazo_total_simulado - mes_atual
            
            if estrategia == 'parcela':
                if tipo_sistema == 'Price':
                    parcela_base_juros_amort = npf.pmt(taxa_mensal, prazo_restante, -saldo_devedor) if taxa_mensal > 0 else (saldo_devedor / prazo_restante)
                else: # SAC
                    amortizacao_base = saldo_devedor / prazo_restante
            else: # Reduzir Prazo
                if tipo_sistema == 'Price':
                    novo_prazo_restante = npf.nper(taxa_mensal, -parcela_base_juros_amort, saldo_devedor) if taxa_mensal > 0 else (saldo_devedor / parcela_base_juros_amort)
                else: # SAC
                    novo_prazo_restante = saldo_devedor / amortizacao_base
                prazo_total_simulado = mes_atual + int(novo_prazo_restante + 0.99)

        mes_atual += 1
        
    return pd.DataFrame(cronograma)

def calcular_investimento(
    valor_inicial: float, 
    taxa_anual_liquida: float, 
    prazo_meses: int
) -> Tuple[float, pd.DataFrame]:
    """
    Calcula o Valor Futuro (VF) de uma aplicação financeira.
    Utilizado para Análise de Custo de Oportunidade.
    
    Fórmula: VF = VP * (1 + i)^n
    """

    if taxa_anual_liquida > 0:
        taxa_mensal = (1 + taxa_anual_liquida)**(1/12) - 1
    else:
        taxa_mensal = 0
        
    cronograma = []
    valor_acumulado = valor_inicial
    
    for mes in range(1, prazo_meses + 1):
        rendimento = valor_acumulado * taxa_mensal
        valor_acumulado += rendimento
        
        cronograma.append({
            "Mês": mes,
            "Rendimento": rendimento,
            "Valor Acumulado": valor_acumulado
        })
        
    ganho_total = valor_acumulado - valor_inicial
    return ganho_total, pd.DataFrame(cronograma)

def encontrar_pagamento_meta(
    tipo_sistema: str, 
    principal: float, 
    taxa_anual: float, 
    prazo_original_meses: int, 
    prazo_desejado_meses: int
) -> float:
    """
    Algoritmo de 'Goal Seeking' (Atingir Meta).
    Calcula quanto de aporte extra mensal é necessário para reduzir o prazo 'X' para 'Y'.
    """
    
    # Se o prazo desejado for maior ou igual, não há pagamento extra
    if prazo_desejado_meses >= prazo_original_meses:
        return 0.0
        
    taxa_mensal = taxa_anual / 12
    extra_necessario = 0.0
    
    try:
        if tipo_sistema == 'Price':
            # Calcula a parcela (J+A) original
            pmt_base_original = npf.pmt(taxa_mensal, prazo_original_meses, -principal) if taxa_mensal > 0 else (principal / prazo_original_meses)
            
            # Calcula a parcela (J+A) necessária para o novo prazo
            pmt_base_desejado = npf.pmt(taxa_mensal, prazo_desejado_meses, -principal) if taxa_mensal > 0 else (principal / prazo_desejado_meses)
            
            # A diferença é o extra mensal
            extra_necessario = pmt_base_desejado - pmt_base_original
            
        else: # SAC
            # Calcula a amortização original
            amort_original = principal / prazo_original_meses
            
            # Calcula a amortização desejada
            amort_desejada = principal / prazo_desejado_meses
            
            # A diferença é o extra mensal (que será somado à amortização)
            extra_necessario = amort_desejada - amort_original
            
    except Exception as e:
        # Captura erros (ex: divisão por zero se prazo for 0)
        print(f"Erro no cálculo da meta: {e}")
        return 0.0

    return extra_necessario

def convert_to_excel(dfs: Dict[str, pd.DataFrame]) -> BytesIO:
    """
    Exportação de Relatórios.
    Gera arquivo binário compatível com MS Excel (.xlsx) contendo múltiplas abas.
    """
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in dfs.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    return output
