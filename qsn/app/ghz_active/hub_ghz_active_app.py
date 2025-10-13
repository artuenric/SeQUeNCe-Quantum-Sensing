from sequence.utils import log
from sequence.protocol import Protocol
from sequence.components.circuit import Circuit
from sequence.network_management.reservation import Reservation
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
        end_time (int): The simulation time at which to end entanglement attempts.
    """

    def __init__(self, owner, sensors_to_monitor: list, start_time=1e12, end_time=10e12):
        """Constructor for the HubGHZActiveApp.

        Args:
            owner (Node): The hub node on which this application is installed.
            sensors_to_monitor (list[str]): The list of sensor names to entangle with.
            start_time (int): The start time for entanglement requests.
            end_time (int): The end time for entanglement requests.
        """
        name = f"{owner.name}-ghz-app"
        super().__init__(owner, name)
        self.owner.protocols.append(self)
        self.sensors_to_monitor = sensors_to_monitor
        self.memories_by_sensor = {}
        self.min_entangled_sensors = len(sensors_to_monitor) // 2
        self.min_entangled_memories = 1
        self.memory_size = 1
        self.start_time = start_time
        self.end_time = end_time

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
        
        if self.owner.timeline.now() >= self.end_time:
            self.should_process_joint_measurement()
            
    def simulate_joint_measurement(self):
        """Applies the GHZ circuit to the entangled memories."""
        log.logger.info(f"{self.owner.name} app joint measurement simulated successfully.")
    
    def should_process_joint_measurement(self):
        """Checks if conditions are met to perform a joint measurement."""
        count_able_to_joint_measure = 0
        if len(self.memories_by_sensor.keys()) == len(self.sensors_to_monitor):
            for sensor in self.memories_by_sensor.keys():
                if self.memories_by_sensor[sensor].count("ENTANGLED") >= self.min_entangled_memories:
                    count_able_to_joint_measure += 1
            
            if count_able_to_joint_measure >= self.min_entangled_sensors:
                log.logger.info(f"{self.owner.name} app processing joint measurement.")
                self.simulate_joint_measurement()
    
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