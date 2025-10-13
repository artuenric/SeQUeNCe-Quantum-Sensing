from sequence.topology.router_net_topo import RouterNetTopo

"""
Arquivo de Configuração para a Simulação de Rede Quântica.
"""

CONFIG = {
    "simulacao": {
        "NETWORK_CONFIG_FILE": "qsn/net.json",
        "LOG_FILE_NAME": "log",
        "START_TIME": 1e12,
        "END_TIME": 3e12,
    },
    "hubs_config": [
        {
            "name": "Hub1", 
            "sensors": ["Sensor1H1", "Sensor2H1", "Sensor3H1", "Sensor4H1"]
        },
        {
            "name": "Hub2", 
            "sensors": ["Sensor1H2", "Sensor2H2", "Sensor3H2", "Sensor4H2"]
        },
        {
            "name": "Hub3",
            "sensors": ["Sensor1H3", "Sensor2H3", "Sensor3H3", "Sensor4H3"]
        }
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
        }
    }
}

def set_parameters(topology: RouterNetTopo):
    """Configura os parâmetros da rede quântica com base no dicionário de configuração."""
    
    hardware = CONFIG["hardware"]
    
    for node in topology.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        memory_array = node.get_components_by_type("MemoryArray")[0]
        memory_array.update_memory_params("frequency", hardware["memoria"]["FREQ"])
        memory_array.update_memory_params("coherence_time", hardware["memoria"]["EXPIRE"])
        memory_array.update_memory_params("efficiency", hardware["memoria"]["EFFICIENCY"])
        memory_array.update_memory_params("raw_fidelity", hardware["memoria"]["FIDELITY"])

    for node in topology.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        node.network_manager.protocol_stack[1].set_swapping_success_rate(hardware["swapping"]["SUCC_PROB"])
        node.network_manager.protocol_stack[1].set_swapping_degradation(hardware["swapping"]["DEGRADATION"])

    for node in topology.get_nodes_by_type(RouterNetTopo.BSM_NODE):
        bsm = node.get_components_by_type("SingleAtomBSM")[0]
        bsm.update_detectors_params("efficiency", hardware["detector"]["EFFICIENCY"])
        bsm.update_detectors_params("count_rate", hardware["detector"]["COUNT_RATE"])
        bsm.update_detectors_params("time_resolution", hardware["detector"]["RESOLUTION"])

    for qc in topology.get_qchannels():
        qc.attenuation = hardware["canal_quantico"]["ATTENUATION"]