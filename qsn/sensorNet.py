import json
import logging
from sequence.topology.router_net_topo import RouterNetTopo

# Configura o logging para salvar a saída em um arquivo.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    filename="sensorNet.txt",
    filemode="w" 
)

def set_parameters(topology: RouterNetTopo):
    """
    Função para configurar os parâmetros dos componentes da rede.
    Baseado nos exemplos do repositório.
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
    ATTENUATION = 1e-5 # atenuação em dB/km
    QC_FREQ = 1e11
    for qc in topology.get_qchannels():
        qc.attenuation = ATTENUATION
        qc.frequency = QC_FREQ

if __name__ == "__main__":
    # Carrega a topologia a partir do arquivo JSON que criamos
    network_config_file = "qsn/net.json"

    print("Carregando a topologia do arquivo:", network_config_file)
    network_topo = RouterNetTopo(network_config_file)
    tl = network_topo.get_timeline()

    print("Configurando os parâmetros da simulação...")
    set_parameters(network_topo)

    # Nós de início e fim da requisição.
    # Escolhemos dois sensores em hubs diferentes para testar o swapping.
    start_node_name = "Sensor1H1"
    end_node_name = "Hub2"
    
    node1 = None
    node2 = None

    for router in network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER):
        if router.name == start_node_name:
            node1 = router
        elif router.name == end_node_name:
            node2 = router
            
    if not node1 or not node2:
        raise Exception("Nós de início ou fim não encontrados na topologia.")

    print(f"Iniciando requisição de emaranhamento entre '{start_node_name}' e '{end_node_name}'...")
    
    nm = node1.network_manager
    # Parâmetros da requisição: (nó_destino, tempo_inicio, tempo_fim, tamanho_memoria, fidelidade_alvo)
    nm.request(end_node_name, 1e12, 10e12, 10, 0.8)

    print("Iniciando a simulação...")
    tl.init()
    tl.run()
    print("Simulação concluída.")

    print("\n---------- Resultados ----------")
    print(f"Memórias do nó inicial ({start_node_name}):")
    print("Índice:\tNó Emaranhado:\tFidelidade:\tEstado:")
    
    for info in node1.resource_manager.memory_manager:
        if info.state == "ENTANGLED":
            print("{:6}\t{:18}\t{:10.4f}\t{}".format(info.index, info.remote_node, info.fidelity, info.state))