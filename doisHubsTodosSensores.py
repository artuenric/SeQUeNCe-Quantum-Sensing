"""
Script: doisHubsTodosSensores.py

Objetivo
- Variante do guia.py que executa a simulação envolvendo 2 hubs e TODOS os sensores de cada hub, em vez de apenas 2 sensores por hub.
- Este script é autossuficiente: inclui CONFIG e set_parameters embutidos (não altera nem importa qsn.parameters).

Uso rápido
- python doisHubsTodosSensores.py --seed 123
- python doisHubsTodosSensores.py --hubs Hub1 Hub2 --seed 42

Notas
- Requer que as aplicações qsn.app.ghz_active (HubGHZActiveApp e SensorApp) e a topologia RouterNetTopo da biblioteca SeQUeNCe estejam instaladas no ambiente.
- O arquivo de rede padrão é qsn/net.json (mesmo caminho usado no projeto atual).
"""
from __future__ import annotations

import argparse
import random
import sys
from typing import Dict, List, Optional, Tuple


# ==========================
# CONFIG e set_parameters
# ==========================
# Copiados e embutidos aqui para tornar o script independente de qsn.parameters
CONFIG: Dict[str, object] = {
    "simulacao": {
        "NETWORK_CONFIG_FILE": "qsn/net.json",
        "LOG_FILE_NAME": "log",
        "START_TIME": 1e12,
        "END_TIME": 3e12,
    },
    "hubs_config": [
        {"name": "Hub1", "sensors": ["Sensor1H1", "Sensor2H1", "Sensor3H1", "Sensor4H1"]},
        {"name": "Hub2", "sensors": ["Sensor1H2", "Sensor2H2", "Sensor3H2", "Sensor4H2"]},
        {"name": "Hub3", "sensors": ["Sensor1H3", "Sensor2H3", "Sensor3H3", "Sensor4H3"]},
    ],
    "hardware": {
        "memoria": {
            "FREQ": 2e3,
            "EXPIRE": 0,
            "EFFICIENCY": 1,
            "FIDELITY": 0.93,
        },
        "swapping": {
            "SUCC_PROB": 0.64,
            "DEGRADATION": 0.99,
        },
        "detector": {
            "EFFICIENCY": 0.9,
            "COUNT_RATE": 5e7,
            "RESOLUTION": 100,
        },
        "canal_quantico": {
            "ATTENUATION": 0.0002,
        },
    },
    "circuito_quantico": {
        "operacoes": [
            ("X", 0),
            ("X", 1),
            ("X", 2),
            ("X", 3)
        ]
    },
}


def set_parameters(topology):
    """Configura os parâmetros da rede quântica com base no dicionário CONFIG."""
    try:
        from sequence.topology.router_net_topo import RouterNetTopo  # type: ignore
    except Exception:
        RouterNetTopo = None  # type: ignore

    hardware = CONFIG["hardware"]

    # Memórias dos roteadores
    for node in topology.get_nodes_by_type(getattr(RouterNetTopo, "QUANTUM_ROUTER", "QuantumRouter")):
        memory_array = node.get_components_by_type("MemoryArray")[0]
        memory_array.update_memory_params("frequency", hardware["memoria"]["FREQ"])
        memory_array.update_memory_params("coherence_time", hardware["memoria"]["EXPIRE"])
        memory_array.update_memory_params("efficiency", hardware["memoria"]["EFFICIENCY"])
        memory_array.update_memory_params("raw_fidelity", hardware["memoria"]["FIDELITY"])

    # Parâmetros de swapping (na pilha do gerenciador de rede)
    for node in topology.get_nodes_by_type(getattr(RouterNetTopo, "QUANTUM_ROUTER", "QuantumRouter")):
        node.network_manager.protocol_stack[1].set_swapping_success_rate(hardware["swapping"]["SUCC_PROB"])
        node.network_manager.protocol_stack[1].set_swapping_degradation(hardware["swapping"]["DEGRADATION"])

    # BSMs
    for node in topology.get_nodes_by_type(getattr(RouterNetTopo, "BSM_NODE", "BSMNode")):
        bsm = node.get_components_by_type("SingleAtomBSM")[0]
        bsm.update_detectors_params("efficiency", hardware["detector"]["EFFICIENCY"])
        bsm.update_detectors_params("count_rate", hardware["detector"]["COUNT_RATE"])
        bsm.update_detectors_params("time_resolution", hardware["detector"]["RESOLUTION"])

    # Canais quânticos
    for qc in topology.get_qchannels():
        qc.attenuation = hardware["canal_quantico"]["ATTENUATION"]


