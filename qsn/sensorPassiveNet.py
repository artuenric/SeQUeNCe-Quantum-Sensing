from config import setup_logger
from sequence.topology.router_net_topo import RouterNetTopo
from app import GHZHandlerApp

def set_parameters(topology: RouterNetTopo):
    """
    Função para configurar os parâmetros dos componentes da rede.
    (Sem alterações aqui)
    """
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

    # Parâmetros dos protocolos de swapping nos roteadores
    SWAP_SUCC_PROB = 0.64
    SWAP_DEGRADATION = 0.99
    for node in topology.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        node.network_manager.protocol_stack[1].set_swapping_success_rate(SWAP_SUCC_PROB)
        node.network_manager.protocol_stack[1].set_swapping_degradation(SWAP_DEGRADATION)

    # Parâmetros dos canais quânticos
    # Aumentamos a atenuação para tornar o cenário um pouco mais realista
    ATTENUATION = 0.0002
    for qc in topology.get_qchannels():
        qc.attenuation = ATTENUATION

if __name__ == "__main__":
    network_config_file = "qsn/net.json"

    print("Carregando a topologia do arquivo:", network_config_file)
    network_topo = RouterNetTopo(network_config_file)
    tl = network_topo.get_timeline()

    print("Configurando o logger para a simulação...")
    log_file_name = "sensor_passive_network"
    setup_logger(tl, log_file_name, mode='custom')
    
    print("Configurando os parâmetros da simulação...")
    set_parameters(network_topo)

    # Passo 2: Encontrar e separar os nós por tipo (Hubs e Sensores)
    all_nodes = network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)
    hubs = {node.name: node for node in all_nodes if "Hub" in node.name}
    sensors = {node.name: node for node in all_nodes if "Sensor" in node.name}

    # Passo 3: Instalar a aplicação nos Hubs
    print("Instalando a HubApp nos hubs...")
    hub1_sensors = ["Sensor1H1", "Sensor2H1"]
    hub2_sensors = ["Sensor1H2", "Sensor2H2"]

    app_hub1 = GHZHandlerApp(hubs["Hub1"], hub1_sensors)
    hubs["Hub1"].set_app(app_hub1)
    
    app_hub2 = GHZHandlerApp(hubs["Hub2"], hub2_sensors)
    hubs["Hub2"].set_app(app_hub2)
    
    # Passo 4: Fazer com que cada sensor inicie uma requisição para o seu hub
    print("Iniciando as requisições de emaranhamento dos sensores para os hubs...")
    # Tempo de início das requisições
    start_time = 1e12
    end_time = 10e12
    
    for sensor_name, sensor_node in sensors.items():
        # Determina a qual hub o sensor deve se conectar
        target_hub = "Hub1" if "H1" in sensor_name else "Hub2"
        
        nm = sensor_node.network_manager
        # Parâmetros: (nó_destino, tempo_inicio, tempo_fim, tamanho_memoria, fidelidade_alvo)
        nm.request(target_hub, start_time, end_time, 1, 0.8)
        print(f"Sensor '{sensor_name}' solicitou emaranhamento com '{target_hub}'.")

    # Passo 5: Rodar a simulação
    print("\nIniciando a simulação...")
    tl.init()
    # Não precisamos mais chamar app.start() pois a app é passiva
    tl.run()
    print("Simulação concluída.")

    print(f"\nVerifique o arquivo '{log_file_name}' para ver os detalhes da execução, "
          "incluindo a criação do estado GHZ nos hubs.")