"""
Script: validacao_topologias.py

Objetivo
--------
Comparar a latencia de agregacao de dados entre duas topologias de rede quantica:
  1. Centralizada (Hub Unico): todos os N sensores conectados a um unico Hub.
  2. Distribuida (Multiplos Hubs): N sensores particionados em K clusters, cada um
     conectado a um Hub intermediario, que reporta a um Hub agregador principal.

Ambas as simulacoes usam o mesmo numero de sensores (N), mesmas distancias de enlace
e mesmos parametros de hardware. Ao final, exporta um CSV com as latencias.

Uso
---
  python validacao_topologias.py
  python validacao_topologias.py --sensors 12 --hubs 3 --seed 42
  python validacao_topologias.py -N 8 -K 2 --output resultado.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
from enum import Enum, auto
from itertools import combinations
from typing import Any, Dict, List, Optional, Tuple

from parameters_utils import set_parameters

# ---------------------------------------------------------------------------
# CONFIG local do script
# ---------------------------------------------------------------------------
CONFIG: Dict[str, Any] = {
    "simulacao": {
        "START_TIME": 1e12,
        "ENTANGLEMENT_WINDOW": 2e12,
        "LOG_FILE_NAME": "validacao_log",
    },
    "hardware": {
        "memoria": {"FREQ": 2e3, "EXPIRE": 0, "EFFICIENCY": 1, "FIDELITY": 0.93},
        "swapping": {"SUCC_PROB": 0.64, "DEGRADATION": 0.99},
        "detector": {"EFFICIENCY": 0.9, "COUNT_RATE": 5e7, "RESOLUTION": 100},
        "canal_quantico": {"ATTENUATION": 0.0002},
    },
    "dinamica": {
        "TICK_INTERVAL": 1e9,
    },
}

# ---------------------------------------------------------------------------
# Importacao segura de dependencias
# ---------------------------------------------------------------------------

def try_imports():
    """Importa modulos com tratamento de erro, seguindo o padrao de hubsDinamicos.py."""
    RouterNetTopo = None
    HubGHZActiveApp = None
    SensorApp = None
    setup_logger = None
    Event = None
    Process = None
    Message = None
    Protocol = None

    try:
        from sequence.topology.router_net_topo import RouterNetTopo
    except Exception as e:
        print("Erro ao importar RouterNetTopo:", e)

    try:
        from qsn.app.ghz_active import HubGHZActiveApp, SensorApp
    except Exception as e:
        print("Erro ao importar HubGHZActiveApp/SensorApp:", e)

    try:
        from qsn.utils import setup_logger
    except Exception:
        try:
            from qsn.utils.logging_setup import setup_logger
        except Exception as e:
            print("Erro ao importar setup_logger:", e)

    try:
        from sequence.kernel.event import Event
        from sequence.kernel.process import Process
    except Exception as e:
        print("Erro ao importar Event/Process:", e)

    try:
        from sequence.message import Message
    except Exception as e:
        print("Erro ao importar Message:", e)

    try:
        from sequence.protocol import Protocol
    except Exception as e:
        print("Erro ao importar Protocol:", e)

    return {
        "RouterNetTopo": RouterNetTopo,
        "HubGHZActiveApp": HubGHZActiveApp,
        "SensorApp": SensorApp,
        "setup_logger": setup_logger,
        "Event": Event,
        "Process": Process,
        "Message": Message,
        "Protocol": Protocol,
    }


# ---------------------------------------------------------------------------
# Utilitarios (baseados em hubsDinamicos.py)
# ---------------------------------------------------------------------------

def _schedule_event_compat(tl, ev):
    """Agendamento compativel com diferentes versoes da Timeline do SeQUeNCe."""
    for name in ("schedule_event", "scheduleEvent", "schedule", "add_event", "addEvent"):
        m = getattr(tl, name, None)
        if callable(m):
            return m(ev)

    for attr in ("scheduler", "events", "event_queue", "queue"):
        obj = getattr(tl, attr, None)
        if obj is None:
            continue
        for mname in ("schedule_event", "schedule", "push", "put", "add", "add_event"):
            mm = getattr(obj, mname, None)
            if callable(mm):
                return mm(ev)

    raise AttributeError(
        "Nao foi possivel agendar evento: Timeline nao expoe metodo conhecido."
    )


def build_node_maps(network_topo, RouterNetTopo):
    all_nodes = network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)
    return {node.name: node for node in all_nodes}


def install_sensor_apps(SensorApp, sensor_nodes):
    """Instala SensorApp em cada sensor, evitando duplicacao."""
    for s_node in sensor_nodes:
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


# ---------------------------------------------------------------------------
# Mensagem de agregacao (hub intermediario -> agregador)
# ---------------------------------------------------------------------------

class AggregationMessageType(Enum):
    RESULT_REPORT = auto()


def _create_aggregation_message_class(MessageBase):
    """Cria a classe AggregationMessage dinamicamente com a classe Message correta."""

    class AggregationMessage(MessageBase):
        def __init__(self, msg_type, receiver, **kwargs):
            super().__init__(msg_type, receiver)
            if msg_type is AggregationMessageType.RESULT_REPORT:
                self.hub_name = kwargs.get("hub_name")
                self.outcomes = kwargs.get("outcomes", [])

    return AggregationMessage


# ---------------------------------------------------------------------------
# ForwardingHubApp: subclasse de HubGHZActiveApp com encaminhamento
# ---------------------------------------------------------------------------

def _create_timed_hub_class(HubGHZActiveApp):
    """Cria TimedHubApp: subclasse que registra completion_time preciso."""

    class TimedHubApp(HubGHZActiveApp):
        """Hub que registra o timestamp exato de conclusao da medicao."""

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.completion_time = None

        def get_memory(self, info):
            super().get_memory(info)
            if self.completed and self.completion_time is None:
                self.completion_time = self.owner.timeline.now()

    return TimedHubApp


def _create_forwarding_hub_class(HubGHZActiveApp, AggregationMessage):
    """Cria ForwardingHubApp dinamicamente para evitar imports no topo."""

    class ForwardingHubApp(HubGHZActiveApp):
        """Hub que, apos completar medicao conjunta, envia resultado ao agregador."""

        def __init__(self, owner, sensors_to_monitor, start_time,
                     aggregator_name,
                     entanglement_window=2e12,
                     quantum_circuit_operations=None,
                     append_ghz=False, ghz_topology="chain"):
            super().__init__(
                owner, sensors_to_monitor, start_time,
                entanglement_window=entanglement_window,
                quantum_circuit_operations=quantum_circuit_operations,
                append_ghz=append_ghz,
                ghz_topology=ghz_topology,
            )
            self.aggregator_name = aggregator_name
            self.aggregator_app_name = f"{aggregator_name}-aggregator-app"
            self._forwarded = False
            self.completion_time = None

        def get_memory(self, info):
            """Apos processar memoria, encaminha resultado ao agregador se completou."""
            super().get_memory(info)
            if self.completed and not self._forwarded:
                self._forwarded = True
                self.completion_time = self.owner.timeline.now()
                msg = AggregationMessage(
                    msg_type=AggregationMessageType.RESULT_REPORT,
                    receiver=self.aggregator_app_name,
                    hub_name=self.owner.name,
                    outcomes=[],
                )
                self.owner.send_message(self.aggregator_name, msg)

    return ForwardingHubApp


# ---------------------------------------------------------------------------
# AggregatorApp: protocolo do no agregador
# ---------------------------------------------------------------------------

def _create_aggregator_app_class(ProtocolBase):
    """Cria AggregatorApp dinamicamente."""

    class AggregatorApp(ProtocolBase):
        """Protocolo que coleta resultados de hubs intermediarios."""

        def __init__(self, owner, expected_hub_names):
            name = f"{owner.name}-aggregator-app"
            super().__init__(owner, name)
            self.owner.protocols.append(self)
            self.expected_hubs = set(expected_hub_names)
            self.received_from = set()
            self.completed = False
            self.completion_time = None

        def received_message(self, src, msg):
            if msg.msg_type == AggregationMessageType.RESULT_REPORT:
                self.received_from.add(msg.hub_name)
                if self.received_from >= self.expected_hubs:
                    self.completed = True
                    self.completion_time = self.owner.timeline.now()

        def start(self):
            pass

        def get_other_reservation(self, reservation):
            pass

        def get_reservation_result(self, reservation, result):
            pass

    return AggregatorApp


# ---------------------------------------------------------------------------
# ValidationHeartbeat: monitora conclusao de apps
# ---------------------------------------------------------------------------

class ValidationHeartbeat:
    """Monitora uma lista de apps e registra t_end quando todos completam."""

    def __init__(self, tl, Event, Process, *,
                 apps_to_monitor,
                 tick_interval=1e9,
                 start_time=1e12):
        self.tl = tl
        self.Event = Event
        self.Process = Process
        self.apps = apps_to_monitor
        self.tick_interval = tick_interval
        self.start_time = start_time
        self.t_end = None
        self.done = False

    def start(self):
        ev = self.Event(self.start_time, self.Process(self, "tick", []))
        _schedule_event_compat(self.tl, ev)

    def tick(self):
        if self.done:
            return
        all_done = all(getattr(app, "completed", False) for app in self.apps)
        if all_done:
            self.t_end = self.tl.now()
            self.done = True
            return
        t_next = self.tl.now() + self.tick_interval
        ev = self.Event(t_next, self.Process(self, "tick", []))
        _schedule_event_compat(self.tl, ev)


# ---------------------------------------------------------------------------
# Geracao de topologias JSON
# ---------------------------------------------------------------------------

def _full_mesh_cconnections(node_names: List[str], delay: int = 100000000) -> List[dict]:
    """Gera conexoes classicas em malha completa."""
    conns = []
    for n1, n2 in combinations(node_names, 2):
        conns.append({"node1": n1, "node2": n2, "delay": delay})
    return conns


def generate_centralized_topology(
    n_sensors: int,
    filepath: str,
    sensor_hub_distance: int = 10,
    attenuation: float = 0.0002,
    stop_time: float = 10e12,
) -> Tuple[str, List[str]]:
    """Gera topologia centralizada: 1 Hub + N sensores.

    Returns:
        (hub_name, sensor_names)
    """
    hub_name = "CentralHub"
    sensor_names = [f"Sensor{i+1}" for i in range(n_sensors)]

    nodes = [
        {"name": hub_name, "type": "QuantumRouter", "seed": 0,
         "memo_size": max(100, n_sensors * 5)},
    ]
    for i, sname in enumerate(sensor_names):
        nodes.append({
            "name": sname, "type": "QuantumRouter",
            "seed": i + 1, "memo_size": 20,
        })

    qconnections = []
    for sname in sensor_names:
        qconnections.append({
            "node1": sname, "node2": hub_name,
            "distance": sensor_hub_distance,
            "attenuation": attenuation,
            "type": "meet_in_the_middle",
        })

    all_node_names = [hub_name] + sensor_names
    cconnections = _full_mesh_cconnections(all_node_names)

    topo = {
        "nodes": nodes,
        "qconnections": qconnections,
        "cconnections": cconnections,
        "stop_time": stop_time,
        "is_parallel": False,
    }

    with open(filepath, "w") as f:
        json.dump(topo, f, indent=2)

    return hub_name, sensor_names


def generate_distributed_topology(
    n_sensors: int,
    n_hubs: int,
    filepath: str,
    sensor_hub_distance: int = 10,
    hub_aggregator_distance: int = 50,
    attenuation: float = 0.0002,
    stop_time: float = 10e12,
) -> Tuple[str, List[str], Dict[str, List[str]]]:
    """Gera topologia distribuida: 1 Agregador + K Hubs + N sensores.

    Returns:
        (aggregator_name, hub_names, hub_sensor_map)
    """
    aggregator_name = "Aggregator"
    hub_names = [f"IntHub{i+1}" for i in range(n_hubs)]
    sensor_names = [f"Sensor{i+1}" for i in range(n_sensors)]

    # Particionar sensores igualmente entre hubs
    hub_sensor_map: Dict[str, List[str]] = {h: [] for h in hub_names}
    for i, sname in enumerate(sensor_names):
        hub_idx = i % n_hubs
        hub_sensor_map[hub_names[hub_idx]].append(sname)

    # Nodes
    seed_counter = 0
    nodes = [
        {"name": aggregator_name, "type": "QuantumRouter",
         "seed": seed_counter, "memo_size": 100},
    ]
    seed_counter += 1

    sensors_per_hub = math.ceil(n_sensors / n_hubs)
    for hname in hub_names:
        nodes.append({
            "name": hname, "type": "QuantumRouter",
            "seed": seed_counter,
            "memo_size": max(100, sensors_per_hub * 5),
        })
        seed_counter += 1

    for sname in sensor_names:
        nodes.append({
            "name": sname, "type": "QuantumRouter",
            "seed": seed_counter, "memo_size": 20,
        })
        seed_counter += 1

    # Quantum connections
    qconnections = []
    # Sensor <-> IntHub
    for hname, sensors in hub_sensor_map.items():
        for sname in sensors:
            qconnections.append({
                "node1": sname, "node2": hname,
                "distance": sensor_hub_distance,
                "attenuation": attenuation,
                "type": "meet_in_the_middle",
            })
    # IntHub <-> Aggregator
    for hname in hub_names:
        qconnections.append({
            "node1": hname, "node2": aggregator_name,
            "distance": hub_aggregator_distance,
            "attenuation": attenuation,
            "type": "meet_in_the_middle",
        })
    # IntHub <-> IntHub
    for h1, h2 in combinations(hub_names, 2):
        qconnections.append({
            "node1": h1, "node2": h2,
            "distance": hub_aggregator_distance,
            "attenuation": attenuation,
            "type": "meet_in_the_middle",
        })

    # Classical connections (malha completa)
    all_node_names = [aggregator_name] + hub_names + sensor_names
    cconnections = _full_mesh_cconnections(all_node_names)

    topo = {
        "nodes": nodes,
        "qconnections": qconnections,
        "cconnections": cconnections,
        "stop_time": stop_time,
        "is_parallel": False,
    }

    with open(filepath, "w") as f:
        json.dump(topo, f, indent=2)

    return aggregator_name, hub_names, hub_sensor_map


# ---------------------------------------------------------------------------
# Funcoes de simulacao
# ---------------------------------------------------------------------------

def run_centralized(n_sensors: int, config: Dict, objs: Dict) -> Dict[str, Any]:
    """Executa simulacao com topologia centralizada (1 Hub + N sensores)."""
    RouterNetTopo = objs["RouterNetTopo"]
    HubGHZActiveApp = objs["HubGHZActiveApp"]
    SensorApp = objs["SensorApp"]
    setup_logger = objs["setup_logger"]
    Event = objs["Event"]
    Process = objs["Process"]

    TimedHubApp = _create_timed_hub_class(HubGHZActiveApp)

    topo_file = "_topo_centralized.json"
    try:
        hub_name, sensor_names = generate_centralized_topology(n_sensors, topo_file)

        network_topo = RouterNetTopo(topo_file)
        tl = network_topo.get_timeline()

        if setup_logger is not None:
            try:
                setup_logger(tl, config["simulacao"]["LOG_FILE_NAME"] + "_central", mode="custom")
            except Exception:
                pass

        set_parameters(network_topo, config=config)
        node_map = build_node_maps(network_topo, RouterNetTopo)

        # Instalar SensorApps
        sensor_nodes = [node_map[s] for s in sensor_names if s in node_map]
        install_sensor_apps(SensorApp, sensor_nodes)

        # Instalar TimedHubApp no hub central (registra completion_time preciso)
        hub_node = node_map[hub_name]
        start_time = config["simulacao"]["START_TIME"]
        ent_window = config["simulacao"]["ENTANGLEMENT_WINDOW"]

        hub_app = TimedHubApp(
            hub_node, sensor_names, start_time,
            entanglement_window=ent_window,
            quantum_circuit_operations=[],
            append_ghz=True,
            ghz_topology="chain",
        )
        hub_node.set_app(hub_app)

        # Heartbeat para manter timeline ativa ate conclusao
        heartbeat = ValidationHeartbeat(
            tl, Event, Process,
            apps_to_monitor=[hub_app],
            tick_interval=config["dinamica"]["TICK_INTERVAL"],
            start_time=start_time,
        )

        tl.init()
        hub_app.start()
        heartbeat.start()
        tl.run()

        t_start = start_time
        # Usar completion_time preciso do app; fallback para heartbeat.t_end
        t_end = hub_app.completion_time if hub_app.completion_time is not None else heartbeat.t_end
        latency = (t_end - t_start) if t_end is not None else None

        if latency is None:
            print("  AVISO: Simulacao centralizada nao completou dentro do stop_time.")

        return {
            "topology": "centralized",
            "n_sensors": n_sensors,
            "n_hubs": 1,
            "t_start_ps": t_start,
            "t_end_ps": t_end,
            "latency_ps": latency,
        }
    finally:
        if os.path.exists(topo_file):
            os.remove(topo_file)


def run_distributed(n_sensors: int, n_hubs: int, config: Dict, objs: Dict) -> Dict[str, Any]:
    """Executa simulacao com topologia distribuida (K Hubs + 1 Agregador)."""
    RouterNetTopo = objs["RouterNetTopo"]
    HubGHZActiveApp = objs["HubGHZActiveApp"]
    SensorApp = objs["SensorApp"]
    setup_logger = objs["setup_logger"]
    Event = objs["Event"]
    Process = objs["Process"]
    Message = objs["Message"]
    Protocol = objs["Protocol"]

    # Criar classes dinamicas
    AggregationMessage = _create_aggregation_message_class(Message)
    ForwardingHubApp = _create_forwarding_hub_class(HubGHZActiveApp, AggregationMessage)
    AggregatorApp = _create_aggregator_app_class(Protocol)

    topo_file = "_topo_distributed.json"
    try:
        aggregator_name, hub_names, hub_sensor_map = generate_distributed_topology(
            n_sensors, n_hubs, topo_file
        )

        network_topo = RouterNetTopo(topo_file)
        tl = network_topo.get_timeline()

        if setup_logger is not None:
            try:
                setup_logger(tl, config["simulacao"]["LOG_FILE_NAME"] + "_distrib", mode="custom")
            except Exception:
                pass

        set_parameters(network_topo, config=config)
        node_map = build_node_maps(network_topo, RouterNetTopo)

        # Instalar SensorApps em todos os sensores
        all_sensor_names = [s for sensors in hub_sensor_map.values() for s in sensors]
        sensor_nodes = [node_map[s] for s in all_sensor_names if s in node_map]
        install_sensor_apps(SensorApp, sensor_nodes)

        # Instalar AggregatorApp no no agregador
        agg_node = node_map[aggregator_name]
        agg_app = AggregatorApp(agg_node, hub_names)
        agg_node.set_app(agg_app)

        # Instalar ForwardingHubApp em cada hub intermediario
        start_time = config["simulacao"]["START_TIME"]
        ent_window = config["simulacao"]["ENTANGLEMENT_WINDOW"]
        hub_apps = []

        for hname in hub_names:
            hub_node = node_map[hname]
            sensors = hub_sensor_map[hname]

            hub_app = ForwardingHubApp(
                hub_node, sensors, start_time,
                aggregator_name=aggregator_name,
                entanglement_window=ent_window,
                quantum_circuit_operations=[],
                append_ghz=True,
                ghz_topology="chain",
            )
            hub_node.set_app(hub_app)
            hub_apps.append(hub_app)

        # Heartbeat monitorando o agregador
        heartbeat = ValidationHeartbeat(
            tl, Event, Process,
            apps_to_monitor=[agg_app],
            tick_interval=config["dinamica"]["TICK_INTERVAL"],
            start_time=start_time,
        )

        tl.init()
        for hub_app in hub_apps:
            hub_app.start()
        heartbeat.start()
        tl.run()

        t_start = start_time
        # Usar completion_time preciso do agregador; fallback para heartbeat.t_end
        t_end = agg_app.completion_time if agg_app.completion_time is not None else heartbeat.t_end
        latency = (t_end - t_start) if t_end is not None else None

        if latency is None:
            print("  AVISO: Simulacao distribuida nao completou dentro do stop_time.")

        return {
            "topology": "distributed",
            "n_sensors": n_sensors,
            "n_hubs": n_hubs,
            "t_start_ps": t_start,
            "t_end_ps": t_end,
            "latency_ps": latency,
        }
    finally:
        if os.path.exists(topo_file):
            os.remove(topo_file)


# ---------------------------------------------------------------------------
# Exportacao CSV
# ---------------------------------------------------------------------------

def write_results_csv(results: List[Dict], filepath: str = "validacao_resultados.csv"):
    """Escreve resultados de latencia em arquivo CSV."""
    fieldnames = ["topology", "n_sensors", "n_hubs", "t_start_ps", "t_end_ps", "latency_ps"]
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r)


def _get_vary_n_values() -> List[int]:
    """Retorna a sequencia de valores de N para varredura: 1-5 e 10 a 100 de 10 em 10."""
    return list(range(1, 6)) + list(range(10, 101, 10))


def _run_single_pair(n: int, k: int, objs: Dict) -> Tuple[Dict, Dict]:
    """Executa centralizada + distribuida para um dado N e K efetivo."""
    k_eff = min(k, n)  # Nao pode ter mais hubs que sensores
    c = run_centralized(n, CONFIG, objs)
    d = run_distributed(n, k_eff, CONFIG, objs)
    return c, d


def _fmt_lat(lat) -> str:
    return f"{lat:.0f}" if lat is not None else "N/A"


def _print_summary_table(all_results: List[Dict]):
    """Imprime tabela comparativa de latencias."""
    print("\n" + "=" * 72)
    print(f"{'N':>5}  {'K_distrib':>9}  {'Lat. Central (ps)':>20}  {'Lat. Distrib. (ps)':>20}")
    print("-" * 72)
    rows_central = {r["n_sensors"]: r for r in all_results if r["topology"] == "centralized"}
    rows_distrib = {r["n_sensors"]: r for r in all_results if r["topology"] == "distributed"}
    for n in sorted(rows_central.keys()):
        rc = rows_central[n]
        rd = rows_distrib.get(n)
        lat_c = _fmt_lat(rc["latency_ps"])
        lat_d = _fmt_lat(rd["latency_ps"]) if rd else "N/A"
        k_d = rd["n_hubs"] if rd else "-"
        print(f"{n:>5}  {k_d:>9}  {lat_c:>20}  {lat_d:>20}")
    print("=" * 72)


# ---------------------------------------------------------------------------
# Funcao principal
# ---------------------------------------------------------------------------

def main(n_sensors: int = 12, n_hubs: int = 3, seed: Optional[int] = None,
         output: str = "validacao_resultados.csv", vary_n: bool = False):
    objs = try_imports()

    essenciais = ["RouterNetTopo", "HubGHZActiveApp", "SensorApp", "Event",
                  "Process", "Message", "Protocol"]
    faltando = [k for k in essenciais if objs.get(k) is None]
    if faltando:
        print("Dependencias essenciais ausentes:")
        for k in faltando:
            print(f"  - {k}")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Modo vary-n: varre N = [1..5, 10, 20, ..., 100]
    # ------------------------------------------------------------------
    if vary_n:
        n_values = _get_vary_n_values()
        print("=" * 60)
        print(f"Varredura de N: {n_values}")
        print(f"K (hubs distribuidos): {n_hubs} (reduzido automaticamente se N < K)")
        print("=" * 60)

        all_results: List[Dict] = []
        total = len(n_values)
        for idx, n in enumerate(n_values, 1):
            k_eff = min(n_hubs, n)
            print(f"\n[{idx}/{total}] N={n}, K_eff={k_eff}")
            print(f"  Centralizada...", end=" ", flush=True)
            c = run_centralized(n, CONFIG, objs)
            print(_fmt_lat(c["latency_ps"]) + " ps")
            print(f"  Distribuida ({k_eff} hubs)...", end=" ", flush=True)
            d = run_distributed(n, k_eff, CONFIG, objs)
            print(_fmt_lat(d["latency_ps"]) + " ps")
            all_results.extend([c, d])

        write_results_csv(all_results, output)
        print(f"\nResultados exportados para '{output}'")
        _print_summary_table(all_results)
        return

    # ------------------------------------------------------------------
    # Modo padrao: N e K fixos
    # ------------------------------------------------------------------
    if n_sensors < n_hubs:
        print(f"Erro: n_sensors ({n_sensors}) deve ser >= n_hubs ({n_hubs})")
        sys.exit(1)

    if n_sensors % n_hubs != 0:
        print(f"Aviso: {n_sensors} sensores nao sao divisiveis igualmente por {n_hubs} hubs.")
        print(f"  A distribuicao sera aproximada (round-robin).")

    print("=" * 60)
    print(f"Validacao de Topologias: {n_sensors} sensores, {n_hubs} hubs")
    print("=" * 60)

    # --- Cenario 1: Centralizada ---
    print(f"\n[1/2] Simulacao CENTRALIZADA (Hub Unico, {n_sensors} sensores)...")
    centralized_result = run_centralized(n_sensors, CONFIG, objs)
    if centralized_result["latency_ps"] is not None:
        print(f"  t_start: {centralized_result['t_start_ps']:.0f} ps")
        print(f"  t_end:   {centralized_result['t_end_ps']:.0f} ps")
        print(f"  Latencia: {centralized_result['latency_ps']:.0f} ps")
    else:
        print("  Simulacao nao completou.")

    # --- Cenario 2: Distribuida ---
    print(f"\n[2/2] Simulacao DISTRIBUIDA ({n_hubs} Hubs + Agregador, {n_sensors} sensores)...")
    distributed_result = run_distributed(n_sensors, n_hubs, CONFIG, objs)
    if distributed_result["latency_ps"] is not None:
        print(f"  t_start: {distributed_result['t_start_ps']:.0f} ps")
        print(f"  t_end:   {distributed_result['t_end_ps']:.0f} ps")
        print(f"  Latencia: {distributed_result['latency_ps']:.0f} ps")
    else:
        print("  Simulacao nao completou.")

    # --- Exportar CSV ---
    results = [centralized_result, distributed_result]
    write_results_csv(results, output)
    print(f"\nResultados exportados para '{output}'")

    # --- Resumo ---
    lat_c = centralized_result["latency_ps"]
    lat_d = distributed_result["latency_ps"]
    if lat_c is not None and lat_d is not None:
        diff = lat_c - lat_d
        print(f"\nResumo:")
        print(f"  Centralizada: {lat_c:.0f} ps")
        print(f"  Distribuida:  {lat_d:.0f} ps")
        print(f"  Diferenca:    {diff:.0f} ps", end="")
        if diff > 0:
            print(" (centralizada mais lenta)")
        elif diff < 0:
            print(" (distribuida mais lenta)")
        else:
            print(" (iguais)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Comparacao de latencia: topologia centralizada vs distribuida."
    )
    parser.add_argument(
        "--sensors", "-N", type=int, default=12,
        help="Numero total de sensores para modo fixo (padrao: 12)"
    )
    parser.add_argument(
        "--hubs", "-K", type=int, default=3,
        help="Numero de hubs intermediarios na topologia distribuida (padrao: 3)"
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Semente para reprodutibilidade"
    )
    parser.add_argument(
        "--output", "-o", type=str, default="validacao_resultados.csv",
        help="Arquivo CSV de saida (padrao: validacao_resultados.csv)"
    )
    parser.add_argument(
        "--vary-n", action="store_true",
        help="Varrer N=[1,2,3,4,5,10,20,...,100] com K fixo (ignora --sensors)"
    )
    args = parser.parse_args()

    main(
        n_sensors=args.sensors,
        n_hubs=args.hubs,
        seed=args.seed,
        output=args.output,
        vary_n=args.vary_n,
    )
