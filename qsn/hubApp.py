import logging
from sequence.components.circuit import Circuit

# Pega o logger configurado no script principal
logger = logging.getLogger(__name__)

class HubApp:
    def __init__(self, node, sensors_to_monitor: list):
        """
        Construtor da aplicação do Hub.
        """
        self.node = node
        self.sensors_to_monitor = sensors_to_monitor
        self.entangled_sensors = {}  # Dicionário: {"nome_sensor": objeto_memory_info}

    def get_memory(self, info):
        """
        Método de callback chamado pelo ResourceManager quando uma memória é atualizada.
        """
        if info.state == "ENTANGLED" and info.remote_node in self.sensors_to_monitor:
            logger.info(f"{self.node.name} se emaranhou com sucesso com {info.remote_node} na memória {info.index}.")
            
            self.entangled_sensors[info.remote_node] = info
            
            if len(self.entangled_sensors) == len(self.sensors_to_monitor):
                logger.info(f"{self.node.name} detectou que todos os sensores ({', '.join(self.sensors_to_monitor)}) estão conectados. "
                            "Iniciando a medição conjunta.")
                self.simulate_joint_measurement()

    def simulate_joint_measurement(self):
        """
        Aplica o circuito GHZ para simular a medição conjunta,
        usando o QuantumManager.
        """
        memory_infos = list(self.entangled_sensors.values())
        
        if len(memory_infos) < 2:
            logger.warning(f"{self.node.name} tentou criar GHZ, mas tem menos de 2 sensores emaranhados.")
            return

        num_qubits = len(memory_infos)
        ghz_circuit = Circuit(num_qubits)
        ghz_circuit.h(0)
        for i in range(num_qubits - 1):
            ghz_circuit.cx(i, i + 1)
        
        qstate_keys = [info.memory.qstate_key for info in memory_infos]
        
        logger.info(f"{self.node.name}: Executando circuito GHZ nas chaves de estado {qstate_keys}.")

        self.node.timeline.quantum_manager.run_circuit(
            ghz_circuit,
            qstate_keys
        )

        logger.info(f"{self.node.name}: Medição conjunta simulada com sucesso.")
        
        # Correção Definitiva: Passar os argumentos corretos para o método update.
        for info in memory_infos:
            # Argumento 1: None (não temos um protocolo formal)
            # Argumento 2: info.memory (o objeto Memory, como exige a docstring)
            self.node.resource_manager.update(None, info.memory, "RAW")
        
        logger.info(f"{self.node.name}: Memórias { [info.index for info in memory_infos] } liberadas.")
        
        # Limpa o dicionário para a próxima rodada
        self.entangled_sensors = {}

    def start(self):
        pass

    def get_other_reservation(self, reservation):
        pass