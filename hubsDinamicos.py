"""
Script: hubsDinamicos.py

Objetivo
- Executar uma única simulação (um único timeline.run()) com 5 rodadas dinâmicas.
- A cada rodada, escolher 1 hub aleatoriamente (com reposição), usar TODOS os sensores dele,
  e uma janela de emaranhamento (entanglement_window) sorteada por rodada.
- Ao terminar a rodada (app.completed == True) iniciar a próxima, até completar 5.
- Sem tempo final fixo: a simulação para naturalmente quando a fila de eventos esvazia.

Observações
- Mantém mesma topologia GHZ ("chain").
- SensorApp é instalado uma única vez por sensor no início.
- HubGHZActiveApp é REINSTANCIADO a cada rodada. Para evitar conflito de nomes
  no nó Hub ("<Hub>-ghz-app"), removemos instâncias antigas com esse nome da lista
  owner.protocols antes de criar a nova.
- A orquestração é feita por um pequeno "heartbeat" agendado na timeline;
  não é um Controller formal, apenas funções/métodos auxiliares para dirigir as rodadas.

Uso rápido
- python hubsDinamicos.py --seed 123
- python hubsDinamicos.py --rounds 5 --seed 42

Requisitos
- sequence (SeQUeNCe) instalado
- qsn.app.ghz_active.HubGHZActiveApp e SensorApp
- net.json na raiz
"""
from __future__ import annotations

import argparse
import random
import sys
from typing import Dict, List, Optional, Tuple

from parameters_utils import set_parameters

# CONFIG local do script (pode ajustar se quiser)
CONFIG: Dict[str, object] = {
    "simulacao": {
        "NETWORK_CONFIG_FILE": "net.json",
        "LOG_FILE_NAME": "log",
        "START_TIME": 1e12,
    },
    # Hubs e sensores conhecidos pela topologia (ajuste para sua rede)
    "hubs_config": [
        {"name": "Hub1", "sensors": ["Sensor1H1", "Sensor2H1", "Sensor3H1", "Sensor4H1"]},
        {"name": "Hub2", "sensors": ["Sensor1H2", "Sensor2H2", "Sensor3H2", "Sensor4H2"]},
        {"name": "Hub3", "sensors": ["Sensor1H3", "Sensor2H3", "Sensor3H3", "Sensor4H3"]},
    ],
    # Parâmetros de hardware (delegado para set_parameters)
    "hardware": {
        "memoria": {"FREQ": 2e3, "EXPIRE": 1, "EFFICIENCY": 1, "FIDELITY": 0.93},
        "swapping": {"SUCC_PROB": 0.64, "DEGRADATION": 0.99},
        "detector": {"EFFICIENCY": 0.9, "COUNT_RATE": 5e7, "RESOLUTION": 100},
        "canal_quantico": {"ATTENUATION": 0.0002},
    },
    # Circuito a aplicar (sempre igual em todas as rodadas)
    "circuito_quantico": {
        "operacoes": [
            ("X", 0),
            ("X", 1),
            ("X", 2),
            ("X", 3),
        ]
    },
    # Faixa de amostragem da janela por rodada (ajuste como preferir)
    "dinamica": {
        "WINDOW_MIN": 0.5e12,
        "WINDOW_MAX": 2.0e12,
        "TICK_INTERVAL": 1e9,  # passo do heartbeat (ps)
        "LEAD_TIME": 5e10,      # tempo de margem antes do start_time de cada rodada (ps)
    },
}


