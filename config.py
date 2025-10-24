"""
Arquivo de configuração geral da simulação.

Este módulo contém apenas o dicionário CONFIG, separado da lógica
de parametrização. O caminho do arquivo de rede agora é relativo à
raiz do projeto ("net.json").
"""

# Dicionário de configuração principal
CONFIG = {
    "simulacao": {
        # Caminho ajustado para o arquivo na raiz do projeto
        "NETWORK_CONFIG_FILE": "net.json",
        "LOG_FILE_NAME": "log",
        "START_TIME": 1e12,
        "END_TIME": 3e12,
    },
    "hubs_config": [
        {
            "name": "Hub1",
            "sensors": ["Sensor1H1", "Sensor2H1", "Sensor3H1", "Sensor4H1"],
        },
        {
            "name": "Hub2",
            "sensors": ["Sensor1H2", "Sensor2H2", "Sensor3H2", "Sensor4H2"],
        },
        {
            "name": "Hub3",
            "sensors": ["Sensor1H3", "Sensor2H3", "Sensor3H3", "Sensor4H3"],
        },
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
        },
    },
    "circuito_quantico": {
        "operacoes": [
            ("H", 0),
            ("CX", 0, 1),
        ]
    },
}
