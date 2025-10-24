"""
Funções utilitárias para parametrização da rede.

Contém a função set_parameters, separada da configuração (CONFIG).
Implementa acessos robustos ao dicionário via .get(), para evitar
quebras quando chaves estiverem ausentes.
"""
from typing import Any, Dict, Optional

from sequence.topology.router_net_topo import RouterNetTopo

from config import CONFIG


def _safe_get(d: Dict[str, Any], *keys: str) -> Any:
    """Recupera um valor aninhado usando .get() encadeado.

    Exemplo: _safe_get(hardware, "memoria", "FREQ")
    """
    cur: Any = d
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
        if cur is None:
            return None
    return cur


def set_parameters(topology: RouterNetTopo, config: Optional[Dict[str, Any]] = None) -> None:
    """Configura parâmetros físicos/hardware na topologia.

    Usa acesso seguro (.get) e só aplica parâmetros quando os valores
    existem (não-None), evitando erros quando uma chave faltar.
    """
    cfg: Dict[str, Any] = CONFIG if config is None else config
    hardware = cfg.get("hardware", {})

    # Memórias dos roteadores
    for node in topology.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        memory_array = node.get_components_by_type("MemoryArray")[0]

        freq = _safe_get(hardware, "memoria", "FREQ")
        if freq is not None:
            memory_array.update_memory_params("frequency", freq)

        coherence = _safe_get(hardware, "memoria", "EXPIRE")
        if coherence is not None:
            memory_array.update_memory_params("coherence_time", coherence)

        efficiency = _safe_get(hardware, "memoria", "EFFICIENCY")
        if efficiency is not None:
            memory_array.update_memory_params("efficiency", efficiency)

        fidelity = _safe_get(hardware, "memoria", "FIDELITY")
        if fidelity is not None:
            memory_array.update_memory_params("raw_fidelity", fidelity)

    # Parâmetros de swapping na pilha do gerenciador de rede
    for node in topology.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        succ_prob = _safe_get(hardware, "swapping", "SUCC_PROB")
        if succ_prob is not None:
            node.network_manager.protocol_stack[1].set_swapping_success_rate(succ_prob)

        degradation = _safe_get(hardware, "swapping", "DEGRADATION")
        if degradation is not None:
            node.network_manager.protocol_stack[1].set_swapping_degradation(degradation)

    # BSMs
    for node in topology.get_nodes_by_type(RouterNetTopo.BSM_NODE):
        bsm = node.get_components_by_type("SingleAtomBSM")[0]

        det_eff = _safe_get(hardware, "detector", "EFFICIENCY")
        if det_eff is not None:
            bsm.update_detectors_params("efficiency", det_eff)

        count_rate = _safe_get(hardware, "detector", "COUNT_RATE")
        if count_rate is not None:
            bsm.update_detectors_params("count_rate", count_rate)

        resolution = _safe_get(hardware, "detector", "RESOLUTION")
        if resolution is not None:
            bsm.update_detectors_params("time_resolution", resolution)

    # Canais quânticos
    att = _safe_get(hardware, "canal_quantico", "ATTENUATION")
    if att is not None:
        for qc in topology.get_qchannels():
            qc.attenuation = att
