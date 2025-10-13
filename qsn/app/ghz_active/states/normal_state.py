from sequence.utils import log
from sequence.message import Message
from ..message_ghz_active import GHZMessageType
from .sensor_state import SensorState

class NormalState(SensorState):
    """Estado normal de operação, aguardando propostas GHZ."""
    def handle_message(self, src: str, msg: Message):
        if msg.msg_type == GHZMessageType.PROPOSE_GHZ:
            self.app.set_hub_name(src)
            self.app.acept_ghz(src)
        elif msg.msg_type == GHZMessageType.ATTEMPT_FAILED:
            log.logger.info(f"{self.app.owner.name} received ATTEMPT_FAILED. Transitioning to FallbackState.")
            from .fallback_state import FallbackState
            self.app.transition_to(FallbackState(self.app))
        else:
            log.logger.warning(f"{self.app.owner.name} app received unknown message type {msg.msg_type} in NormalState from {src}")
