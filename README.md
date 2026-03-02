# Sensoriamento Quântico Distribuído com Tolerância a Falhas

Este projeto implementa um simulador de **redes quânticas para sensoriamento distribuído** utilizando a biblioteca **SeQUeNCe** (Simulator of QUantum Network Communication Environments). O objetivo é validar protocolos de comunicação que permitem a sensores quânticos, coordenados por um nó central (Hub), realizar medições com precisão aprimorada através de emaranhamento multipartite.

## 🏛️ Arquitetura do Código (`qsn/`)

A aplicação implementa um protocolo "GHZ Ativo" onde o Hub orquestra a criação de estados Greenberger-Horne-Zeilinger (GHZ) entre múltiplos sensores. A robustez é garantida por um **mecanismo automático de fallback**: se o emaranhamento quântico falha, os sensores transitam para um modo de medição clássica.

### Estrutura de pacotes

```
qsn/
├── app/
│   └── ghz_active/
│       ├── hub_ghz_active_app.py       # Hub: orquestra emaranhamento e medição conjunta
│       ├── sensor_app.py               # Sensor: delegador de estado
│       ├── message_ghz_active.py       # Definição de mensagens do protocolo
│       ├── states/
│       │   ├── sensor_state.py         # Classe base abstrata
│       │   ├── normal_state.py         # Estado: aguardando emaranhamento
│       │   └── fallback_state.py       # Estado: medição clássica (contingência)
│       └── __init__.py
└── utils/
    ├── logging_setup.py                # Configurador de logs da simulação
    ├── tracked_modules.py              # Módulos a rastrear em logs
    └── __init__.py
```

### Componentes principais

#### **1. Hub (`hub_ghz_active_app.py`)**
- Inicia proativamente o protocolo GHZ enviando `PROPOSE_GHZ` aos sensores
- Gerencia reservas de emaranhamento quântico via SeQUeNCe Network Manager
- Monitora fidelidade de memórias e seleciona os sensores de melhor qualidade
- Realiza medições conjuntas quando suficientes sensores estão emaranhados
- Detecta falhas e envia `ATTEMPT_FAILED` aos sensores degradados

#### **2. Sensores com Máquina de Estados (`sensor_app.py`)**
Implementa padrão de máquina de estados finita:

- **NormalState** (`normal_state.py`)
  - Estado inicial
  - Aguarda `PROPOSE_GHZ` do Hub
  - Aceita participação no emaranhamento
  - Transita para fallback ao receber `ATTEMPT_FAILED`

- **FallbackState** (`fallback_state.py`)
  - Ativado automaticamente quando emaranhamento falha
  - Realiza medição local clássica
  - Envia resultado via `CLASSICAL_FALLBACK` ao Hub
  - Garante entrega de dados mesmo em cenários hostis

#### **3. Protocolo de Mensagens (`message_ghz_active.py`)**
```
PROPOSE_GHZ        → Hub → Sensores (inicia protocolo)
ACEPT_GHZ          → Sensores → Hub (confirma participação)
STATUS_UPDATE      → Sensores → Hub (notifica estado de memória)
ATTEMPT_FAILED     → Hub → Sensores (emaranhamento impossível)
CLASSICAL_FALLBACK → Sensores → Hub (resultado clássico)
```

#### **4. Logging (`logging_setup.py`)**
Sistema de rastreamento modular que registra apenas módulos especificados, permitindo análise detalhada do fluxo de execução em `poc_fallback_log.txt`.

---

## 🧪 Prova de Conceito (PoC): Tolerância a Falhas

### O que demonstra

A PoC comprova que o simulador sobrevive a falhas de coerência quântica através de transição automática para medição clássica. Um cenário controlado induz propositalmente uma falha num nó sensor e documenta as 5 fases da recuperação.

### Cenário

| Nó | Configuração | Resultado |
|----|--------------|-|
| **Sensor1** | Parâmetros ideais (0.0002 dB/km) | ✅ Emaranhamento sucesso |
| **Sensor2** | Parâmetros ideais (0.0002 dB/km) | ✅ Emaranhamento sucesso |
| **Sensor3** | Degradado (10 dB/km, 1ps coerência, 1% eff.) | ⚠️ Fallback clássico |

### As 5 Fases (registadas em `poc_fallback_log.txt`)

1. **Fase 1 - Configuração:** Topologia e parâmetros degradados inicializados
2. **Fase 2 - Funcionamento Normal:** Hub coordena emaranhamento; Sensor1/Sensor2 bem-sucedidos
3. **Fase 3 - Detecção de Falha:** Fim da janela; Sensor3 identificado como sem emaranhamento
4. **Fase 4 - Fallback:** Sensor3 transita `NormalState → FallbackState`, envia resultado clássico
5. **Fase 5 - Agregação:** Hub recolhe 2 resultados quânticos + 1 clássico = rede íntegra

### Executar a PoC

```bash
.venv/bin/python poc_fallback.py --seed 42
```

Saída esperada:
```
Sensores c/ emaranhamento quantico : ['Sensor1', 'Sensor2']
Sensores em fallback classico      : ['Sensor3']
Medicao conjunta completada        : True
Agregacao completa                 : True

CONCLUSAO: A falha de coerencia em Sensor3 NAO causou a queda da rede.
```

---

## 📖 Documentação Detalhada

Para análise profunda da PoC, consulte: **`POC_Detalhado.ipynb`**

Este notebook contém:
- Explicação teórica de máquinas de estados
- Dissecção linha-a-linha do código da PoC
- Interpretação dos timestamps de log
- Extensões possíveis (mais sensores, cenários diferentes)

---

## 🔧 Desenvolvimento Futuro

- Suporte para múltiplos Hubs com agregação distribuída
- Variação de parâmetros para análise de robustez
- Integração com optimizadores de topologia
- Novos protocolos além de GHZ (cluster states, etc.)

---

## 📚 Referências

- **SeQUeNCe**: https://github.com/mit-quanta/sequence-docs
- **GHZ States**: Greenberger, M. D.; Horne, M. A.; Zeilinger, A. (1989)
- **Quantum Sensing**: Giovannetti, V.; Lloyd, S.; Maccone, L. (2011)
