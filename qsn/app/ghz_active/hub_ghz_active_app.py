from sequence.utils import log
from sequence.protocol import Protocol
from sequence.components.circuit import Circuit
from sequence.network_management.reservation import Reservation 
from .message_ghz_active import GHZMessageType, GHZMessage

class HubGHZActiveApp(Protocol):
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
        print(self.owner, sensors_to_monitor)
        self.memories_by_sensor = {}
        self.min_entangled_sensors = len(sensors_to_monitor)//2
        self.min_entangled_memories = 1
        self.memory_size = 1
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
            memory_size=self.memory_size,
            target_fidelity=0.8
        )
        log.logger.info(f"{self.owner.name} app requested entanglement with {sensor_name}.")

    def get_memory(self, info):
        if info.state == "ENTANGLED":
            self.to_register_memories(info.remote_node, info.state)
            log.logger.info(f"{self.owner.name} app registered entangled memory from {info.remote_node}.")
        if self.owner.timeline.now() >= self.end_time:
            self.should_process_joint_measurement()
                
        
    def simulate_joint_measurement(self):
        """
        Aplica o circuito GHZ.
        A lógica aqui é idêntica à da aplicação passiva.
        """
        log.logger.info(f"{self.owner.name} app joint measurement simulated successfully.")
        
    
    def should_process_joint_measurement(self):
        count_able_to_joint_measure = 0
        if len(self.memories_by_sensor.keys()) == len(self.sensors_to_monitor):
            for sensor in self.memories_by_sensor.keys():
                if self.memories_by_sensor[sensor].count("ENTANGLED") >= self.min_entangled_memories:
                    count_able_to_joint_measure += 1
                    
            if count_able_to_joint_measure >= self.min_entangled_sensors:
                log.logger.info(f"{self.owner.name} app processing joint measurement.")
                self.simulate_joint_measurement()
    
    def should_process_fallback(self, sensor_name: str):
        if self.owner.timeline.now() >= self.end_time:
            if sensor_name in self.sensors_to_monitor:
                if self.memories_by_sensor.get(sensor_name) is None:
                    log.logger.info(f"{self.owner.name} app processing fallback for {sensor_name}.")
                    msg = GHZMessage(
                        msg_type=GHZMessageType.ATTEMPT_FAILED,
                        receiver=sensor_name+"-ghz-app"
                    )
                    self.owner.send_message(sensor_name, msg)
                    
    
    def to_register_memories(self, sensor_name: str, info: str):
        """
        Registra o status das memórias recebidas de um sensor.
        """
        if self.memories_by_sensor.get(sensor_name) is None:
            self.memories_by_sensor[sensor_name] = []
        
        if len(self.memories_by_sensor[sensor_name]) < self.memory_size:
            self.memories_by_sensor[sensor_name].append(info)
            
        
        
    def received_message(self, src: str, msg):
        if msg.msg_type == GHZMessageType.ACEPT_GHZ:
            log.logger.info(f"{self.owner.name} app received ACEPT GHZ message from {src}")
            self.request_entanglement(src)
        elif msg.msg_type == GHZMessageType.STATUS_UPDATE:
            self.should_process_fallback(src)
        elif msg.msg_type == GHZMessageType.CLASSICAL_FALLBACK:
            log.logger.info(f"{self.owner.name} app received CLASSICAL_FALLBACK message from {src}")
        else:
            log.logger.warning(f"{self.owner.name} app received unknown message type {msg.msg_type} from {src}")
            
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
            log.logger.info(f"Reservation for {reservation.responder} approved on node {self.owner.name}")
        else:
            log.logger.info(f"Reservation for {reservation.responder} failed on node {self.owner.name}")