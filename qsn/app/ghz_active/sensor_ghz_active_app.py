from sequence.utils import log
from sequence.protocol import Protocol
from sequence.message import Message
from .message_ghz_active import GHZMessageType, GHZMessage
from sequence.components.circuit import Circuit
from .sensor_ghz_active_fallback_app import SensorGHZActiveFallBackApp


class SensorGHZActiveApp(Protocol):
    """An application/protocol for sensor nodes.

    This application reacts to entanglement proposals from a central hub.

    Attributes:
        hub_name (str): The name of the central hub node.
        hub_app_name (str): The name of the corresponding application on the hub node.
    """

    def __init__(self, owner):
        """Constructor for the SensorGHZActiveApp.

        Args:
            owner (Node): The sensor node on which this application is installed.
        """
        name = f"{owner.name}-ghz-app"
        super().__init__(owner, name)
        self.owner.protocols.append(self)
        self.hub_name = None
        self.hub_app_name = None

    def set_hub_name(self, hub_name: str):
        """Sets the hub node to communicate with.

        Args:
            hub_name (str): The name of the hub node.
        """
        self.hub_name = hub_name
        self.hub_app_name = f"{hub_name}-ghz-app"
        log.logger.info(f"{self.owner.name} app set hub to {hub_name}")
    
    def get_memory(self, info):
        """Callback for memory updates, triggering a status report to the hub.

        Args:
            info (MemoryInfo): An object containing information about the updated memory.
        """
        self.send_status(info)

    def send_status(self, info):
        """Sends a memory status update to the hub.
        
        This is used by the hub to decide whether to proceed with its main plan
        or to execute a fallback procedure.

        Args:
            info (MemoryInfo): The memory information containing the state to be sent.
        """
        msg = GHZMessage(
            msg_type=GHZMessageType.STATUS_UPDATE,
            receiver=self.hub_app_name,
            status=info.state
        )
        self.owner.send_message(self.hub_name, msg)
        log.logger.info(f"{self.owner.name} sent status '{info.state}' update to {self.hub_name}")
            
    def local_measurement(self) -> int:
        """Simulates a local measurement.

        Returns:
            int: A random classical bit (0 or 1).
        """
        classical_result = self.owner.get_generator().integers(2)
        return classical_result
    
    def acept_ghz(self, src: str):
        """Sends a message to the hub to accept the GHZ proposal.

        Args:
            src (str): The name of the source node of the proposal (the hub).
        """
        msg = GHZMessage(
            msg_type=GHZMessageType.ACEPT_GHZ,
            receiver=self.hub_app_name
        )
        self.owner.send_message(self.hub_name, msg)
        log.logger.info(f"{self.owner.name} app accepted GHZ proposal from {src}")
    
    def fallback(self):
        """Switches the node's application to the fallback protocol.

        This method replaces the current app instance with SensorGHZActiveFallBackApp,
        allowing the node to operate under the fallback mechanism.
        """
        app = SensorGHZActiveFallBackApp(self.owner, self.hub_name)
        self.owner.set_app(app)
        self.owner.app.start()
        self.owner.protocols.remove(self)
    
    def received_message(self, src: str, msg: Message):
        """Main message handler for the protocol.

        Args:
            src (str): The name of the source node of the message.
            msg (Message): The message object received.
        """
        if msg.msg_type == GHZMessageType.PROPOSE_GHZ:
            self.set_hub_name(src)
            self.acept_ghz(src)
        elif msg.msg_type == GHZMessageType.ATTEMPT_FAILED:
            self.fallback()
        else:
            log.logger.warning(f"{self.owner.name} app received unknown message type {msg.msg_type} from {src}")
    
    # This methods are required by the Protocol/App class but are not used in this active model.
    def start(self):
        """Start method required by the Protocol interface. Not used in this app."""
        pass
    
    def get_other_reservation(self, reservation):
        """Callback for receiving reservation requests.

        Args:
            reservation (Reservation): The incoming reservation object.
        """
        log.logger.info(f"{self.owner.name} app received reservation request from {reservation.initiator}")
