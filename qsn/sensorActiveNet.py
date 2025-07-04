from config import setup_logger
from sequence.topology.router_net_topo import RouterNetTopo
from app import GHZRequestApp
from app import EntanglamentResponderApp
    
def set_parameters(topology: RouterNetTopo):
    """Função para configurar os parâmetros da rede (idêntica à anterior)."""

    # Parâmetros das memórias quânticas
    MEMO_FREQ = 2e3
    MEMO_EXPIRE = 0
    MEMO_EFFICIENCY = 1
    MEMO_FIDELITY = 0.93
    for node in topology.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        memory_array = node.get_components_by_type("MemoryArray")[0]
        memory_array.update_memory_params("frequency", MEMO_FREQ)
        memory_array.update_memory_params("coherence_time", MEMO_EXPIRE)
        memory_array.update_memory_params("efficiency", MEMO_EFFICIENCY)
        memory_array.update_memory_params("raw_fidelity", MEMO_FIDELITY)
    
    # Parâmetros dos detectores dos BSMs
    DETECTOR_EFFICIENCY = 0.0
    DETECTOR_COUNT_RATE = 5e7
    DETECTOR_RESOLUTION = 100
    for node in topology.get_nodes_by_type(RouterNetTopo.BSM_NODE):
        bsm = node.get_components_by_type("SingleAtomBSM")[0]
        bsm.update_detectors_params("efficiency", DETECTOR_EFFICIENCY)
        bsm.update_detectors_params("count_rate", DETECTOR_COUNT_RATE)
        bsm.update_detectors_params("time_resolution", DETECTOR_RESOLUTION)
    
    # Parâmetros dos protocolos de swapping
    SWAP_SUCC_PROB = 0.64
    SWAP_DEGRADATION = 0.99
    for node in topology.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        node.network_manager.protocol_stack[1].set_swapping_success_rate(SWAP_SUCC_PROB)
        node.network_manager.protocol_stack[1].set_swapping_degradation(SWAP_DEGRADATION)

    # Parâmetros dos canais quânticos
    ATTENUATION = 0.0002
    for qc in topology.get_qchannels():
        qc.attenuation = ATTENUATION

if __name__ == "__main__":
    # Usamos o mesmo arquivo de configuração de rede
    network_config_file = "qsn/net.json"

    print(f"Carregando a topologia do arquivo: {network_config_file}")
    network_topo = RouterNetTopo(network_config_file)
    tl = network_topo.get_timeline()
    start_time = 1e12
    end_time = 10e12
    tl.stop_time = end_time + 1e12

    print("Configurando o logger para a simulação...")
    log_file_name = "sensor_active_efic0"
    setup_logger(tl, log_file_name, mode='custom')

    print("Configurando os parâmetros da simulação...")
    set_parameters(network_topo)
    
    # Encontra e separa os nós por tipo
    all_nodes = network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)
    hubs = {node.name: node for node in all_nodes if "Hub" in node.name}
    sensors = {node.name: node for node in all_nodes if "Sensor" in node.name}

    # Instala a SensorGenEntanglementApp em todos os sensores
    print("Instalando as aplicações nos sensores...")
    for name, node in sensors.items():
        # O nome da app é o nome do nó acrescido de "_app"
        app = EntanglamentResponderApp(node, f"{name}_app")
        node.set_app(app)

    # Instala a ActiveHubApp em todos os hubs
    print("Instalando as aplicações nos hubs...")
    hub1_sensors = ["Sensor1H1", "Sensor2H1"]
    hub2_sensors = ["Sensor1H2", "Sensor2H2"]

    app_hub1 = GHZRequestApp(hubs["Hub1"], "hub1_app", hub1_sensors, start_time
                             )
    hubs["Hub1"].set_app(app_hub1)
    
    app_hub2 = GHZRequestApp(hubs["Hub2"], "hub2_app", hub2_sensors, start_time, end_time)
    hubs["Hub2"].set_app(app_hub2)
    
    # Inicia a simulação e o processo ATIVO
    print("\nIniciando a simulação...")
    tl.init()
    
    # A principal diferença: chamamos o método start() das apps dos Hubs
    app_hub1.start()
    app_hub2.start()

    tl.run()
    print("Simulação concluída.")
    
    print("\nVerifique o arquivo 'active_network.log' para ver os detalhes da execução.")