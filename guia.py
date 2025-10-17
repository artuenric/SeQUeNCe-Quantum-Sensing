"""
guia.py

Script que replica o notebook GUIA.ipynb.

Ele executa os mesmos passos do notebook:
- importa módulos
- carrega a topologia da rede
- configura o logger
- aplica parâmetros de hardware
- mostra a estrutura lógica dos hubs/sensores
- seleciona aleatoriamente 2 sensores para um hub alvo
- instala as aplicações (hub + sensores)
- executa a simulação

Use --hub para escolher outro hub (padrão: Hub1) e --seed para tornar a seleção determinística.
"""

from __future__ import annotations

import argparse
import random
import sys
from typing import Optional


def try_imports():
    """Tenta importar dependências do projeto e retorna os objetos necessários.

    Faz fallbacks informativos caso algum módulo não esteja disponível.
    """
    RouterNetTopo = None
    HubGHZActiveApp = None
    SensorGHZActiveApp = None
    set_parameters = None
    CONFIG = None
    setup_logger = None

    try:
        from sequence.topology.router_net_topo import RouterNetTopo
    except Exception as e:
        print("Erro ao importar RouterNetTopo (sequence.topology.router_net_topo):", e)

    try:
        from qsn.app.ghz_active import HubGHZActiveApp, SensorApp
    except Exception as e:
        print("Erro ao importar aplicações GHZ (qsn.app.ghz_active):", e)

    try:
        from qsn.parameters import set_parameters, CONFIG
    except Exception as e:
        print("Erro ao importar set_parameters/CONFIG (qsn.parameters):", e)

    # setup_logger pode estar exposto em qsn.utils ou em qsn.utils.logging_setup
    try:
        from qsn.utils import setup_logger
    except Exception:
        try:
            from qsn.utils.logging_setup import setup_logger
        except Exception as e:
            print("Erro ao importar setup_logger (qsn.utils.*):", e)

    return {
        "RouterNetTopo": RouterNetTopo,
        "HubGHZActiveApp": HubGHZActiveApp,
        "SensorApp": SensorApp,
        "set_parameters": set_parameters,
        "CONFIG": CONFIG,
        "setup_logger": setup_logger,
    }


