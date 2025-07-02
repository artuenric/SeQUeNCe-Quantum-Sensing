import logging
from sequence.protocol import Protocol
from sequence.components.circuit import Circuit
from sequence.network_management.reservation import Reservation 

logger = logging.getLogger(__name__)

class GHZRequestApp(Protocol):
    """Uma aplicação 'ativa' para o Hub.
    Esta aplicação inicia ativamente o processo, solicitando emaranhamento com uma lista de nós sensores.
    """
    def __init__(self, owner, name: str, sensors_to_monitor: list, start_time=1e12, end_time=10e12):
        """Construtor da ActiveHubApp.

        Args:
            owner (Node): O nó do hub ao qual a aplicação está instalada.
            name (str): Um nome para a instância da aplicação.
            sensors_to_monitor (list): A lista de nomes de sensores para emaranhar.
            start_time (int): O tempo de início para as solicitações de emaranhamento.
            end_time (int): O tempo final para as solicitações.
        """
        super().__init__(owner, name)
        self.sensors_to_monitor = sensors_to_monitor
        self.entangled_sensors = {}  # Dicionário para rastrear o sucesso
        self.start_time = start_time
        self.end_time = end_time

    def start(self):
        """
        Inicia o processo, enviando requisições de emaranhamento para todos os sensores.
        """
        logger.info(f"{self.owner.name} app starting active entanglement process.")
        for sensor_name in self.sensors_to_monitor:
            # O NetworkManager do Hub solicita o emaranhamento
            self.owner.network_manager.request(
                sensor_name,
                start_time=self.start_time,
                end_time=self.end_time,
                memory_size=1,
                target_fidelity=0.8
            )
            logger.info(f"{self.owner.name} app requested entanglement with {sensor_name}.")

    def get_memory(self, info):
        """
        Callback para quando uma memória muda de estado.
        A lógica aqui é idêntica à da aplicação passiva.
        """
        if info.state == "ENTANGLED" and info.remote_node in self.sensors_to_monitor:
            logger.info(f"{self.owner.name} app successfully entangled with {info.remote_node}.")
            
            self.entangled_sensors[info.remote_node] = info
            
            if len(self.entangled_sensors) == len(self.sensors_to_monitor):
                logger.info(f"{self.owner.name} app detected all sensors connected. "
                            "Initiating joint measurement.")
                self.simulate_joint_measurement()

    def simulate_joint_measurement(self):
        """
        Aplica o circuito GHZ.
        A lógica aqui é idêntica à da aplicação passiva.
        """
        memory_infos = list(self.entangled_sensors.values())
        
        if len(memory_infos) < 2:
            return

        num_qubits = len(memory_infos)
        ghz_circuit = Circuit(num_qubits)
        ghz_circuit.h(0)
        for i in range(num_qubits - 1):
            ghz_circuit.cx(i, i + 1)
        
        qstate_keys = [info.memory.qstate_key for info in memory_infos]
        
        logger.info(f"{self.owner.name} app executing GHZ circuit on state keys {qstate_keys}.")

        self.owner.timeline.quantum_manager.run_circuit(ghz_circuit, qstate_keys)
        logger.info(f"{self.owner.name} app joint measurement simulated successfully.")
        
        for info in memory_infos:
            self.owner.resource_manager.update(None, info.memory, "RAW")
        
        logger.info(f"{self.owner.name} app freed memories: {[info.index for info in memory_infos]}.")
        self.entangled_sensors = {}

    # Métodos obrigatórios mas não utilizados
    def get_other_reservation(self, reservation):
        # Este método não deve ser chamado no modelo ativo, pois o Hub é o iniciador.
        # Mas o mantemos por compatibilidade com a herança de Protocol.
        pass
    
    def get_reservation_result(self, reservation: Reservation, result: bool):
        """
        Callback para receber o resultado de uma solicitação de reserva.
        """
        if result:
            logger.info(f"Reservation for {reservation.responder} approved on node {self.owner.name}")
        else:
            logger.warning(f"Reservation for {reservation.responder} failed on node {self.owner.name}")
            # FUTURAMENTE: aqui poderíamos implementar uma lógica de retentativa ou
            # decidir prosseguir com um estado GHZ com menos qubits.
    
    def received_message(self, src: str, msg):
        """
        Método obrigatório pela herança de 'Protocol'.
        No modelo ativo, o Hub (iniciador) não espera receber
        mensagens clássicas, então a implementação pode ser vazia.
        """
        pass