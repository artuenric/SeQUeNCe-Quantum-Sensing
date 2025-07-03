from sequence.utils import log
from sequence.components.circuit import Circuit

class GHZHandlerApp:
    """
    Uma aplicação passiva para o Hub.
    Esta aplicação aguarda passivamente o emaranhamento de sensores e, quando todos os sensores estão conectados, cria o circuito GHZ.
    """
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
            log.logger.info(f"{self.node.name} se emaranhou com sucesso com {info.remote_node} na memória {info.index}.")
            
            self.entangled_sensors[info.remote_node] = info
            
            if len(self.entangled_sensors) == len(self.sensors_to_monitor):
                log.logger.info(f"{self.node.name} detectou que todos os sensores ({', '.join(self.sensors_to_monitor)}) estão conectados. "
                            "Iniciando a medição conjunta.")
                self.simulate_joint_measurement()

    def simulate_joint_measurement(self):
        """
        Aplica o circuito GHZ para simular a medição conjunta,
        usando o QuantumManager.
        """
        memory_infos = list(self.entangled_sensors.values())
        
        if len(memory_infos) < 2:
            log.logger.warning(f"{self.node.name} tentou criar GHZ, mas tem menos de 2 sensores emaranhados.")
            return

        num_qubits = len(memory_infos)
        ghz_circuit = Circuit(num_qubits)
        ghz_circuit.h(0)
        for i in range(num_qubits - 1):
            ghz_circuit.cx(i, i + 1)
        
        qstate_keys = [info.memory.qstate_key for info in memory_infos]
        
        log.logger.info(f"{self.node.name}: Executando circuito GHZ nas chaves de estado {qstate_keys}.")

        self.node.timeline.quantum_manager.run_circuit(
            ghz_circuit,
            qstate_keys
        )

        log.logger.info(f"{self.node.name}: Medição conjunta simulada com sucesso.")
        
        for info in memory_infos:
            # Argumento 1: None (não temos um protocolo formal)
            self.node.resource_manager.update(None, info.memory, "RAW")
        
        log.logger.info(f"{self.node.name}: Memórias { [info.index for info in memory_infos] } liberadas.")
        
        # Limpa o dicionário para a próxima rodada
        self.entangled_sensors = {}

    # Métodos obrigatórios mas não utilizados
    def start(self):
        # O método start não contém lógica, uma vez que a app é passiva
        pass
    def get_other_reservation(self, reservation):
        """
        Callback para quando uma solicitação de reserva de outro nó chega.
        No modelo passivo, este é o Hub recebendo a solicitação do Sensor.
        Nenhuma ação é necessária aqui por enquanto, apenas registramos o evento.
        """
        log.logger.info(f"app received reservation request from {reservation.initiator}")
        pass