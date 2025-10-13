from sequence.utils import log
from sequence.message import Message
from ..message_ghz_active import GHZMessageType, GHZMessage
from .sensor_state import SensorState

class FallbackState(SensorState):
    """Estado de fallback, executa medição local e envia o resultado."""
    def __init__(self, app):
        super().__init__(app)
        self.enter()

    def enter(self):
        """Na entrada, executa a lógica de fallback."""
        log.logger.info(f"{self.app.owner.name} app executing fallback by sending classical result to Hub.")
        classical_result = self.app.local_measurement()
        msg = GHZMessage(
            GHZMessageType.CLASSICAL_FALLBACK, 
            self.app.hub_app_name, 
            classical_result=classical_result
        )
        self.app.owner.send_message(self.app.hub_name, msg)
        log.logger.info(f"{self.app.owner.name} sent classical result {classical_result} to node {self.app.hub_name}.")

    def handle_message(self, src: str, msg: Message):
        """Neste estado, a maioria das mensagens é ignorada."""
        log.logger.debug(f"{self.app.owner.name} received message in FallbackState from {src}. Ignoring.")
        pass
