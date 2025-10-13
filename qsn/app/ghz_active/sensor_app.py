from abc import ABC, abstractmethod
from sequence.utils import log
from sequence.protocol import Protocol
from sequence.message import Message
from .message_ghz_active import GHZMessageType, GHZMessage


# Passo 2: Criação da Estrutura de Estados
class SensorState(ABC):
    """Classe base abstrata para os estados do sensor."""
    def __init__(self, app):
        self.app = app

    @abstractmethod
    def handle_message(self, src: str, msg: Message):
        """Lida com mensagens recebidas, dependendo do estado atual."""
        pass

    def enter(self):
        """Método opcional para executar na entrada do estado."""
        pass


# Passo 3: Implementação do Estado Normal (Plano A)
class NormalState(SensorState):
    """Estado normal de operação, aguardando propostas GHZ."""
    def handle_message(self, src: str, msg: Message):
        if msg.msg_type == GHZMessageType.PROPOSE_GHZ:
            self.app.set_hub_name(src)
            self.app.acept_ghz(src)
        elif msg.msg_type == GHZMessageType.ATTEMPT_FAILED:
            log.logger.info(f"{self.app.owner.name} received ATTEMPT_FAILED. Transitioning to FallbackState.")
            self.app.transition_to(FallbackState(self.app))
        else:
            log.logger.warning(f"{self.app.owner.name} app received unknown message type {msg.msg_type} in NormalState from {src}")


# Passo 4: Implementação do Estado de Fallback (Plano B)
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


# Passo 1 e 5: Unificação e Transformação de SensorApp no Contexto
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