def main(hub_name: str = "Hub1", seed: Optional[int] = None):
    objs = try_imports()

    RouterNetTopo = objs["RouterNetTopo"]
    HubGHZActiveApp = objs["HubGHZActiveApp"]
    SensorApp = objs["SensorApp"]
    set_parameters = objs["set_parameters"]
    CONFIG = objs["CONFIG"]
    setup_logger = objs["setup_logger"]

    # Verificações iniciais
    if None in (RouterNetTopo, HubGHZActiveApp, SensorApp, set_parameters, CONFIG):
        print("Dependências essenciais ausentes. Verifique se o ambiente do projeto está corretamente instalado.")
        print("Itens faltando:")
        if RouterNetTopo is None:
            print(" - sequence.topology.router_net_topo.RouterNetTopo")
        if HubGHZActiveApp is None or SensorApp is None:
            print(" - qsn.app.ghz_active.HubGHZActiveApp / SensorApp")
        if set_parameters is None or CONFIG is None:
            print(" - qsn.parameters.set_parameters / CONFIG")
        sys.exit(1)

    # Opcional: semente para reprodutibilidade
    if seed is not None:
        random.seed(seed)

    # 1) Carrega a topologia
    network_file = CONFIG["simulacao"]["NETWORK_CONFIG_FILE"]
    print(f"Carregando a rede a partir de '{network_file}'...")
    network_topo = RouterNetTopo(network_file)
    tl = network_topo.get_timeline()
    print("Topologia da rede carregada.")

    # 2) Configura o logger
    if setup_logger is not None:
        print("Configurando o logger para a simulação (modo: custom)...")
        try:
            setup_logger(tl, CONFIG["simulacao"]["LOG_FILE_NAME"], mode="custom")
        except Exception as e:
            print("Falha ao configurar logger:", e)
    else:
        print("setup_logger não disponível; pulando configuração de logs.")

    # 3) Aplica parâmetros de hardware
    print("Aplicando parâmetros de hardware (memórias, detectores, etc.)...")
    try:
        set_parameters(network_topo)
        print("Parâmetros aplicados.")
    except Exception as e:
        print("Falha ao aplicar parâmetros:", e)

    # 4) Visualiza a estrutura lógica definida em CONFIG
    print("\nEstrutura Lógica da Rede:")
    for hub_info in CONFIG.get("hubs_config", []):
        hub = hub_info.get("name")
        print(f"└── Hub: {hub}")
        sensor_names = hub_info.get("sensors", [])
        for i, sensor_name in enumerate(sensor_names):
            if i == len(sensor_names) - 1:
                print(f"    └── Sensor: {sensor_name}")
            else:
                print(f"    ├── Sensor: {sensor_name}")

    # 5) Seleciona aleatoriamente 2 sensores para o hub alvo
    target_hub_name = hub_name
    hub_info = None
    for h_info in CONFIG.get("hubs_config", []):
        if h_info.get("name") == target_hub_name:
            hub_info = h_info
            break

    if not hub_info:
        print(f"Erro: Hub com o nome '{target_hub_name}' não encontrado na configuração.")
        sys.exit(1)

    possible_sensors = hub_info.get("sensors", [])
    if len(possible_sensors) < 2:
        print(f"Erro: O {target_hub_name} não tem pelo menos 2 sensores configurados.")
        sys.exit(1)

    selected_sensors = random.sample(possible_sensors, 2)
    print(f"Hub selecionado: {target_hub_name}")
    print(f"Sensores sorteados para o experimento: {selected_sensors[0]} e {selected_sensors[1]}")

    # 6) Instala as aplicações nos nós selecionados
    all_nodes = network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)
    node_map = {node.name: node for node in all_nodes}

    hub_node = node_map.get(target_hub_name)
    sensor_node1 = node_map.get(selected_sensors[0])
    sensor_node2 = node_map.get(selected_sensors[1])

    if not (hub_node and sensor_node1 and sensor_node2):
        print("Erro: Um ou mais nós selecionados não foram encontrados na topologia.")
        sys.exit(1)

    # Instala a App no Hub (informando os sensores selecionados)
    hub_app = HubGHZActiveApp(hub_node, selected_sensors,
                              CONFIG["simulacao"]["START_TIME"],
                              CONFIG["simulacao"]["END_TIME"],
                              CONFIG["circuito_quantico"]["operacoes"])
    hub_node.set_app(hub_app)
    print(f"Aplicação instalada no Hub: {hub_node.name}")

    # Instala as Apps nos Sensores
    sensor_app1 = SensorApp(sensor_node1)
    sensor_node1.set_app(sensor_app1)
    print(f"Aplicação instalada no Sensor: {sensor_node1.name}")

    sensor_app2 = SensorApp(sensor_node2)
    sensor_node2.set_app(sensor_app2)
    print(f"Aplicação instalada no Sensor: {sensor_node2.name}")

    # 7) Executa a simulação
    print(f"\nIniciando simulação focada entre {target_hub_name} e os sensores {selected_sensors}...")
    tl.init()
    hub_app.start()
    tl.run()

    print("\nSimulação focada concluída!")
    log_file = CONFIG["simulacao"]["LOG_FILE_NAME"]
    print(f"Verifique o arquivo '{log_file}.txt' para ver os detalhes da comunicação.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Executa o guia interativo de simulação (versão script).")
    parser.add_argument("--hub", "-H", default="Hub1", help="Nome do hub alvo (padrão: Hub1)")
    parser.add_argument("--seed", type=int, default=None, help="Semente aleatória para reprodutibilidade")
    args = parser.parse_args()
    main(hub_name=args.hub, seed=args.seed)
