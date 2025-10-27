import pandas as pd
import numpy_financial as npf
from io import BytesIO
from typing import List, Dict, Tuple, Optional

# --- FUNÇÕES DE CÁLCULO FINANCEIRO (BACKEND) ---
# Implementação com Type Hints (Melhoria 3a) e lógica de CET (Melhoria 1a)

def calcular_cronograma_price(
    principal: float, 
    taxa_anual: float, 
    prazo_meses: int, 
    taxa_adm_fixa: float = 0.0, 
    seguro_perc_anual: float = 0.0
) -> pd.DataFrame:
    """
    Calcula o cronograma Price, incluindo custos de CET (taxa adm e seguro).
    """
    taxa_mensal = taxa_anual / 12
    # O seguro % anual também é dividido por 12
    seguro_perc_mensal = seguro_perc_anual / 12
    
    # Se a taxa for 0, o cálculo de PMT falha
    if taxa_mensal > 0:
        # PMT calcula apenas a parte de Juros + Amortização
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
        
        # Cálculo dos custos de CET
        seguro_valor = saldo_devedor * seguro_perc_mensal
        
        # Parcela total = (Juros + Amort) + Taxas
        parcela_total = pmt_base + taxa_adm_fixa + seguro_valor
        
        saldo_devedor -= amortizacao
        
        # Correção para o último mês
        if mes == prazo_meses and saldo_devedor > 0.01:
            amortizacao += saldo_devedor
            saldo_devedor = 0.0

        cronograma.append({
            "Mês": mes,
            "Parcela": parcela_total,
            "Juros": juros,
            "Amortização": amortizacao,
            "Seguro": seguro_valor,
            "Taxa Adm": taxa_adm_fixa,
            "Saldo Devedor": saldo_devedor
        })

    return pd.DataFrame(cronograma)

