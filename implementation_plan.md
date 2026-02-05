# Plano de Implementação: Agente Genérico (Tool Use Loop)

**Objetivo:** Implementar um ciclo completo de uso de ferramentas, onde o bot pode consultar dados do QGIS (ex: listar camadas, listar estações) e usar essa informação para interagir com o usuário ou executar ações parametrizadas.

## Arquitetura do Loop
1.  **LLM:** Envia `COMMAND: nome_comando args`
2.  **HidroBotDialog:**
    *   Detecta comando.
    *   Executa função no `plugin.py`.
    *   Captura o **retorno** da função (string).
    *   Adiciona o retorno ao histórico como `role: function` (ou `user` com prefixo "System Output").
    *   **Re-envia** o histórico atualizado para o LLM (Recursão/Loop).
3.  **LLM:** Analisa o retorno e decide:
    *   Responder ao usuário (ex: "Selecione uma das camadas: X, Y").
    *   Ou enviar outro comando.

## Proposed Changes

### 1. Funções de Consulta no Plugin (`plugin.py`)
Novos métodos que retornam strings úteis para o bot:
*   `list_layers()`: Retorna nomes das camadas vetoriais.
*   `list_nearest_stations()`: Retorna estações próximas.
*   `get_project_summary()`: Retorna resumo detalhado.

### 2. Suporte a Argumentos (`plugin.py`)
Atualizar métodos existentes para aceitar parâmetros opcionais:
*   `run_climate_analysis(station_code=None)`
*   `run_area(layer_name=None)`

### 3. Lógica de Loop (`ui/hidrobot_dialog.py`)
*   Refatorar `send_message` para suportar recursão (max depth = 3 para evitar loops infinitos).
*   Implementar parser de argumentos `key=value`.

### 4. Prompt do Sistema (`core/hidrobot.py`)
*   Ensinar o conceito de "Consultar antes de Agir".
*   Exemplo: "Para calcular área, se não souber a camada, use `listar_camadas` primeiro."

## Verification Plan
1.  **Teste de Consulta:** "Quais camadas eu tenho?" -> Bot deve usar `listar_camadas` e responder com a lista.
2.  **Teste de Fluxo:** "Faça análise climática" -> Bot usa `listar_estacoes` -> Bot pergunta "Qual estação?" -> Usuário responde -> Bot usa `analise_climatica code=X`.
