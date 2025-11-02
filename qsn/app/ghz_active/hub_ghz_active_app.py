from sequence.utils import log
from sequence.protocol import Protocol
from sequence.components.circuit import Circuit
from sequence.network_management.reservation import Reservation
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from .message_ghz_active import GHZMessageType, GHZMessage


class HubGHZActiveApp(Protocol):
    """An 'active' application for the Hub node.

    This application actively initiates the GHZ state creation process by
    requesting entanglement with a list of sensor nodes.

    Attributes:
        sensors_to_monitor (list[str]): A list of sensor names to monitor and entangle with.
        memories_by_sensor (dict): A dictionary to store the memory states from each sensor.
        min_entangled_sensors (int): The minimum number of sensors that must be entangled
                                     to proceed with the joint measurement.
        min_entangled_memories (int): The minimum number of entangled memories required per sensor.
        memory_size (int): The number of memories to request for entanglement.
        start_time (int): The simulation time at which to start entanglement requests.
        entanglement_window (int): The duration to keep entanglement requests active.
        end_time (int): The simulation time at which to end entanglement attempts.
        quantum_circuit_operations (list): A list of quantum operations to be applied.
    """

    def __init__(self, owner, sensors_to_monitor: list, start_time=1e12, entanglement_window=2e12,
                 quantum_circuit_operations: list = None,
                 append_ghz: bool = False,
                 ghz_topology: str = "chain"):
        """Constructor for the HubGHZActiveApp.

        Args:
            owner (Node): The hub node on which this application is installed.
            sensors_to_monitor (list[str]): The list of sensor names to entangle with.
            start_time (int): The start time for entanglement requests.
            entanglement_window (int): How long entanglement attempts should remain valid.
            quantum_circuit_operations (list, optional): A list of quantum operations to be applied. Defaults to None.
        """
        # Identificação do app e registro no Hub
        name = f"{owner.name}-ghz-app"
        super().__init__(owner, name)
        self.owner.protocols.append(self)

        # Sensores monitorados e tracking local de memórias
        self.sensors_to_monitor = sensors_to_monitor
        self.memories_by_sensor = {}

        # Parâmetros mínimos e alocação por sensor
        self.min_entangled_sensors = len(sensors_to_monitor) // 2
        self.min_entangled_memories = 1
        self.memory_size = 1

        # Janela temporal para tentativas de emaranhamento
        self.start_time = start_time
        self.entanglement_window = entanglement_window
        self.end_time = self.start_time + self.entanglement_window

        # Circuito quântico customizável (opcional)
        self.quantum_circuit_operations = quantum_circuit_operations if quantum_circuit_operations is not None else []

        # Opções de preparação/medição GHZ automática
        # ghz_topology: "chain" (H(0); CX(0,1); CX(1,2); ...) ou "star" (CX(0,j) j>=1; depois H(0))
        self.append_ghz = append_ghz
        self.ghz_topology = ghz_topology  # "chain" | "star"
        if self.quantum_circuit_operations:
            log.logger.info(f"Quantum circuit loaded with operations: {self.quantum_circuit_operations}")

        # Pré-cálculos derivados e estado interno
        # Se formos fazer GHZ automático, exigimos TODOS os sensores informados.
        self.required_qubits = len(sensors_to_monitor) if self.append_ghz else self._compute_required_qubits()
        self.completed = False

        log.logger.info(
            f"{self.owner.name} app circuit requires {self.required_qubits} qubits "
            f"within a {self.entanglement_window} time-unit entanglement window."
        )

    def start(self):
        """Starts the process by sending GHZ proposals to all monitored sensors."""
        log.logger.info(f"{self.owner.name} app starting active GHZ process.")
        
        for sensor_name in self.sensors_to_monitor:
            msg = GHZMessage(
                msg_type=GHZMessageType.PROPOSE_GHZ,
                receiver=f"{sensor_name}-ghz-app",
                start_time=self.start_time,
                end_time=self.end_time,
                hub_name=self.owner.name
            )
            self.owner.send_message(sensor_name, msg)

    def request_entanglement(self, sensor_name: str):
        """Requests entanglement with a specified sensor.

        Args:
            sensor_name (str): The name of the sensor to entangle with.
        """
        self.owner.network_manager.request(
            sensor_name,
            start_time=self.start_time,
            end_time=self.end_time,
            memory_size=self.memory_size,
            target_fidelity=0.8
        )
        log.logger.info(f"{self.owner.name} app requested entanglement with {sensor_name}.")

    def get_memory(self, info):
        """Callback function for the memory manager.

        This method is called when a memory has been updated, for example, after an
        entanglement attempt. It registers the memory state and checks if a joint
        measurement should be performed.

        Args:
            info (MemoryInfo): An object containing information about the memory.
        """
        if info.state == "ENTANGLED":
            self.to_register_memories(info.remote_node, info.state)
            log.logger.info(f"{self.owner.name} app registered entangled memory from {info.remote_node}.")
            # early trigger: if we already have enough entangled sensors, run now
            if not self.completed and self.should_process_joint_measurement():
                log.logger.info(f"{self.owner.name} app triggering joint measurement.")
                self.simulate_joint_measurement()
                self.completed = True

    def simulate_joint_measurement(self):
        """Aplica o circuito quântico customizado nas memórias emaranhadas e as mede."""
        # 1) Determina quantos qubits o circuito exige (máximo índice + 1)
        required_qubits = self.required_qubits if getattr(self, "required_qubits", None) else self._compute_required_qubits()

        # 2) Escolhe, por sensor, a memória ENTANGLED com MAIOR fidelidade
        best_mem_by_sensor = {}
        for mem_info in self.owner.resource_manager.memory_manager:
            if mem_info.state != "ENTANGLED" or not mem_info.remote_node:
                continue
            sensor = mem_info.remote_node
            # Apenas sensores que estamos monitorando
            if sensor not in self.sensors_to_monitor:
                continue
            try:
                memo_name = mem_info.memory.name
            except Exception:
                memo_name = str(getattr(mem_info.memory, "name", "<unknown>"))
            log.logger.info(
                f"{self.owner.name} app checando fidelidade da memoria {memo_name} associada ao sensor {sensor} pra botar no circuito (f={mem_info.fidelity:.4f})."
            )
            prev = best_mem_by_sensor.get(sensor)
            if prev is None or mem_info.fidelity > prev.fidelity:
                best_mem_by_sensor[sensor] = mem_info

        # 3) Sensores com emaranhamento confirmado pelo nosso tracking interno E com melhor memória disponível
        candidate_infos = []  # lista de tuplas (sensor, MemoryInfo)
        for sensor, mi in best_mem_by_sensor.items():
            if self.memories_by_sensor.get(sensor, []).count("ENTANGLED") >= self.min_entangled_memories:
                candidate_infos.append((sensor, mi))

        # logs de depuração do conjunto candidato
        log.logger.info(f"{self.owner.name} app sensores candidatos por fidelidade: {[s for s,_ in candidate_infos]}")

        if len(candidate_infos) < required_qubits:
            log.logger.warning(
                f"{self.owner.name} app tem apenas {len(candidate_infos)} sensores candidatos; requer {required_qubits} para rodar o circuito."
            )
            # também loga descartes por insuficiência
            return

        # 4) Ordena candidatos por fidelidade decrescente e seleciona os necessários
        candidate_infos.sort(key=lambda t: t[1].fidelity, reverse=True)
        selected = candidate_infos[:required_qubits]
        discarded = candidate_infos[required_qubits:]

        # Logs de seleção/descarta por fidelidade
        for sensor, mi in selected:
            memo_name = getattr(getattr(mi, "memory", None), "name", "<unknown>")
            log.logger.info(
                f"{self.owner.name} app fidelidade da memória {memo_name} associada ao sensor {sensor} alta, adicionada ao circuito (f={mi.fidelity:.4f})."
            )
        for sensor, mi in discarded:
            memo_name = getattr(getattr(mi, "memory", None), "name", "<unknown>")
            log.logger.info(
                f"{self.owner.name} app fidelidade da memória {memo_name} associada ao sensor {sensor} baixa, descartada (f={mi.fidelity:.4f})."
            )

        selected_sensors = [s for s, _ in selected]
        entangled_qubits = [mi.memory for _, mi in selected]
        log.logger.info(f"{self.owner.name} app selected sensors for circuit (by fidelity): {selected_sensors}")

        # 5) Constrói o circuito com o tamanho mínimo necessário
        circuit = Circuit(len(entangled_qubits))
        # Pré-operações fornecidas pelo usuário (se houver)
        operations = list(self.quantum_circuit_operations)
        # Se configurado, acrescenta as portas de GHZ antes da medição
        if self.append_ghz:
            ghz_ops = self._build_ghz_ops(len(entangled_qubits))
            operations += ghz_ops
            log.logger.info(f"{self.owner.name} app appended GHZ ops ({self.ghz_topology}): {ghz_ops}")

        for op, *qubits_indices in operations:
            if all(isinstance(i, int) and i < len(entangled_qubits) for i in qubits_indices):
                try:
                    gate_method = getattr(circuit, op.lower())
                    gate_method(*qubits_indices)
                except AttributeError:
                    log.logger.error(f"Gate '{op}' not supported by Circuit class. Application aborted.")
                    return
            else:
                log.logger.error(f"Invalid qubit index in operation {op}{qubits_indices}. Circuit application aborted.")
                return

        # 6) Marca medições no circuito para todos os qubits usados
        for i in range(len(entangled_qubits)):
            circuit.measure(i)

        # 7) Aplica o circuito via QuantumManager.run_circuit com amostra de medição
        try:
            keys = [q.qstate_key for q in entangled_qubits]
            qm = self.owner.timeline.quantum_manager
            meas_samp = float(self.owner.get_generator().random())
            results_map = qm.run_circuit(circuit, keys, meas_samp=meas_samp)
        except Exception as e:
            log.logger.error(f"Failed to run circuit: {e}")
            return

        # 8) Ordena os resultados pela ordem dos qubits selecionados
        outcomes = [int(results_map.get(key, 0)) for key in keys]
        for i, outcome in enumerate(outcomes):
            log.logger.info(f"{self.owner.name} app measured qubit {i} with outcome {outcome}.")

        log.logger.info(f"{self.owner.name} app joint measurement with custom circuit completed. Outcomes: {outcomes}")
        self.completed = True
    
    def should_process_joint_measurement(self):
        """Verifica se há recursos suficientes para executar a medição conjunta e o circuito."""
        if self.completed:
            return False

        required_qubits = self.required_qubits if getattr(self, "required_qubits", None) else self._compute_required_qubits()

        # Sensores com ENTANGLED suficientes (pelo tracking interno) E com memória entangled disponível no hub
        entangled_memory_nodes = {mi.remote_node for mi in self.owner.resource_manager.memory_manager if mi.state == "ENTANGLED"}
        entangled_sensors = [
            s for s in self.sensors_to_monitor
            if self.memories_by_sensor.get(s, []).count("ENTANGLED") >= self.min_entangled_memories and s in entangled_memory_nodes
        ]
        entangled_qubits_count = len(entangled_sensors)

        if entangled_qubits_count >= required_qubits:
            log.logger.info(f"{self.owner.name} app has sufficient resources to process joint measurement.")
            return True
        else:
            log.logger.warning(
                f"{self.owner.name} app has only {entangled_qubits_count} entangled qubits; requires {required_qubits} to run the circuit."
            )
            return False

    def _compute_required_qubits(self) -> int:
        rq = 1
        try:
            for op, *indices in self.quantum_circuit_operations:
                if indices:
                    rq = max(rq, max(indices) + 1)
        except Exception:
            pass
        return rq
    
    def _build_ghz_ops(self, n: int):
        """Gera as operações para medição na base GHZ com n qubits.

        Topologias suportadas:
        - chain: H(0); CX(0,1); CX(1,2); ...; CX(n-2, n-1)
        - star:  CX(0,j) para j=1..n-1; H(0)
        """
        ops = []
        if n <= 1:
            return ops
        if self.ghz_topology == "star":
            ops += [("CX", 0, j) for j in range(1, n)]
            ops += [("H", 0)]
        else:  # chain (padrão)
            ops += [("H", 0)]
            for j in range(0, n - 1):
                ops += [("CX", j, j + 1)]
        return ops
    
    def should_process_fallback(self, sensor_name: str):
        """Checks if a fallback message should be sent to a sensor.

        This is triggered if the deadline is reached and no entanglement was
        established with the given sensor.

        Args:
            sensor_name (str): The name of the sensor to check.
        """
        if self.owner.timeline.now() >= self.end_time:
            if sensor_name in self.sensors_to_monitor and self.memories_by_sensor.get(sensor_name) is None:
                log.logger.info(f"{self.owner.name} app processing fallback for {sensor_name}.")
                msg = GHZMessage(
                    msg_type=GHZMessageType.ATTEMPT_FAILED,
                    receiver=f"{sensor_name}-ghz-app"
                )
                self.owner.send_message(sensor_name, msg)
                
    def to_register_memories(self, sensor_name: str, info: str):
        """Registers the memory state received from a sensor.

        Args:
            sensor_name (str): The name of the sensor providing the memory info.
            info (str): The state of the memory (e.g., "ENTANGLED").
        """
        if self.memories_by_sensor.get(sensor_name) is None:
            self.memories_by_sensor[sensor_name] = []
        
        if len(self.memories_by_sensor[sensor_name]) < self.memory_size:
            self.memories_by_sensor[sensor_name].append(info)
            
    def received_message(self, src: str, msg):
        """Main message handler for the protocol.

        Args:
            src (str): The name of the source node of the message.
            msg (Message): The message object received.
        """
        if msg.msg_type == GHZMessageType.ACEPT_GHZ:
            log.logger.info(f"{self.owner.name} app received ACEPT_GHZ message from {src}")
            self.request_entanglement(src)
        elif msg.msg_type == GHZMessageType.STATUS_UPDATE:
            self.should_process_fallback(src)
        elif msg.msg_type == GHZMessageType.CLASSICAL_FALLBACK:
            log.logger.info(f"{self.owner.name} app received CLASSICAL_FALLBACK message from {src}")
        else:
            log.logger.warning(f"{self.owner.name} app received unknown message type {msg.msg_type} from {src}")
    
    # This methods are required by the Protocol class but are not used in this active model.
    def get_other_reservation(self, reservation: Reservation):
        """Required by Protocol, but not used in this active model.

        This method should not be called, as the Hub is the initiator. It's
        implemented for compatibility with the parent Protocol class.

        Args:
            reservation (Reservation): The reservation object.
        """
        pass
    
    def get_reservation_result(self, reservation: Reservation, result: bool):
        """Callback to receive the result of a reservation request.

        Args:
            reservation (Reservation): The reservation that was resolved.
            result (bool): True if the reservation was successful, False otherwise.
        """
        if result:
            log.logger.info(f"Reservation for {reservation.responder} approved on node {self.owner.name}")
        else:
            log.logger.info(f"Reservation for {reservation.responder} failed on node {self.owner.name}")