def try_imports():
    RouterNetTopo = None
    HubGHZActiveApp = None
    SensorApp = None
    setup_logger = None
    Event = None
    Process = None

    try:
        from sequence.topology.router_net_topo import RouterNetTopo  # type: ignore
    except Exception as e:
        print("Erro ao importar RouterNetTopo (sequence.topology.router_net_topo):", e)

    try:
        from qsn.app.ghz_active import HubGHZActiveApp, SensorApp  # type: ignore
    except Exception as e:
        print("Erro ao importar aplicações GHZ (qsn.app.ghz_active):", e)

    try:
        from qsn.utils import setup_logger  # type: ignore
    except Exception:
        try:
            from qsn.utils.logging_setup import setup_logger  # type: ignore
        except Exception as e:
            print("Erro ao importar setup_logger (qsn.utils.*):", e)

    try:
        from sequence.kernel.event import Event  # type: ignore
        from sequence.kernel.process import Process  # type: ignore
    except Exception as e:
        print("Erro ao importar Event/Process (sequence.kernel.*):", e)

    return {
        "RouterNetTopo": RouterNetTopo,
        "HubGHZActiveApp": HubGHZActiveApp,
        "SensorApp": SensorApp,
        "setup_logger": setup_logger,
        "Event": Event,
        "Process": Process,
    }


# ----------------------
# Utilitários do script
# ----------------------

def _schedule_event_compat(tl, ev):
    """Agendamento compatível com diferentes versões da Timeline do SeQUeNCe.

    Tenta múltiplas assinaturas conhecidas para inserir um Event na timeline.
    """
    # Tenta métodos diretos na Timeline
    for name in ("schedule_event", "scheduleEvent", "schedule", "add_event", "addEvent"):
        m = getattr(tl, name, None)
        if callable(m):
            return m(ev)

    # Tenta objetos internos comuns que mantêm a fila de eventos
    for attr in ("scheduler", "events", "event_queue", "queue"):
        obj = getattr(tl, attr, None)
        if obj is None:
            continue
        for mname in ("schedule_event", "schedule", "push", "put", "add", "add_event"):
            mm = getattr(obj, mname, None)
            if callable(mm):
                return mm(ev)

    raise AttributeError(
        "Não foi possível agendar evento: Timeline não expõe método conhecido (ex.: schedule_event)."
    )

def build_node_maps(network_topo, RouterNetTopo):
    all_nodes = network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)
    node_map = {node.name: node for node in all_nodes}
    return node_map


def resolve_hub_and_sensors(node_map, hub_info: Dict[str, object]):
    hub_node = node_map.get(hub_info["name"])  # type: ignore
    sensor_nodes = []
    for s_name in hub_info.get("sensors", []):  # type: ignore
        n = node_map.get(s_name)
        if n is None:
            print(f"Aviso: Sensor '{s_name}' não encontrado na topologia. Será ignorado.")
        else:
            sensor_nodes.append(n)
    return hub_node, sensor_nodes


def install_sensor_apps(SensorApp, sensor_nodes):
    for s_node in sensor_nodes:
        # Evita reinstalar se já houver app com esse nome
        expected_name = f"{s_node.name}-ghz-app"
        already = False
        try:
            for p in getattr(s_node, "protocols", []):
                if getattr(p, "name", None) == expected_name:
                    already = True
                    break
        except Exception:
            pass
        if not already:
            s_app = SensorApp(s_node)
            s_node.set_app(s_app)