# ==========================
# Import helpers
# ==========================

def try_imports():
    """Tenta importar dependências do projeto e retorna os objetos necessários.

    Faz fallbacks informativos caso algum módulo não esteja disponível.
    """
    RouterNetTopo = None
    HubGHZActiveApp = None
    SensorApp = None
    setup_logger = None

    try:
        from sequence.topology.router_net_topo import RouterNetTopo  # type: ignore
    except Exception as e:
        print("Erro ao importar RouterNetTopo (sequence.topology.router_net_topo):", e)

    try:
        from qsn.app.ghz_active import HubGHZActiveApp, SensorApp  # type: ignore
    except Exception as e:
        print("Erro ao importar aplicações GHZ (qsn.app.ghz_active):", e)

    # setup_logger pode estar exposto em qsn.utils ou em qsn.utils.logging_setup
    try:
        from qsn.utils import setup_logger  # type: ignore
    except Exception:
        try:
            from qsn.utils.logging_setup import setup_logger  # type: ignore
        except Exception as e:
            print("Erro ao importar setup_logger (qsn.utils.*):", e)

    return {
        "RouterNetTopo": RouterNetTopo,
        "HubGHZActiveApp": HubGHZActiveApp,
        "SensorApp": SensorApp,
        "setup_logger": setup_logger,
    }


# ==========================
# Lógica principal
# ==========================

def pick_two_hubs(all_hubs: List[Dict[str, object]], names_from_cli: Optional[List[str]], seed: Optional[int]) -> Tuple[Dict[str, object], Dict[str, object]]:
    """Seleciona dois hubs: se names_from_cli fornecido, usa-os; senão escolhe aleatoriamente.
    Lança SystemExit se inválido.
    """
    if names_from_cli:
        if len(names_from_cli) != 2:
            print("Erro: Use exatamente dois nomes após --hubs, por exemplo: --hubs Hub1 Hub2")
            sys.exit(1)
        lookup = {h["name"]: h for h in all_hubs}  # type: ignore
        try:
            h1 = lookup[names_from_cli[0]]
            h2 = lookup[names_from_cli[1]]
        except KeyError as e:
            print(f"Erro: Hub '{e.args[0]}' não encontrado em CONFIG.hubs_config.")
            sys.exit(1)
        if h1 == h2:
            print("Erro: Os dois hubs devem ser distintos.")
            sys.exit(1)
        return h1, h2

    # aleatório
    if seed is not None:
        random.seed(seed)
    if len(all_hubs) < 2:
        print("Erro: CONFIG.hubs_config deve ter pelo menos 2 hubs.")
        sys.exit(1)
    return tuple(random.sample(all_hubs, 2))  # type: ignore


