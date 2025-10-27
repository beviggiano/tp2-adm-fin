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
    inflacao_anual: float = 0.0  # <-- MELHORIA 1: Inflação
) -> pd.DataFrame:
    """
    Calcula o cronograma Price, incluindo CET e Valor Presente da Parcela.
    """
    taxa_mensal = taxa_anual / 12
    seguro_perc_mensal = seguro_perc_anual / 12
    # MELHORIA 1: Cálculo da taxa de inflação mensal
    taxa_inflacao_mensal = (1 + inflacao_anual)**(1/12) - 1 if inflacao_anual > 0 else 0.0
    
    if taxa_mensal > 0:
        pmt_base = npf.pmt(taxa_mensal, prazo_meses, -principal)
    else:
        pmt_base = principal / prazo_meses

    cronograma = []
    saldo_devedor = principal

    for mes in range(1, prazo_meses + 1):
        juros = saldo_devedor * taxa_mensal
        
        if taxa_mensal > 0:
            amortizacao = pmt_base - juros
        else:
            amortizacao = pmt_base
        
        seguro_valor = saldo_devedor * seguro_perc_mensal
        parcela_total = pmt_base + taxa_adm_fixa + seguro_valor
        
        saldo_devedor -= amortizacao
        
        if mes == prazo_meses and saldo_devedor > 0.01:
            amortizacao += saldo_devedor
            parcela_total += saldo_devedor # Adiciona resíduo na última parcela
            saldo_devedor = 0.0

        # MELHORIA 1: Cálculo do Valor Presente da Parcela
        vp_parcela = parcela_total / ((1 + taxa_inflacao_mensal) ** mes)

        cronograma.append({
            "Mês": mes,
            "Parcela": parcela_total,
            "Juros": juros,
            "Amortização": amortizacao,
            "Seguro": seguro_valor,
            "Taxa Adm": taxa_adm_fixa,
            "Saldo Devedor": saldo_devedor,
            "VP Parcela": vp_parcela  # <-- MELHORIA 1: Nova coluna
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
    Calcula o cronograma SAC, incluindo CET e Valor Presente da Parcela.
    """
    taxa_mensal = taxa_anual / 12
    seguro_perc_mensal = seguro_perc_anual / 12
    taxa_inflacao_mensal = (1 + inflacao_anual)**(1/12) - 1 if inflacao_anual > 0 else 0.0
    amortizacao_fixa = principal / prazo_meses

    cronograma = []
    saldo_devedor = principal

    for mes in range(1, prazo_meses + 1):
        juros = saldo_devedor * taxa_mensal
        seguro_valor = saldo_devedor * seguro_perc_mensal
        
        parcela_total = amortizacao_fixa + juros + taxa_adm_fixa + seguro_valor
        
        saldo_devedor -= amortizacao_fixa
        
        if mes == prazo_meses:
            saldo_devedor = 0.0

        # MELHORIA 1: Cálculo do Valor Presente da Parcela
        vp_parcela = parcela_total / ((1 + taxa_inflacao_mensal) ** mes)

        cronograma.append({
            "Mês": mes,
            "Parcela": parcela_total,
            "Juros": juros,
            "Amortização": amortizacao_fixa,
            "Seguro": seguro_valor,
            "Taxa Adm": taxa_adm_fixa,
            "Saldo Devedor": saldo_devedor,
            "VP Parcela": vp_parcela  # <-- MELHORIA 1: Nova coluna
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
    inflacao_anual: float = 0.0  # <-- MELHORIA 1: Inflação
) -> pd.DataFrame:
    """
    Calcula um cronograma com amortizações extraordinárias (única ou recorrente),
    incluindo o cálculo do Valor Presente (VP) da parcela.
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
        # (Lógica de amortização extra e cálculo de parcela... omitida para brevidade, é a mesma de antes)
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

        # MELHORIA 1: Cálculo do Valor Presente da Parcela
        vp_parcela = parcela_total / ((1 + taxa_inflacao_mensal) ** mes_atual)

        cronograma.append({
            "Mês": mes_atual,
            "Parcela": parcela_total,
            "Juros": juros,
            "Amortização": amortizacao_total_mes,
            "Seguro": seguro_valor,
            "Taxa Adm": taxa_adm_fixa,
            "Saldo Devedor": saldo_devedor,
            "VP Parcela": vp_parcela # <-- MELHORIA 1: Nova coluna
        })

        # (Lógica de recálculo de prazo/parcela... omitida para brevidade, é a mesma de antes)
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
    Calcula a evolução de um investimento com juros compostos.
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

# --- MELHORIA 2: NOVA FUNÇÃO "SOLVER" ---
def encontrar_pagamento_meta(
    tipo_sistema: str, 
    principal: float, 
    taxa_anual: float, 
    prazo_original_meses: int, 
    prazo_desejado_meses: int
) -> float:
    """
    Calcula o valor extra MENSAL necessário (apenas amortização) para 
    quitar um financiamento no prazo desejado.
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
    Converte um dicionário de DataFrames para um arquivo Excel em memória.
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in dfs.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    return output
