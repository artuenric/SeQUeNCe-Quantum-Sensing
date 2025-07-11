from sequence.utils import log
from sequence.protocol import Protocol
from sequence.components.circuit import Circuit
from sequence.network_management.reservation import Reservation 
from .message_ghz_active import GHZMessageType, GHZMessage

class GHZRequestApp(Protocol):
    """Uma aplicação 'ativa' para o Hub.
    Esta aplicação inicia ativamente o processo, solicitando emaranhamento com uma lista de nós sensores.
    """
    def __init__(self, owner, sensors_to_monitor: list, start_time=1e12, end_time=10e12):
        """Construtor da ActiveHubApp.

        Args:
            owner (Node): O nó do hub ao qual a aplicação está instalada.
            name (str): Um nome para a instância da aplicação.
            sensors_to_monitor (list): A lista de nomes dos sensores para emaranhar.
            start_time (int): O tempo de início para as solicitações de emaranhamento.
            end_time (int): O tempo final para as solicitações.
        """
        name = f"{owner.name}-ghz-app"
        super().__init__(owner, name)
        self.owner.protocols.append(self)
        self.sensors_to_monitor = sensors_to_monitor
        self.entangled_sensors = {} 
        self.start_time = start_time
        self.end_time = end_time

    def start(self):
        """
        Inicia o processo, enviando requisições de emaranhamento para todos os sensores.
        """
        log.logger.info(f"{self.owner.name} app starting active entanglement process.")
        
        for sensor_name in self.sensors_to_monitor:
            msg = GHZMessage(
            msg_type=GHZMessageType.PROPOSE_GHZ,
            receiver=sensor_name+"-ghz-app",
            start_time=self.start_time,
            end_time=self.end_time,
            hub_name=self.owner.name
            )
            self.owner.send_message(sensor_name, msg)
        
    def request_entanglement(self, sensor_name):
        """Solicita o emaranhamento com os sensores especificados na lista sensors_to_monitor."""
        self.owner.network_manager.request(
            sensor_name,
            start_time=self.start_time,
            end_time=self.end_time,
            memory_size=1,
            target_fidelity=0.8
        )
        log.logger.info(f"{self.owner.name} app requested entanglement with {sensor_name}.")

    def get_memory(self, info):
        """
        Callback para quando uma memória muda de estado.
        A lógica aqui é idêntica à da aplicação passiva.
        """
        if info.state == "ENTANGLED" and info.remote_node in self.sensors_to_monitor:
            log.logger.info(f"{self.owner.name} app successfully entangled with {info.remote_node}.")
            
            self.entangled_sensors[info.remote_node] = info
            
            if len(self.entangled_sensors) == len(self.sensors_to_monitor):
                log.logger.info(f"{self.owner.name} app detected all sensors connected. Initiating joint measurement.")
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
        
        log.logger.info(f"{self.owner.name} app executing GHZ circuit on state keys {qstate_keys}.")

        self.owner.timeline.quantum_manager.run_circuit(ghz_circuit, qstate_keys)
        log.logger.info(f"{self.owner.name} app joint measurement simulated successfully.")
        
    def finish(self):
        log.logger.info(f"{self.owner.name} app finishing and freeing entangled memories.")
        memory_infos = list(self.entangled_sensors.values())
        for info in memory_infos:
            self.owner.resource_manager.update(None, info.memory, "RAW")
        
        log.logger.info(f"{self.owner.name} app freed memories: {[info.index for info in memory_infos]}.")
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
        print(result)
        if result:
            log.logger.info(f"Reservation for {reservation.responder} approved on node {self.owner.name}")
        else:
            log.logger.info(f"Reservation for {reservation.responder} failed on node {self.owner.name}")
            # FUTURAMENTE: aqui poderíamos implementar uma lógica de retentativa ou
            # decidir prosseguir com um estado GHZ com menos qubits.
    
    def attempt_failed(self, sensor_name: str):
        if sensor_name in self.sensors_to_monitor:
            if sensor_name not in self.entangled_sensors:
                log.logger.info(f"{self.owner.name} app processing fallback for {sensor_name}.")
                msg = GHZMessage(
                    msg_type=GHZMessageType.ATTEMPT_FAILED,
                    receiver=sensor_name+"-ghz-app"
                )
                self.owner.send_message(sensor_name, msg)
                
    
    def received_message(self, src: str, msg):
        if msg.msg_type == GHZMessageType.ACEPT_GHZ:
            log.logger.info(f"{self.owner.name} app received ACEPT GHZ message from {src}")
            self.request_entanglement(src)
        elif msg.msg_type == GHZMessageType.STATUS_UPDATE:
            if msg.status == "RAW":
                self.attempt_failed(src)
        elif msg.msg_type == GHZMessageType.CLASSICAL_FALLBACK:
            log.logger.info(f"{self.owner.name} app received CLASSICAL_FALLBACK message from {src}")
        else:
            log.logger.warning(f"{self.owner.name} app received unknown message type {msg.msg_type} from {src}")