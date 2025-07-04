from sequence.utils import log
from sequence.protocol import Protocol
from sequence.components.circuit import Circuit
from sequence.network_management.reservation import Reservation
from sequence.message import Message

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
        
        self.entangled_sensors = {}  # Dicionário para armazenar sensores emaranhados
        self.pending_sensors = sensors_to_monitor.copy()  # Sensores que ainda não foram emaranhados

    def start(self):
        """
        Inicia o processo, enviando requisições de emaranhamento para todos os sensores.
        """
        log.logger.info(f"{self.owner.name} app starting active entanglement process.")
        for sensor_name in self.sensors_to_monitor:
            # O NetworkManager do Hub solicita o emaranhamento
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
        Callback para quando uma memória muda de estado. A lógica aqui é idêntica à da aplicação passiva.
        """
        if info.state == "ENTANGLED" and info.remote_node in self.sensors_to_monitor:
            log.logger.info(f"{self.owner.name} app successfully entangled with {info.remote_node}.")
            
            # Armazena o sucesso do emaranhamento e remove o sensor da lista pendente
            self.entangled_sensors[info.remote_node] = info
            self.pending_sensors.remove(info.remote_node)
            
            # Sucesso ou falha
            if not self.pending_sensors:
                log.logger.info(f"All pending reservations resolved. Initiating joint measurement.")
                self.simulate_joint_measurement()

    def simulate_joint_measurement(self):
        """Aplica o circuito GHZ apenas nos sensores que se emaranharam com sucesso."""
        
        # Medida de segurança: se nenhum sensor se emaranhou, não faz nada.
        if not self.entangled_sensors:
            log.logger.warning(f"No entangled memories available to perform measurement. Aborting.")
            return

        memory_infos = list(self.entangled_sensors.values())
        qstate_keys = [info.memory.qstate_key for info in memory_infos]
        num_qubits = len(memory_infos)
        ghz_circuit = Circuit(num_qubits)
        
        log.logger.info(f"Performing joint measurement on {num_qubits} sensors: {list(self.entangled_sensors.keys())}")

        ghz_circuit.h(0)
        for i in range(num_qubits - 1):
            ghz_circuit.cx(i, i + 1)
        for i in range(num_qubits):
            ghz_circuit.measure(i)

        measurement_results = self.owner.timeline.quantum_manager.run_circuit(
            circuit=ghz_circuit,
            keys=qstate_keys,
            meas_samp=self.owner.get_generator().random()
        )

        log.logger.info(f"Classical measurement result: {measurement_results}")
        
        for info in memory_infos:
            self.owner.resource_manager.update(None, info.memory, "RAW")
        
        log.logger.info(f"app freed memories: {[info.index for info in memory_infos]}.")
        self.entangled_sensors.clear()

    # Métodos obrigatórios mas não utilizados
    def get_other_reservation(self, reservation):
        # Este método não deve ser chamado no modelo ativo, pois o Hub é o iniciador.
        # Mas o mantemos por compatibilidade com a herança de Protocol.
        pass
    
    def get_reservation_result(self, reservation: Reservation, result: bool):
        """
        Callback para receber o resultado de uma solicitação de reserva.
        """
        responder = reservation.responder

        if responder not in self.pending_sensors:
            return  # Ignora se já tratamos este sensor

        if result:
            log.logger.info(f"Reservation for {responder} approved. Waiting for entanglement.")
        else:
            # LÓGICA DO PLANO B (FALHA NA RESERVA)
            log.logger.warning(f"Reservation for {responder} has FAILED or EXPIRED.")
            self.pending_sensors.remove(responder) # Remove da lista de pendentes

            # Verifica se, mesmo com a falha, já podemos prosseguir
            if not self.pending_sensors:
                log.logger.info(f"All pending reservations resolved. Initiating joint measurement with available resources.")
                self.simulate_joint_measurement()
    
    def received_message(self, src: str, msg: Message):
        """Lida com mensagens recebidas. Especificamente, a mensagem de 'fallback clássico' do sensor."""
        
        msg_content = msg.content
        
        if msg_content.get("type") == "classical_fallback":
            bit = msg_content.get("bit")
            log.logger.warning(self, f"received classical fallback bit {bit} from sensor {src}.")
            
            # Armazenamos o resultado clássico (opcional, mas bom para o futuro)
            self.classical_results[src] = bit
            
            # ##############################################################
            # LÓGICA FALTANTE ADICIONADA AQUI
            # ##############################################################
            # Se o sensor que enviou a mensagem ainda estava pendente...
            if src in self.pending_sensors:
                # ...nós o removemos da lista de pendentes!
                self.pending_sensors.remove(src)
                log.logger.info(self, f"Sensor {src} resolved via classical fallback.")
                
                # E agora, verificamos se todos os outros já responderam.
                if not self.pending_sensors:
                    log.logger.info(self, f"All pending sensors resolved. Initiating joint measurement with available resources.")
                    self.simulate_joint_measurement()