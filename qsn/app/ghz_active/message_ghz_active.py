from enum import Enum, auto
from sequence.message import Message


class GHZMessageType(Enum):
    """Defines the message types for the GHZ state creation protocol.
    
    The comments indicate the typical direction of communication:
    - Hub -> Sensor
    - Sensor -> Hub
    """
    PROPOSE_GHZ = auto()        # Hub -> Sensor
    ACEPT_GHZ = auto()          # Sensor -> Hub
    REJECT_GHZ = auto()         # Sensor -> Hub
    STATUS_UPDATE = auto()      # Sensor -> Hub
    ATTEMPT_FAILED = auto()     # Hub -> Sensor
    CLASSICAL_FALLBACK = auto() # Sensor -> Hub
    

class GHZMessage(Message):
    """Custom message for communication in the GHZ protocol.

    This class populates its attributes based on the message type,
    allowing for flexible data transfer.

    Attributes:
        msg_type (GHZMessageType): The type of the message.
        receiver (str): The name of the protocol that will receive the message.
        hub_name (str): The name of the initiating hub node.
        star_time (int): The start time for the protocol execution.
        end_time (int): The deadline for the protocol execution.
        num_memories (int): The number of memories involved.
        status (any): The status being updated.
        classical_result (any): The classical measurement result for the fallback plan.
    """

    def __init__(self, msg_type: GHZMessageType, receiver: str, **kwargs):
        """Constructor for the GHZMessage.

        Args:
            msg_type (GHZMessageType): The type of the message.
            receiver (str): The name of the protocol that will receive the message.
            **kwargs: Keyword arguments that compose the message attributes,
                      e.g., end_time=10e12, hub_name="hub_node".
        """
        super().__init__(msg_type, receiver)

        if msg_type is GHZMessageType.PROPOSE_GHZ:
            self.hub_name = kwargs.get("hub_name")
            self.start_time = kwargs.get("start_time")
            self.end_time = kwargs.get("end_time")
            self.num_memories = kwargs.get("num_memories")
        elif msg_type is GHZMessageType.STATUS_UPDATE:
            self.status = kwargs.get("status")
        elif msg_type is GHZMessageType.CLASSICAL_FALLBACK:
            self.classical_result = kwargs.get("classical_result")