from sequence.utils import log
from sequence.protocol import Protocol
from sequence.message import Message
from .message_ghz_active import GHZMessageType, GHZMessage
from sequence.components.circuit import Circuit

class EntanglamentResponderApp(Protocol):
    """Uma aplicação/protocolo para nós sensores.
    Reage a solicitações de emaranhamento de um hub.
    """
    def __init__(self, owner):
        name = f"{owner.name}-ghz-app"
        super().__init__(owner, name)
        self.owner.protocols.append(self)
        self.hub_name = None
        self.hub_app_name = None
        self.requests = {}

    def set_hub_name(self, hub_name):
        self.hub_name = hub_name
        self.hub_app_name = f"{hub_name}-ghz-app"
        log.logger.info(f"{self.owner.name} app set hub to {hub_name}")
    
    def get_other_reservation(self, reservation):
        log.logger.info(f"{self.owner.name} app received reservation request from {reservation.initiator}")
        pass

    def get_memory(self, info):
        if info.state == "ENTANGLED":
            log.logger.info(f"{self.owner.name} app successfully entangled with {info.remote_node}")
        elif info.state == "RAW":
            log.logger.info(f"{self.owner.name} memory is now RAW")
        
        self.send_status_update(info)

    def send_status_update(self, info):
        """
        Callback para atualizações de status de memória.
        Caso a memória esteja em estado RAW, envia uma mensagem de atualização de status para o Hub. Por que o hub vai decidir se deve executar o plano B ou não.
        """
        if info.state == "RAW":
            msg = GHZMessage(
                msg_type=GHZMessageType.STATUS_UPDATE,
                receiver=self.hub_app_name,
                status="RAW"
                )
            self.owner.send_message(self.hub_name, msg)
            log.logger.info(f"{self.owner.name} app sent status RAW update to {self.hub_app_name} on node {self.hub_name}.")
    
    def local_measurement(self):
        """
        Simula uma medição local gerando um bit clássico aleatório e o envia para o Hub.
        """
        classical_result = self.owner.get_generator().integers(2)
        return classical_result
    
    def fallback(self):
        """
        Envia o resultado clássico da medição local para o Hub como um fallback.
        """
        log.logger.info(f"{self.owner.name} app executing fallback by sending classical result to Hub.")
        classical_result = self.local_measurement()
        msg = GHZMessage(
            GHZMessageType.CLASSICAL_FALLBACK, 
            self.hub_app_name, 
            classical_result=classical_result
            )
        self.owner.send_message(self.hub_name, msg)
        log.logger.info(f"{self.owner.name} sent classical result {classical_result} to app '{self.hub_app_name}' on node {self.hub_name}.")
    
    def start(self):
        pass
    
    def acept_ghz(self, src: str):
        """
        Método chamado quando o Hub aceita a proposta de GHZ.
        """
        log.logger.info(f"{self.owner.name} app accepted GHZ proposal from {src}.")
        msg = GHZMessage(
                msg_type=GHZMessageType.ACEPT_GHZ,
                receiver=self.hub_app_name
            )
        self.owner.send_message(self.hub_name, msg)
        log.logger.info(f"{self.owner.name} app accepted GHZ proposal from {src}")
    
    # Métodso obrigatórios da classe Protocol, mas não utilizados
    def received_message(self, src: str, msg: Message):
        if msg.msg_type == GHZMessageType.PROPOSE_GHZ:
            self.acept_ghz(src)
            self.set_hub_name(src)
        elif msg.msg_type == GHZMessageType.ATTEMPT_FAILED:
            self.fallback()
        else:
            log.logger.warning(f"{self.owner.name} app received unknown message type {msg.msg_type} from {src}")