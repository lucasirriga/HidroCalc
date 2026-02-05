# HidroCalc QGIS Plugin

![Status](https://img.shields.io/badge/Status-Em%20Desenvolvimento-yellow)
![QGIS](https://img.shields.io/badge/QGIS-3.x-green)
![Python](https://img.shields.io/badge/Python-3.9+-blue)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

**HidroCalc** é um plugin avançado para QGIS projetado para auxiliar engenheiros no dimensionamento e otimização de redes hidráulicas de irrigação. Ele combina ferramentas de cálculo tradicionais com inteligência artificial para otimizar custos e eficiência.

## 🚀 Funcionalidades Principais

- **Dimensionamento Hidráulico:** Cálculo de perda de carga (Hazen-Williams), velocidade e pressão.
- **Otimização Genética:** Algoritmo genético integrado para encontrar a configuração de diâmetros mais econômica que atenda aos requisitos de pressão.
- **Relatórios Automáticos:** Geração de relatórios de materiais (tubos e peças) e serviços em PDF.
- **Análise Climática:** Integração com dados do INMET para cálculo de ETo e janelas de irrigação.

## 🛠️ Instalação

1. Clone este repositório na pasta de plugins do seu QGIS:
    - **Windows:** `C:\Users\SEU_USUARIO\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\`
    - **Linux/Mac:** `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`

    ```bash
    git clone https://github.com/seu-usuario/HidroCalc.git
    ```

2. Reinicie o QGIS.
3. Ative o plugin no menu `Complementos` > `Gerenciar e Instalar Complementos`.

## 📖 Como Usar

### Otimização Genética

1. Certifique-se de que suas camadas vetoriais estejam nomeadas corretamente (ex: 'Fonte', 'Válvulas', 'Adutora', 'Linha Lateral').
2. Clique no botão **"Otimizar Rede (Genético)"** na barra de ferramentas.
3. Aguarde o processamento. O plugin ajustará automaticamente os diâmetros para minimizar o custo.

## 🧪 Desenvolvimento e Testes

Este projeto utiliza `pytest` para testes.

1. Instale as dependências de desenvolvimento:

    ```bash
    pip install -r requirements-dev.txt
    ```

2. Execute os testes:

    ```bash
    pytest
    ```

## 📄 Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.