class Heartbeat:
    """Pequeno orquestrador baseado em eventos da timeline.

    Não é um Controller formal, apenas um "tick" que checa o estado e inicia rondas.
    """

    def __init__(self, tl, Event, Process, *,
                 hubs_info: List[Dict[str, object]],
                 node_map: Dict[str, object],
                 HubGHZActiveApp,
                 quantum_ops: List[Tuple[str, int]],
                 ghz_topology: str,
                 max_rounds: int,
                 tick_interval: float,
                 start_time: float,
                 window_min: float,
                 window_max: float,
                 lead_time: float,
                 seed: Optional[int] = None):
        self.tl = tl
        self.Event = Event
        self.Process = Process
        self.hubs_info = hubs_info
        self.node_map = node_map
        self.HubGHZActiveApp = HubGHZActiveApp
        self.quantum_ops = quantum_ops
        self.ghz_topology = ghz_topology
        self.max_rounds = max_rounds
        self.tick_interval = tick_interval
        self.start_time = start_time
        self.window_min = window_min
        self.window_max = window_max
        self.lead_time = lead_time
        self.rng = random.Random(seed)

        self.current_app = None
        self.current_hub_name = None
        self.round_idx = 0

    # ---- funções auxiliares ----
    def _choose_random_hub(self):
        hub_info = self.rng.choice(self.hubs_info)
        hub_node, sensor_nodes = resolve_hub_and_sensors(self.node_map, hub_info)
        if not hub_node or not sensor_nodes:
            return None, []
        return hub_node, sensor_nodes

    def _sample_window(self) -> float:
        return self.rng.uniform(self.window_min, self.window_max)

    def _cleanup_old_hub_protocol(self, hub_node):
        """Remove protocolos antigos com o mesmo nome do hub-app."""
        try:
            expected_name = f"{hub_node.name}-ghz-app"
            if hasattr(hub_node, "protocols"):
                hub_node.protocols = [p for p in hub_node.protocols if getattr(p, "name", None) != expected_name]
        except Exception:
            pass

    def _start_round(self):
        hub_node, sensor_nodes = self._choose_random_hub()
        if not hub_node or not sensor_nodes:
            # não encontrou nada válido; reagendar um tick para tentar de novo
            self._schedule_next_tick()
            return

        window = self._sample_window()
        # Definimos um start_time no futuro para respeitar a checagem do Reservation
        # (assert now() < start_time) mesmo após latências de mensagens.
        start_t = self.tl.now() + self.lead_time

        # limpa protocolos antigos c/ mesmo nome
        self._cleanup_old_hub_protocol(hub_node)

        # cria app novo
        hub_app = self.HubGHZActiveApp(
            hub_node,
            [n.name for n in sensor_nodes],
            start_t,
            entanglement_window=window,
            quantum_circuit_operations=self.quantum_ops,
            append_ghz=True,
            ghz_topology=self.ghz_topology,
        )
        hub_node.set_app(hub_app)
        hub_app.start()

        self.current_app = hub_app
        self.current_hub_name = hub_node.name

        # agenda próximo tick
        self._schedule_next_tick()

    def _schedule_next_tick(self):
        t_next = max(self.tl.now(), self.start_time) + self.tick_interval
        ev = self.Event(t_next, self.Process(self, "tick", []))
        _schedule_event_compat(self.tl, ev)

    # ---- API pública ----
    def start(self):
        # agenda o primeiro tick na START_TIME
        ev = self.Event(self.start_time, self.Process(self, "tick", []))
        _schedule_event_compat(self.tl, ev)

    def tick(self):
        # Se já completamos todas as rodadas, não faz mais nada
        if self.round_idx >= self.max_rounds:
            return

        # Se não há rodada em curso, inicia uma
        if self.current_app is None:
            self._start_round()
            return

        # Se a rodada atual completou, avança o contador e prepara a próxima
        if getattr(self.current_app, "completed", False):
            self.round_idx += 1
            # limpar referência do app atual
            self.current_app = None
            self.current_hub_name = None

            # se atingimos o limite, não agenda próximo tick (deixa a timeline esvaziar)
            if self.round_idx >= self.max_rounds:
                return

            # caso contrário, agenda tick para iniciar a próxima
            self._schedule_next_tick()
        else:
            # ainda não completou; segue checando periodicamente
            self._schedule_next_tick()


# ----------------------
# Entrada principal
# ----------------------

