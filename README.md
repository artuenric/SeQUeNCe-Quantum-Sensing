# Simulação de Redes para Sensoriamento Quântico Distribuído

Este projeto apresenta uma plataforma para simular redes quânticas aplicadas ao **sensoriamento distribuído**, utilizando a biblioteca **SeQUeNCe**. O objetivo principal é explorar e validar protocolos de comunicação que permitem a um conjunto de sensores quânticos, coordenados por um nó central (Hub), realizar medições com precisão aprimorada.

Para alcançar sensibilidades além dos limites clássicos, muitos protocolos de sensoriamento quântico se baseiam na criação de estados emaranhados multipartites entre os sensores. Este repositório implementa, como uma primeira solução, um protocolo "ativo" onde um Hub orquestra a geração de um estado Greenberger-Horne-Zeilinger (GHZ) entre os nós sensores. O protocolo também inclui mecanismos de *fallback* para os casos em que o emaranhamento quântico não é bem-sucedido, garantindo a robustez da rede.

## 🏛️ Arquitetura do Projeto

A estrutura do projeto foi desenhada para separar as responsabilidades de forma clara, facilitando a manutenção, a escalabilidade e a adição de novos protocolos de sensoriamento no futuro.

  * **Configuração (`qsn/net.json`, `qsn/parameters.py`):** Define o cenário da simulação. Aqui, especificamos os componentes da rede (nós e suas conexões) e seus parâmetros físicos, como fidelidade e eficiência das memórias.
  * **Lógica da Aplicação (`qsn/app/`):** Contém o "cérebro" da simulação. Atualmente, a implementação se concentra no protocolo `ghz_active`:
      * `ghz_active/hub_ghz_active_app.py`: Aplicação proativa do Hub, que inicia e gerencia o protocolo de criação do estado GHZ.
      * `ghz_active/sensor_ghz_active_app.py`: Aplicação reativa dos Sensores, que respondem às propostas do Hub e tentam o emaranhamento (Plano A).
      * `ghz_active/sensor_ghz_active_fallback_app.py`: Aplicação de contingência (Plano B), ativada se o emaranhamento falhar. Realiza uma medição local e envia o resultado clássico ao Hub.
      * `ghz_active/message_ghz_active.py`: Define o "idioma" da comunicação para o protocolo GHZ, com todos os tipos de mensagens trocadas entre os nós.
  * **Ferramentas (`qsn/utils/`):** Módulos de suporte, como a configuração de logs para monitorar a execução da simulação.
  * **Execução e Análise (`GUIA.ipynb`, `log.txt`):** Notebooks para guiar a execução e arquivos de log para analisar os resultados.

A topologia da rede simulada consiste em 3 Hubs, cada um conectado a 4 Sensores, com conexões quânticas e clássicas entre eles, conforme definido em `qsn/net.json`.

## 🚀 Como Executar a Simulação

Existem duas maneiras principais de executar a simulação: através do script principal ou interativamente usando o notebook.

### 1\. Execução Completa

O script `sensorActiveNet.py` é o ponto de entrada principal para rodar a simulação completa. Ele carrega a configuração, instala as aplicações em todos os hubs e sensores, e executa o protocolo.

Para executar, basta rodar o seguinte comando a partir da raiz do projeto:

```bash
python -m qsn.sensorActiveNet
```

Ao final, os resultados detalhados da execução serão salvos no arquivo `log.txt`.

### 2\. Execução Interativa com o `GUIA.ipynb`

O notebook `GUIA.ipynb` oferece um ambiente interativo para entender e executar a simulação passo a passo. Ele permite:

  * Carregar a topologia e os parâmetros de forma controlada.
  * Visualizar a estrutura lógica da rede.
  * Executar um cenário focado, selecionando um Hub e um par aleatório de Sensores para testar o protocolo em menor escala.

Recomenda-se abrir o `GUIA.ipynb` em um ambiente como o Jupyter Lab ou VS Code para uma experiência mais rica.

## 📝 Entendendo o Fluxo do Protocolo (Exemplo: GHZ Ativo)

O fluxo de comunicação do protocolo implementado pode ser observado no arquivo `log.txt`. As principais etapas são:

1.  **Início:** O Hub inicia o processo enviando uma mensagem `PROPOSE_GHZ` para os sensores que monitora.
2.  **Aceitação:** Os sensores respondem com uma mensagem `ACEPT_GHZ`, confirmando a participação.
3.  **Requisição de Emaranhamento:** O Hub solicita formalmente o emaranhamento com os sensores que aceitaram.
4.  **Confirmação:** Os nós trocam informações sobre a reserva de recursos para o emaranhamento.
5.  **Atualização de Status:** Uma vez que o emaranhamento é bem-sucedido, os sensores notificam o Hub enviando o status `ENTANGLED`.
6.  **Medição Conjunta:** Após o fim do tempo estipulado, se um número mínimo de sensores estiver emaranhado, o Hub realiza uma medição conjunta simulada.
7.  **(Fallback)**: Se o emaranhamento com um sensor falhar, o Hub notifica o sensor com `ATTEMPT_FAILED`. O sensor então ativa sua aplicação de fallback, realiza uma medição local e envia um resultado clássico de volta.

## 🛠️ Configuração

Para modificar os parâmetros da simulação, edite o arquivo `qsn/parameters.py`. Nele, você pode ajustar:

  * Tempos de início e fim da simulação.
  * A relação entre Hubs e Sensores.
  * Parâmetros de hardware, como fidelidade da memória e eficiência dos detectores.

Para alterar a topologia da rede (adicionar/remover nós ou conexões), modifique o arquivo `qsn/net.json`.