def main(hubs: Optional[List[str]] = None, seed: Optional[int] = None):
    objs = try_imports()
    RouterNetTopo = objs["RouterNetTopo"]
    HubGHZActiveApp = objs["HubGHZActiveApp"]
    SensorApp = objs["SensorApp"]
    setup_logger = objs["setup_logger"]

    # Verificações iniciais
    if None in (RouterNetTopo, HubGHZActiveApp, SensorApp):
        print("Dependências essenciais ausentes. Verifique se o ambiente do projeto está corretamente instalado.")
        if RouterNetTopo is None:
            print(" - sequence.topology.router_net_topo.RouterNetTopo")
        if HubGHZActiveApp is None or SensorApp is None:
            print(" - qsn.app.ghz_active.HubGHZActiveApp / SensorApp")
        sys.exit(1)

    # 1) Seleção dos hubs
    h1_info, h2_info = pick_two_hubs(CONFIG.get("hubs_config", []), hubs, seed)

    # 2) Carrega a topologia
    network_file = CONFIG["simulacao"]["NETWORK_CONFIG_FILE"]
    print(f"Carregando a rede a partir de '{network_file}'...")
    network_topo = RouterNetTopo(network_file)
    tl = network_topo.get_timeline()
    print("Topologia da rede carregada.")

    # 3) Configura o logger
    if setup_logger is not None:
        print("Configurando o logger para a simulação (modo: custom)...")
        try:
            setup_logger(tl, CONFIG["simulacao"]["LOG_FILE_NAME"], mode="custom")
        except Exception as e:
            print("Falha ao configurar logger:", e)
    else:
        print("setup_logger não disponível; pulando configuração de logs.")

    # 4) Aplica parâmetros de hardware
    print("Aplicando parâmetros de hardware (memórias, detectores, etc.)...")
    try:
        set_parameters(network_topo)
        print("Parâmetros aplicados.")
    except Exception as e:
        print("Falha ao aplicar parâmetros:", e)

    # 5) Visualiza a estrutura lógica e a escolha
    def print_hub_structure(hub_info: Dict[str, object]):
        hub = hub_info.get("name")
        print(f"└── Hub: {hub}")
        sensor_names = hub_info.get("sensors", [])  # type: ignore
        for i, sensor_name in enumerate(sensor_names):
            branch = "└──" if i == len(sensor_names) - 1 else "├──"
            print(f"    {branch} Sensor: {sensor_name}")

    print("\nEstrutura Lógica da Rede (foco nos hubs selecionados):")
    print_hub_structure(h1_info)
    print_hub_structure(h2_info)

    # 6) Mapeia nós da topologia
    all_nodes = network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)
    node_map = {node.name: node for node in all_nodes}

    def resolve_nodes(hub_info: Dict[str, object]):
        hub_node = node_map.get(hub_info["name"])  # type: ignore
        sensor_nodes = []
        for s_name in hub_info.get("sensors", []):  # type: ignore
            n = node_map.get(s_name)
            if n is None:
                print(f"Aviso: Sensor '{s_name}' não encontrado na topologia. Será ignorado.")
            else:
                sensor_nodes.append(n)
        return hub_node, sensor_nodes

    hub1_node, hub1_sensors = resolve_nodes(h1_info)
    hub2_node, hub2_sensors = resolve_nodes(h2_info)

    if not hub1_node or not hub2_node:
        print("Erro: Um dos hubs selecionados não foi encontrado na topologia.")
        sys.exit(1)

    if len(hub1_sensors) == 0 or len(hub2_sensors) == 0:
        print("Erro: Pelo menos um dos hubs não possui sensores válidos na topologia.")
        sys.exit(1)

    # 7) Instala as aplicações
    print(f"\nInstalando aplicações nos hubs {hub1_node.name} e {hub2_node.name} envolvendo TODOS os seus sensores...")

    # Notas:
    # O HubGHZActiveApp no guia original aceita (hub_node, selected_sensors, start, end, operacoes)
    # Aqui passamos a lista completa de sensores de cada hub.
    hub1_app = HubGHZActiveApp(
        hub1_node,
        [n.name for n in hub1_sensors],
        CONFIG["simulacao"]["START_TIME"],
        CONFIG["simulacao"]["END_TIME"],
        CONFIG["circuito_quantico"]["operacoes"],
        append_ghz=True,
        ghz_topology="chain",
    )
    hub1_node.set_app(hub1_app)

    hub2_app = HubGHZActiveApp(
        hub2_node,
        [n.name for n in hub2_sensors],
        CONFIG["simulacao"]["START_TIME"],
        CONFIG["simulacao"]["END_TIME"],
        CONFIG["circuito_quantico"]["operacoes"],
        append_ghz=True,
        ghz_topology="chain",
    )
    hub2_node.set_app(hub2_app)

    # Instala SensorApp em todos os sensores de ambos hubs
    for s_node in hub1_sensors + hub2_sensors:
        s_app = SensorApp(s_node)
        s_node.set_app(s_app)

    print(f"Aplicações instaladas: Hub {hub1_node.name} com {len(hub1_sensors)} sensores; Hub {hub2_node.name} com {len(hub2_sensors)} sensores.")

    # 8) Executa a simulação
    print("\nIniciando simulação...")
    tl.init()
    # Inicia ambos hubs (assumindo que cada app coordena com seus sensores conforme protocolo)
    hub1_app.start()
    hub2_app.start()
    tl.run()

    print("\nSimulação concluída!")
    log_file = CONFIG["simulacao"]["LOG_FILE_NAME"]
    print(f"Verifique o arquivo '{log_file}.txt' para ver os detalhes da comunicação.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Executa simulação envolvendo DOIS hubs e TODOS os sensores de cada um (versão script, independente de qsn.parameters)."
        )
    )
    parser.add_argument(
        "--hubs",
        nargs=2,
        metavar=("HUB1", "HUB2"),
        help="Nomes dos dois hubs a incluir (por padrão escolhe aleatoriamente)",
    )
    parser.add_argument("--seed", type=int, default=None, help="Semente aleatória para reprodutibilidade (na escolha aleatória de hubs)")
    args = parser.parse_args()

    main(hubs=args.hubs, seed=args.seed)
