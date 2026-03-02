"""
poc_fallback.py - Prova de Conceito: Tolerancia a Falhas via Fallback Classico
===============================================================================

Demonstra o funcionamento da maquina de estados (NormalState / FallbackState)
e a tolerancia a falhas do simulador de redes quanticas de sensores.

Cenario
-------
  1 Hub  +  3 Sensores
  - Sensor1, Sensor2: parametros ideais  (emaranhamento bem-sucedido)
  - Sensor3:          parametros degradados (falha de emaranhamento -> fallback classico)

Fases registadas no log
-----------------------
  Fase 1 - Configuracao do cenario (topologia, parametros)
  Fase 2 - Inicializacao: Hub envia PROPOSE_GHZ, sensores aceitam, emaranhamento inicia
  Fase 3 - Detecao de falha: fim da janela, verificacao de emaranhamento por sensor
  Fase 4 - Fallback classico: sensor degradado transita para FallbackState
  Fase 5 - Agregacao: Hub reune dados quanticos + classicos de todos os nos

Uso
---
  python poc_fallback.py
  python poc_fallback.py --seed 42
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from itertools import combinations
from typing import Any, Dict, List, Optional, Tuple

from parameters_utils import set_parameters

# ---------------------------------------------------------------------------
# Configuracao da PoC
# ---------------------------------------------------------------------------
# Nota: canal_quantico.ATTENUATION omitido propositadamente para preservar
# as atenuacoes por conexao definidas no JSON da topologia.
POC_CONFIG: Dict[str, Any] = {
    "simulacao": {
        "START_TIME": 1e12,
        "ENTANGLEMENT_WINDOW": 2e12,
        "LOG_FILE_NAME": "poc_fallback_log",
    },
    "hardware": {
        "memoria": {"FREQ": 2e3, "EXPIRE": 0, "EFFICIENCY": 0.8, "FIDELITY": 0.93},
        "swapping": {"SUCC_PROB": 0.64, "DEGRADATION": 0.99},
        "detector": {"EFFICIENCY": 0.7, "COUNT_RATE": 5e7, "RESOLUTION": 100},
    },
}

DEGRADED_SENSOR = "Sensor3"
DEGRADED_CHANNEL_ATTENUATION = 10    # dB/km (vs 0.0002 ideal) — 99.99% perda
DEGRADED_COHERENCE_TIME = 1          # 1 ps  (vs 0 = infinito ideal)
DEGRADED_EFFICIENCY = 0.01           # 1%    (vs 80% ideal)

N_HEALTHY_SENSORS = 2  # Sensor1 e Sensor2


# ---------------------------------------------------------------------------
# Importacao segura
# ---------------------------------------------------------------------------

def _try_imports():
    mods: Dict[str, Any] = {}
    try:
        from sequence.topology.router_net_topo import RouterNetTopo
        mods["RouterNetTopo"] = RouterNetTopo
    except Exception as e:
        sys.exit(f"Erro ao importar RouterNetTopo: {e}")

    try:
        from qsn.app.ghz_active import HubGHZActiveApp, SensorApp
        from qsn.app.ghz_active import GHZMessageType, GHZMessage
        mods["HubGHZActiveApp"] = HubGHZActiveApp
        mods["SensorApp"] = SensorApp
        mods["GHZMessageType"] = GHZMessageType
        mods["GHZMessage"] = GHZMessage
    except Exception as e:
        sys.exit(f"Erro ao importar GHZ apps: {e}")

    try:
        from qsn.utils import setup_logger
        mods["setup_logger"] = setup_logger
    except Exception:
        try:
            from qsn.utils.logging_setup import setup_logger
            mods["setup_logger"] = setup_logger
        except Exception as e:
            sys.exit(f"Erro ao importar setup_logger: {e}")

    try:
        from sequence.kernel.event import Event
        from sequence.kernel.process import Process
        mods["Event"] = Event
        mods["Process"] = Process
    except Exception as e:
        sys.exit(f"Erro ao importar Event/Process: {e}")

    try:
        from sequence.utils import log
        mods["log"] = log
    except Exception as e:
        sys.exit(f"Erro ao importar log: {e}")

    return mods


# ---------------------------------------------------------------------------
# Utilitarios
# ---------------------------------------------------------------------------

def _schedule_event(tl, ev):
    """Agenda evento na timeline de forma compativel."""
    for name in ("schedule", "schedule_event", "scheduleEvent", "add_event"):
        m = getattr(tl, name, None)
        if callable(m):
            return m(ev)
    raise AttributeError("Timeline nao expoe metodo de agendamento conhecido.")


def _full_mesh_cconnections(node_names: List[str], delay: int = 100_000_000):
    return [{"node1": a, "node2": b, "delay": delay}
            for a, b in combinations(node_names, 2)]


# ---------------------------------------------------------------------------
# Geracao da topologia
# ---------------------------------------------------------------------------

def generate_poc_topology(filepath: str, base_seed: int = 42) -> Tuple[str, List[str]]:
    """Gera topologia 1 Hub + 3 Sensores.

    Sensor3 recebe atenuacao drasticamente alta no canal quantico para
    simular um ambiente hostil onde o emaranhamento e impossivel.
    """
    hub_name = "Hub"
    sensor_names = ["Sensor1", "Sensor2", "Sensor3"]

    nodes = [
        {"name": hub_name, "type": "QuantumRouter",
         "seed": base_seed, "memo_size": 100},
        {"name": "Sensor1", "type": "QuantumRouter",
         "seed": base_seed + 1, "memo_size": 20},
        {"name": "Sensor2", "type": "QuantumRouter",
         "seed": base_seed + 2, "memo_size": 20},
        {"name": "Sensor3", "type": "QuantumRouter",
         "seed": base_seed + 3, "memo_size": 20},
    ]

    qconnections = [
        # Sensor1 e Sensor2: canal ideal
        {"node1": "Sensor1", "node2": hub_name, "distance": 10,
         "attenuation": 0.0002, "type": "meet_in_the_middle",
         "seed": base_seed + 100},
        {"node1": "Sensor2", "node2": hub_name, "distance": 10,
         "attenuation": 0.0002, "type": "meet_in_the_middle",
         "seed": base_seed + 101},
        # Sensor3: canal degradado (atenuacao extrema)
        {"node1": "Sensor3", "node2": hub_name, "distance": 10,
         "attenuation": DEGRADED_CHANNEL_ATTENUATION,
         "type": "meet_in_the_middle",
         "seed": base_seed + 102},
    ]

    cconnections = _full_mesh_cconnections([hub_name] + sensor_names)

    topo = {
        "nodes": nodes,
        "qconnections": qconnections,
        "cconnections": cconnections,
        "stop_time": 10e12,
        "is_parallel": False,
    }

    with open(filepath, "w") as f:
        json.dump(topo, f, indent=2)

    return hub_name, sensor_names


# ---------------------------------------------------------------------------
# PoCHubApp: Hub com verificacao de fallback temporizada e agregacao
# ---------------------------------------------------------------------------

def _create_poc_hub_class(HubGHZActiveApp, GHZMessageType, GHZMessage,
                          Event, Process, log):
    """Cria PoCHubApp dinamicamente (mesmo padrao de validacao_topologias)."""

    class PoCHubApp(HubGHZActiveApp):
        """Hub que agenda verificacao de fallback e agrega resultados."""

        def __init__(self, owner, sensors_to_monitor, start_time,
                     entanglement_window=2e12, n_healthy=2):
            self.classical_results = {}
            self.aggregation_complete = False
            self._fallback_checked = False

            super().__init__(
                owner, sensors_to_monitor, start_time,
                entanglement_window=entanglement_window,
                quantum_circuit_operations=[],
                append_ghz=False,
            )
            # So precisamos de n_healthy qubits para a medicao conjunta
            self.required_qubits = n_healthy
            log.logger.info(
                f"{self.owner.name} required_qubits ajustado para "
                f"{n_healthy} (sensores saudaveis esperados)"
            )

        def start(self):
            log.logger.info("=" * 60)
            log.logger.info("FASE 2: Hub inicia protocolo GHZ com todos os sensores")
            log.logger.info("=" * 60)
            super().start()
            # Agendar verificacao de fallback apos fim da janela
            t_check = int(self.end_time) + 1
            ev = Event(t_check, Process(self, "check_all_fallbacks", []))
            _schedule_event(self.owner.timeline, ev)
            log.logger.info(
                f"{self.owner.name} verificacao de fallback agendada para t={t_check} ps"
            )

        def check_all_fallbacks(self):
            """Fim da janela: identifica sensores sem emaranhamento e envia ATTEMPT_FAILED."""
            if self._fallback_checked:
                return
            self._fallback_checked = True

            log.logger.info("=" * 60)
            log.logger.info("FASE 3: Fim da janela de emaranhamento - verificacao de estado")
            log.logger.info("=" * 60)

            for sensor in self.sensors_to_monitor:
                has_ent = (
                    self.memories_by_sensor.get(sensor) is not None
                    and "ENTANGLED" in self.memories_by_sensor.get(sensor, [])
                )
                if has_ent:
                    log.logger.info(
                        f"  [OK]   {sensor}: emaranhamento estabelecido (canal quantico)"
                    )
                else:
                    log.logger.info(
                        f"  [FAIL] {sensor}: SEM emaranhamento - enviando ATTEMPT_FAILED"
                    )
                    msg = GHZMessage(
                        msg_type=GHZMessageType.ATTEMPT_FAILED,
                        receiver=f"{sensor}-ghz-app",
                    )
                    self.owner.send_message(sensor, msg)

        def received_message(self, src, msg):
            if msg.msg_type == GHZMessageType.CLASSICAL_FALLBACK:
                log.logger.info("=" * 60)
                log.logger.info(
                    f"FASE 4: {self.owner.name} recebe fallback classico de {src}"
                )
                log.logger.info("=" * 60)
                self.classical_results[src] = msg.classical_result
                log.logger.info(
                    f"  {src} enviou resultado classico de leitura ambiental: "
                    f"{msg.classical_result}"
                )
                self._check_aggregation()
            else:
                super().received_message(src, msg)

        def _check_aggregation(self):
            """Verifica se todos os sensores (quantico + classico) reportaram."""
            quantum = [
                s for s in self.sensors_to_monitor
                if self.memories_by_sensor.get(s)
                and "ENTANGLED" in self.memories_by_sensor[s]
            ]
            classical = list(self.classical_results.keys())
            total = len(quantum) + len(classical)

            if total >= len(self.sensors_to_monitor):
                self.aggregation_complete = True
                log.logger.info("=" * 60)
                log.logger.info("FASE 5: AGREGACAO COMPLETA")
                log.logger.info(
                    f"  Dados quanticos de: {quantum} ({len(quantum)} sensores)"
                )
                log.logger.info(
                    f"  Fallback classico de: {classical} ({len(classical)} sensores)"
                )
                log.logger.info(
                    f"  Total: {total}/{len(self.sensors_to_monitor)} sensores OK"
                )
                log.logger.info(
                    "  RESULTADO: Rede sobreviveu a falha quantica parcial!"
                )
                log.logger.info("=" * 60)

    return PoCHubApp


# ---------------------------------------------------------------------------
# Heartbeat: mantem timeline ativa ate agregacao completa
# ---------------------------------------------------------------------------

class PoCHeartbeat:
    """Tick periodico que mantem a simulacao viva enquanto a agregacao nao completa."""

    def __init__(self, tl, Event, Process, hub_app,
                 tick_interval=1e9, start_time=1e12):
        self.tl = tl
        self.Event = Event
        self.Process = Process
        self.hub_app = hub_app
        self.tick_interval = tick_interval
        self.start_time = start_time
        self.done = False

    def start(self):
        ev = self.Event(int(self.start_time), self.Process(self, "tick", []))
        _schedule_event(self.tl, ev)

    def tick(self):
        if self.done:
            return
        if self.hub_app.aggregation_complete:
            self.done = True
            return
        t_next = int(self.tl.now() + self.tick_interval)
        ev = self.Event(t_next, self.Process(self, "tick", []))
        _schedule_event(self.tl, ev)


# ---------------------------------------------------------------------------
# Funcao principal
# ---------------------------------------------------------------------------

def run_poc(seed: int = 42):
    objs = _try_imports()

    RouterNetTopo = objs["RouterNetTopo"]
    SensorApp = objs["SensorApp"]
    HubGHZActiveApp = objs["HubGHZActiveApp"]
    GHZMessageType = objs["GHZMessageType"]
    GHZMessage = objs["GHZMessage"]
    setup_logger = objs["setup_logger"]
    Event = objs["Event"]
    Process = objs["Process"]
    log = objs["log"]

    PoCHubApp = _create_poc_hub_class(
        HubGHZActiveApp, GHZMessageType, GHZMessage, Event, Process, log,
    )

    topo_file = "_poc_topology.json"

    try:
        # ==================================================================
        # FASE 1: Configuracao do cenario
        # ==================================================================
        print("=" * 64)
        print("  PoC: Tolerancia a Falhas via Fallback Classico")
        print("=" * 64)
        print()
        print("Cenario: 1 Hub + 3 Sensores")
        print(f"  Sensor1, Sensor2 : parametros ideais")
        print(f"  {DEGRADED_SENSOR}          : parametros degradados")
        print(f"    - Canal quantico  : atenuacao = {DEGRADED_CHANNEL_ATTENUATION} dB/km "
              f"(ideal: 0.0002 dB/km)")
        print(f"    - Memoria quantica: coerencia = {DEGRADED_COHERENCE_TIME} ps "
              f"(ideal: infinita)")
        print(f"    - Memoria quantica: eficiencia = {DEGRADED_EFFICIENCY*100:.0f}% "
              f"(ideal: 80%)")
        print()

        # Gerar topologia
        hub_name, sensor_names = generate_poc_topology(topo_file, base_seed=seed)

        # Carregar topologia no SeQUeNCe
        network_topo = RouterNetTopo(topo_file)
        tl = network_topo.get_timeline()

        # Configurar logger
        setup_logger(tl, POC_CONFIG["simulacao"]["LOG_FILE_NAME"], mode="custom")
        # Rastrear modulo do script PoC
        log.track_module("__main__")
        log.track_module("poc_fallback")

        # Registar Fase 1 no log
        log.logger.info("=" * 60)
        log.logger.info("FASE 1: Configuracao do cenario de teste")
        log.logger.info("=" * 60)
        log.logger.info(f"  Topologia: 1 Hub + {len(sensor_names)} Sensores")
        log.logger.info(f"  Sensor degradado: {DEGRADED_SENSOR}")
        log.logger.info(
            f"    Canal quantico: atenuacao = {DEGRADED_CHANNEL_ATTENUATION} dB/km"
        )
        log.logger.info(
            f"    Memoria: coerencia = {DEGRADED_COHERENCE_TIME} ps, "
            f"eficiencia = {DEGRADED_EFFICIENCY*100:.0f}%"
        )

        # Aplicar parametros ideais a todos os nos
        set_parameters(network_topo, config=POC_CONFIG)

        # Construir mapa de nos
        all_nodes = network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)
        node_map = {node.name: node for node in all_nodes}

        # Degradar memoria do Sensor3
        degraded_node = node_map[DEGRADED_SENSOR]
        mem_array = degraded_node.get_components_by_type("MemoryArray")[0]
        mem_array.update_memory_params("coherence_time", DEGRADED_COHERENCE_TIME)
        mem_array.update_memory_params("efficiency", DEGRADED_EFFICIENCY)

        log.logger.info(
            f"  {DEGRADED_SENSOR} memoria degradada: "
            f"coherence_time={DEGRADED_COHERENCE_TIME} ps, "
            f"efficiency={DEGRADED_EFFICIENCY}"
        )
        log.logger.info("  Parametros ideais aplicados aos demais sensores.")

        # Instalar SensorApp em cada sensor
        for sname in sensor_names:
            s_node = node_map[sname]
            s_app = SensorApp(s_node)
            s_node.set_app(s_app)

        # Instalar PoCHubApp
        hub_node = node_map[hub_name]
        start_time = POC_CONFIG["simulacao"]["START_TIME"]
        ent_window = POC_CONFIG["simulacao"]["ENTANGLEMENT_WINDOW"]

        hub_app = PoCHubApp(
            hub_node, sensor_names, start_time,
            entanglement_window=ent_window,
            n_healthy=N_HEALTHY_SENSORS,
        )
        hub_node.set_app(hub_app)

        # Heartbeat
        heartbeat = PoCHeartbeat(
            tl, Event, Process, hub_app,
            tick_interval=1e9,
            start_time=start_time,
        )

        # ==================================================================
        # FASES 2-5: Execucao da simulacao
        # ==================================================================
        print("Iniciando simulacao...")
        print()
        tl.init()
        hub_app.start()
        heartbeat.start()
        tl.run()

        # ==================================================================
        # Resultados
        # ==================================================================
        quantum_sensors = [
            s for s in sensor_names
            if hub_app.memories_by_sensor.get(s)
            and "ENTANGLED" in hub_app.memories_by_sensor[s]
        ]
        classical_sensors = list(hub_app.classical_results.keys())

        print("=" * 64)
        print("  RESULTADOS")
        print("=" * 64)
        print()
        print(f"  Sensores c/ emaranhamento quantico : {quantum_sensors}")
        print(f"  Sensores em fallback classico      : {classical_sensors}")
        print(f"  Medicao conjunta completada        : {hub_app.completed}")
        print(f"  Agregacao completa                 : {hub_app.aggregation_complete}")
        if hub_app.classical_results:
            print(f"  Resultados classicos               : {hub_app.classical_results}")
        print()

        if hub_app.aggregation_complete:
            print("  CONCLUSAO: A falha de coerencia em " + DEGRADED_SENSOR)
            print("  NAO causou a queda da rede. A leitura ambiental")
            print("  foi entregue por todos os nos (quantico + classico).")
        else:
            print("  NOTA: Agregacao nao completou dentro do tempo de simulacao.")
            if not hub_app.completed:
                print("  (medicao conjunta tambem nao completou)")

        log_path = POC_CONFIG["simulacao"]["LOG_FILE_NAME"] + ".txt"
        print()
        print(f"  Log detalhado: {log_path}")
        print("=" * 64)

    finally:
        if os.path.exists(topo_file):
            os.remove(topo_file)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="PoC: Tolerancia a falhas via fallback classico."
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Semente para reprodutibilidade (padrao: 42)",
    )
    args = parser.parse_args()
    run_poc(seed=args.seed)
