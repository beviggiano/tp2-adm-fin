# 🏦 Simulador Interativo de Operações Financeiras

Este projeto é um dashboard web interativo construído em Python e Streamlit, desenvolvido como parte do "Trabalho 2" da disciplina de Administração Financeira (CAD 167) da UFMG.

A aplicação permite a simulação e análise avançada de operações de financiamento, comparando sistemas de amortização, calculando o Custo Efetivo Total (CET) e avaliando estratégias financeiras como amortizações extraordinárias.

## ✨ Funcionalidades Principais

* **Comparador SAC vs. Price:** Analisa os dois principais sistemas de amortização, mostrando a evolução do saldo devedor, o valor da parcela e o custo total.
* **Cálculo de CET:** Inclui nos cálculos custos adicionais como Taxa de Administração e Seguros, fornecendo uma simulação mais realista.
* **Simulador de Amortização Extra:** Permite simular o impacto de pagamentos únicos ou recorrentes (ex: 13º salário) na dívida, usando estratégias de redução de prazo ou de parcela.
* **Análise "Amortizar vs. Investir?":** Compara a economia de juros obtida ao amortizar a dívida com o ganho potencial de investir o mesmo valor.
* **Geração de Relatórios:** Exporta todos os cronogramas (Original Price, Original SAC, Simulado) para um único arquivo Excel (.xlsx) com múltiplas abas.

## 📂 Estrutura do Projeto

O projeto é dividido em dois arquivos Python principais, seguindo boas práticas de modularização:

* `finance_logic.py`: O "backend" do sistema. Contém todas as funções de cálculo financeiro (ex: `calcular_cronograma_price`, `calcular_simulacao_extra`).
* `app.py`: O "frontend" da aplicação. Contém toda a lógica da interface do usuário (UI) usando o Streamlit.
* `requirements.txt`: A lista de dependências do projeto.

## 🚀 Como Executar o Sistema

Para rodar este projeto em sua máquina local, siga os passos abaixo.

### 1. Pré-requisitos

* Você precisa ter o **Python 3.8** (ou mais recente) instalado em seu computador.
* Os arquivos `app.py`, `finance_logic.py`, e `requirements.txt` devem estar no mesmo diretório.

### 2. Instalação

1.  **Abra seu terminal** (Prompt de Comando, PowerShell ou Terminal).

2.  **Navegue até o diretório** onde você salvou os arquivos do projeto.
    ```bash
    cd /caminho/para/o/projeto
    ```

3.  **(Opcional, mas recomendado)** Crie e ative um ambiente virtual (virtualenv) para isolar as dependências do projeto:
    ```bash
    # Criar o ambiente
    python -m venv .venv
    
    # Ativar no Windows (PowerShell)
    .\.venv\Scripts\Activate.ps1
    
    # Ativar no macOS/Linux
    source .venv/bin/activate
    ```

4.  **Instale as bibliotecas necessárias** usando o arquivo `requirements.txt`:
    ```bash
    pip install -r requirements.txt
    ```

### 3. Execução

1.  Após a instalação, execute o seguinte comando no seu terminal:
    ```bash
    streamlit run app.py
    ```

2.  O Streamlit iniciará o servidor e abrirá automaticamente o seu navegador web padrão, exibindo a aplicação pronta para uso.
