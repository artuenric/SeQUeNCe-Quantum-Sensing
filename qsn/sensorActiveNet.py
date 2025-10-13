from sequence.topology.router_net_topo import RouterNetTopo
from app.ghz_active import HubGHZActiveApp, SensorApp
from utils import setup_logger
# Importamos a função e o dicionário do nosso arquivo de parâmetros
from parameters import set_parameters, CONFIG

if __name__ == "__main__":
    # 1. Carregar configurações diretamente do dicionário CONFIG
    network_file = CONFIG['simulacao']['NETWORK_CONFIG_FILE']
    log_file_name = CONFIG['simulacao']['LOG_FILE_NAME']
    start_time = CONFIG['simulacao']['START_TIME']
    end_time = CONFIG['simulacao']['END_TIME']

    # 2. Configuração inicial da rede e do logger
    print(f"Carregando a topologia do arquivo: {network_file}")
    network_topo = RouterNetTopo(network_file)
    tl = network_topo.get_timeline()

    print("Configurando o logger para a simulação...")
    setup_logger(tl, log_file_name, mode='custom')

    print("Configurando os parâmetros da simulação...")
    set_parameters(network_topo)

    # 3. Obter todos os nós da topologia de uma vez
    all_nodes = network_topo.get_nodes_by_type(RouterNetTopo.QUANTUM_ROUTER)
    node_map = {node.name: node for node in all_nodes}

    # 4. Loop de instalação automática das aplicações
    all_hubs_apps = []
    
    print("Instalando aplicações nos nós (Hubs e Sensores)...")
    for hub_info in CONFIG['hubs_config']:
        hub_name = hub_info['name']
        sensor_names = hub_info['sensors']
        
        # Instala a App no Hub
        hub_node = node_map.get(hub_name)
        if hub_node:
            app_hub = HubGHZActiveApp(hub_node, sensor_names, start_time, end_time)
            hub_node.set_app(app_hub)
            all_hubs_apps.append(app_hub)
            print(f"  Aplicação instalada no hub: {hub_name}")

        # Instala as Apps nos Sensores associados
        for sensor_name in sensor_names:
            sensor_node = node_map.get(sensor_name)
            if sensor_node:
                app_sensor = SensorApp(sensor_node)
                sensor_node.set_app(app_sensor)
                print(f"    Aplicação instalada no sensor: {sensor_name}")

    # 5. Inicia a simulação
    print("\nIniciando a simulação...")
    tl.init()
    
    # Inicia o processo ATIVO em todos os hubs configurados
    for app in all_hubs_apps:
        app.start()

    tl.run()
    print("Simulação concluída.")
    
    # 6. Usa a variável de configuração na mensagem final
    print(f"\nVerifique o arquivo '{log_file_name}.log' para ver os detalhes da execução.")