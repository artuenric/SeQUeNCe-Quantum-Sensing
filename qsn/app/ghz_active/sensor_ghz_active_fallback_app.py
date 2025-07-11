from sequence.utils import log
from sequence.protocol import Protocol
from sequence.message import Message
from .message_ghz_active import GHZMessageType, GHZMessage
from sequence.components.circuit import Circuit


class SensorGHZActiveFallBackApp(Protocol):
    """An application/protocol for sensor nodes acting as a fallback.

    This protocol is activated when the primary entanglement strategy fails.
    Its purpose is to perform a local measurement and send the classical
    result back to the hub.

    Attributes:
        hub_name (str): The name of the central hub node.
        hub_app_name (str): The name of the corresponding application on the hub node.
    """

    def __init__(self, owner, hub_name: str):
        """Constructor for the SensorGHZActiveFallBackApp.

        Args:
            owner (Node): The sensor node on which this application is installed.
            hub_name (str): The name of the hub node to send results to.
        """
        name = f"{owner.name}-ghz-fallback-app"
        super().__init__(owner, name)
        self.owner.protocols.append(self)
        self.hub_name = hub_name
        self.hub_app_name = f"{hub_name}-ghz-app"
    
    def local_measurement(self) -> int:
        """Simulates a local measurement by generating a random classical bit.

        Returns:
            int: A random classical bit (0 or 1).
        """
        classical_result = self.owner.get_generator().integers(2)
        return classical_result

    def fallback(self):
        """Sends the classical result of a local measurement to the Hub."""
        log.logger.info(f"{self.owner.name} app executing fallback by sending classical result to Hub.")
        classical_result = self.local_measurement()
        msg = GHZMessage(
            GHZMessageType.CLASSICAL_FALLBACK, 
            self.hub_app_name, 
            classical_result=classical_result
        )
        self.owner.send_message(self.hub_name, msg)
        log.logger.info(f"{self.owner.name} sent classical result {classical_result} to node {self.hub_name}.")
    
    # This methods are required by the Protocol/App interface but is not used in this app.
    def start(self):
        """Starts the fallback process."""
        log.logger.info(f"{self.owner.name} app starting fallback process.")
        self.fallback()
    
    def received_message(self, src: str, msg: Message):
        """Required by Protocol, but not used in this fallback app.
        
        This application does not process incoming messages.
        """
        pass
    
    def get_other_reservation(self, reservation):
        """Required by Protocol, but not used in this fallback app."""
        pass

    def get_memory(self, info):
        """Required by Protocol, but not used in this fallback app."""
        pass