def main(seed: Optional[int], rounds: int):
    objs = try_imports()
    RouterNetTopo = objs["RouterNetTopo"]
    HubGHZActiveApp = objs["HubGHZActiveApp"]
    SensorApp = objs["SensorApp"]
    setup_logger = objs["setup_logger"]
    Event = objs["Event"]
    Process = objs["Process"]

    if None in (RouterNetTopo, HubGHZActiveApp, SensorApp, Event, Process):
        print("Dependências essenciais ausentes. Verifique o ambiente do projeto.")
        if RouterNetTopo is None:
            print(" - sequence.topology.router_net_topo.RouterNetTopo")
        if HubGHZActiveApp is None or SensorApp is None:
            print(" - qsn.app.ghz_active.HubGHZActiveApp / SensorApp")
        if Event is None or Process is None:
            print(" - sequence.kernel.event.Event / sequence.kernel.process.Process")
        sys.exit(1)

    # Cria topologia e timeline
    network_file = CONFIG["simulacao"]["NETWORK_CONFIG_FILE"]
    print(f"Carregando a rede a partir de '{network_file}'...")
    network_topo = RouterNetTopo(network_file)
    tl = network_topo.get_timeline()
    print("Topologia da rede carregada.")

    # Logger
    if setup_logger is not None:
        try:
            setup_logger(tl, CONFIG["simulacao"]["LOG_FILE_NAME"], mode="custom")
        except Exception as e:
            print("Falha ao configurar logger:", e)

    # Parâmetros de hardware
    try:
        set_parameters(network_topo, config=CONFIG)
    except Exception as e:
        print("Falha ao aplicar parâmetros:", e)

    # Mapeamento de nós
    node_map = build_node_maps(network_topo, RouterNetTopo)

    # Prepara lista de hubs válidos e instala SensorApps (uma vez por sensor)
    valid_hubs: List[Dict[str, object]] = []
    all_sensor_nodes = []
    for hub_info in CONFIG.get("hubs_config", []):
        hub_node, sensor_nodes = resolve_hub_and_sensors(node_map, hub_info)
        if hub_node and sensor_nodes:
            valid_hubs.append(hub_info)
            all_sensor_nodes.extend(sensor_nodes)
        else:
            print(f"Aviso: Hub '{hub_info.get('name')}' ignorado por falta de mapeamento ou sensores válidos.")

    if not valid_hubs:
        print("Erro: Nenhum hub válido foi encontrado na topologia com base em CONFIG.hubs_config.")
        sys.exit(1)

    # Instala SensorApp em todos os sensores (sem duplicar)
    install_sensor_apps(SensorApp, list(set(all_sensor_nodes)))

    # Inicializa timeline
    print("Inicializando timeline...")
    tl.init()

    # Cria heartbeat simples que controla as rodadas
    hb = Heartbeat(
        tl,
        Event,
        Process,
        hubs_info=valid_hubs,
        node_map=node_map,
        HubGHZActiveApp=HubGHZActiveApp,
        quantum_ops=CONFIG["circuito_quantico"]["operacoes"],
        ghz_topology="chain",
        max_rounds=rounds,
        tick_interval=CONFIG["dinamica"]["TICK_INTERVAL"],
        start_time=CONFIG["simulacao"]["START_TIME"],
        window_min=CONFIG["dinamica"]["WINDOW_MIN"],
        window_max=CONFIG["dinamica"]["WINDOW_MAX"],
        lead_time=CONFIG["dinamica"]["LEAD_TIME"],
        seed=seed,
    )

    # Agenda o primeiro tick
    hb.start()

    # Roda a simulação até a fila esvaziar
    print("Iniciando simulação com rodadas dinâmicas...")
    tl.run()

    print("\nSimulação concluída!")
    log_file = CONFIG["simulacao"]["LOG_FILE_NAME"]
    print(f"Verifique o arquivo '{log_file}.txt' para os detalhes.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulação dinâmica com 5 rodadas e um único run().")
    parser.add_argument("--seed", type=int, default=None, help="Semente para reprodutibilidade da escolha de hubs e janelas")
    parser.add_argument("--rounds", type=int, default=5, help="Número de rodadas (padrão: 5)")
    args = parser.parse_args()

    main(seed=args.seed, rounds=args.rounds)
