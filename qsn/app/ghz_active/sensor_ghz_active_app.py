from sequence.utils import log
from sequence.protocol import Protocol
from sequence.message import Message
from .message_ghz_active import GHZMessageType, GHZMessage
from sequence.components.circuit import Circuit
from .sensor_ghz_active_fallback_app import SensorGHZActiveFallBackApp

class SensorGHZActiveApp(Protocol):
    """Uma aplicação/protocolo para nós sensores.
    Reage a solicitações de emaranhamento de um hub.
    """
    def __init__(self, owner):
        name = f"{owner.name}-ghz-app"
        super().__init__(owner, name)
        self.owner.protocols.append(self)
        self.hub_name = None
        self.hub_app_name = None

    def set_hub_name(self, hub_name):
        self.hub_name = hub_name
        self.hub_app_name = f"{hub_name}-ghz-app"
        log.logger.info(f"{self.owner.name} app set hub to {hub_name}")
    
    def get_other_reservation(self, reservation):
        log.logger.info(f"{self.owner.name} app received reservation request from {reservation.initiator}")

    def get_memory(self, info):
        self.send_status(info)

    def send_status(self, info):
        """
        Callback para atualizações de status de memória.
        Caso a memória esteja em estado RAW, envia uma mensagem de atualização de status para o Hub. Por que o hub vai decidir se deve executar o plano B ou não.
        """
        msg = GHZMessage(
                msg_type=GHZMessageType.STATUS_UPDATE,
                receiver=self.hub_app_name,
                status=info.state
                )
        self.owner.send_message(self.hub_name, msg)
        log.logger.info(f"{self.owner.name} sent status {info.state} update to {self.hub_name}")
            
    def local_measurement(self):
        """
        Simula uma medição local gerando um bit clássico aleatório e o envia para o Hub.
        """
        classical_result = self.owner.get_generator().integers(2)
        return classical_result
    
    def start(self):
        pass
    
    def acept_ghz(self, src: str):
        """
        Método chamado quando o Hub aceita a proposta de GHZ.
        """
        msg = GHZMessage(
                msg_type=GHZMessageType.ACEPT_GHZ,
                receiver=self.hub_app_name
            )
        self.owner.send_message(self.hub_name, msg)
        log.logger.info(f"{self.owner.name} app accepted GHZ proposal from {src}")
    
    def fallback(self):
        app = SensorGHZActiveFallBackApp(self.owner, self.hub_name)
        self.owner.set_app(app)
        self.owner.app.start()
        self.owner.protocols.remove(self)
    
    # Métodso obrigatórios da classe Protocol, mas não utilizados
    def received_message(self, src: str, msg: Message):
        if msg.msg_type == GHZMessageType.PROPOSE_GHZ:
            self.set_hub_name(src)
            self.acept_ghz(src)
        elif msg.msg_type == GHZMessageType.ATTEMPT_FAILED:
            self.fallback()
        else:
            log.logger.warning(f"{self.owner.name} app received unknown message type {msg.msg_type} from {src}")