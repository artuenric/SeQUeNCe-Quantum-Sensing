from sequence.utils import log
from sequence.protocol import Protocol
from sequence.message import Message
from .message_ghz_active import GHZMessageType, GHZMessage
from .states import SensorState, NormalState, FallbackState


class SensorApp(Protocol):
    """Aplicação unificada para nós sensores que gerencia seu próprio estado."""

    def __init__(self, owner):
        """Construtor para a SensorApp."""
        name = f"{owner.name}-ghz-app"
        super().__init__(owner, name)
        self.owner.protocols.append(self)
        self.hub_name = None
        self.hub_app_name = None
        # O estado inicial é NormalState
        self._state = NormalState(self)

    def transition_to(self, new_state: SensorState):
        """Muda o estado atual da aplicação."""
        log.logger.info(f"{self.owner.name} transitioning from {type(self._state).__name__} to {type(new_state).__name__}")
        self._state = new_state

    def set_hub_name(self, hub_name: str):
        """Define o hub com o qual se comunicar."""
        self.hub_name = hub_name
        self.hub_app_name = f"{hub_name}-ghz-app"
        log.logger.info(f"{self.owner.name} app set hub to {hub_name}")
    
    def get_memory(self, info):
        """Callback para atualizações de memória."""
        self.send_status(info)

    def send_status(self, info):
        """Envia uma atualização de status da memória para o hub."""
        msg = GHZMessage(
            msg_type=GHZMessageType.STATUS_UPDATE,
            receiver=self.hub_app_name,
            status=info.state
        )
        self.owner.send_message(self.hub_name, msg)
        log.logger.info(f"{self.owner.name} sent status '{info.state}' update to {self.hub_name}")
            
    def local_measurement(self) -> int:
        """Simula uma medição local."""
        classical_result = self.owner.get_generator().integers(2)
        return classical_result
    
    def acept_ghz(self, src: str):
        """Envia uma mensagem ao hub para aceitar a proposta GHZ."""
        msg = GHZMessage(
            msg_type=GHZMessageType.ACEPT_GHZ,
            receiver=self.hub_app_name
        )
        self.owner.send_message(self.hub_name, msg)
        log.logger.info(f"{self.owner.name} app accepted GHZ proposal from {src}")
    
    def received_message(self, src: str, msg: Message):
        """Delega o tratamento da mensagem para o estado atual."""
        self._state.handle_message(src, msg)
    
    def start(self):
        """Método de início não utilizado neste modelo."""
        pass
    
    def get_other_reservation(self, reservation):
        """Callback para solicitações de reserva."""
        log.logger.info(f"{self.owner.name} app received reservation request from {reservation.initiator}")