def calcular_cronograma_sac(
    principal: float, 
    taxa_anual: float, 
    prazo_meses: int, 
    taxa_adm_fixa: float = 0.0, 
    seguro_perc_anual: float = 0.0
) -> pd.DataFrame:
    """
    Calcula o cronograma SAC, incluindo custos de CET (taxa adm e seguro).
    """
    taxa_mensal = taxa_anual / 12
    seguro_perc_mensal = seguro_perc_anual / 12
    amortizacao_fixa = principal / prazo_meses

    cronograma = []
    saldo_devedor = principal

    for mes in range(1, prazo_meses + 1):
        juros = saldo_devedor * taxa_mensal
        seguro_valor = saldo_devedor * seguro_perc_mensal
        
        # Parcela total = (Juros + Amort) + Taxas
        parcela_total = amortizacao_fixa + juros + taxa_adm_fixa + seguro_valor
        
        saldo_devedor -= amortizacao_fixa
        
        # Correção para o último mês
        if mes == prazo_meses:
            saldo_devedor = 0.0

        cronograma.append({
            "Mês": mes,
            "Parcela": parcela_total,
            "Juros": juros,
            "Amortização": amortizacao_fixa,
            "Seguro": seguro_valor,
            "Taxa Adm": taxa_adm_fixa,
            "Saldo Devedor": saldo_devedor
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
    mes_inicio_extra: int = 1
) -> pd.DataFrame:
    """
    Calcula um cronograma com amortizações extraordinárias (única ou recorrente).
    Implementação da Melhoria 1c.
    """
    taxa_mensal = taxa_anual / 12
    seguro_perc_mensal = seguro_perc_anual / 12
    
    cronograma = []
    saldo_devedor = principal
    mes_atual = 1
    prazo_total_simulado = prazo_meses

    # Define os parâmetros base de cálculo
    if tipo_sistema == 'Price':
        parcela_base_juros_amort = npf.pmt(taxa_mensal, prazo_meses, -principal) if taxa_mensal > 0 else (principal / prazo_meses)
    else: # SAC
        amortizacao_base = principal / prazo_meses

    while saldo_devedor > 0.01 and mes_atual <= prazo_total_simulado:
        # 1. Verifica se é mês de amortização extra
        amortizacao_extra_mes = 0.0
        if valor_extra > 0:
            if tipo_amort_extra == 'unico' and mes_atual == mes_inicio_extra:
                amortizacao_extra_mes = valor_extra
            elif tipo_amort_extra == 'anual' and mes_atual >= mes_inicio_extra and (mes_atual - mes_inicio_extra) % 12 == 0:
                amortizacao_extra_mes = valor_extra

        # 2. Calcula componentes normais
        juros = saldo_devedor * taxa_mensal
        seguro_valor = saldo_devedor * seguro_perc_mensal

        if tipo_sistema == 'Price':
            amortizacao_normal = parcela_base_juros_amort - juros
        else: # SAC
            amortizacao_normal = amortizacao_base
            
        # 3. Lógica de Quitação (não amortizar mais que o saldo)
        if (amortizacao_normal + amortizacao_extra_mes) > saldo_devedor:
            amortizacao_total_mes = saldo_devedor + juros # Paga juros e quita
            amortizacao_extra_mes = saldo_devedor - amortizacao_normal
        else:
            amortizacao_total_mes = amortizacao_normal + amortizacao_extra_mes
            
        # 4. Parcela Final
        parcela_total = amortizacao_total_mes + juros + taxa_adm_fixa + seguro_valor
        
        # 5. Atualiza Saldo Devedor
        saldo_devedor_anterior = saldo_devedor
        saldo_devedor -= (amortizacao_normal + amortizacao_extra_mes)
        
        # 6. Lógica de Fim de Prazo (garantir zerar)
        if mes_atual == prazo_total_simulado and saldo_devedor > 0.01:
             amortizacao_total_mes += saldo_devedor
             parcela_total += saldo_devedor
             saldo_devedor = 0.0

        cronograma.append({
            "Mês": mes_atual,
            "Parcela": parcela_total,
            "Juros": juros,
            "Amortização": amortizacao_total_mes,
            "Seguro": seguro_valor,
            "Taxa Adm": taxa_adm_fixa,
            "Saldo Devedor": saldo_devedor
        })

        # 7. Recalcula parâmetros futuros se houve amortização extra
        if amortizacao_extra_mes > 0 and saldo_devedor > 0.01:
            prazo_restante = prazo_total_simulado - mes_atual
            
            if estrategia == 'parcela': # Reduzir Parcela
                if tipo_sistema == 'Price':
                    parcela_base_juros_amort = npf.pmt(taxa_mensal, prazo_restante, -saldo_devedor) if taxa_mensal > 0 else (saldo_devedor / prazo_restante)
                else: # SAC
                    amortizacao_base = saldo_devedor / prazo_restante
                    
            else: # Reduzir Prazo
                if tipo_sistema == 'Price':
                    if taxa_mensal > 0:
                        novo_prazo_restante = npf.nper(taxa_mensal, -parcela_base_juros_amort, saldo_devedor)
                    else:
                        novo_prazo_restante = saldo_devedor / parcela_base_juros_amort
                else: # SAC
                    novo_prazo_restante = saldo_devedor / amortizacao_base
                
                prazo_total_simulado = mes_atual + int(novo_prazo_restante + 0.99) # Arredonda pra cima

        mes_atual += 1
        
    return pd.DataFrame(cronograma)

def calcular_investimento(
    valor_inicial: float, 
    taxa_anual_liquida: float, 
    prazo_meses: int
) -> Tuple[float, pd.DataFrame]:
    """
    Calcula a evolução de um investimento com juros compostos.
    Implementação da Melhoria 1b.
    """
    # Juros compostos: converte taxa anual para mensal
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

def convert_to_excel(dfs: Dict[str, pd.DataFrame]) -> BytesIO:
    """
    Converte um dicionário de DataFrames para um arquivo Excel em memória.
    Implementação da Melhoria 2b.
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in dfs.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)
    # output.seek(0) # Não é mais necessário com as versões recentes do pd/st
    return output
