from sequence.utils import log
from sequence.protocol import Protocol
from sequence.message import Message

class EntanglamentResponderApp(Protocol):
    """Uma aplicação/protocolo para nós sensores.
    Reage a solicitações de emaranhamento de um hub.
    """
    def __init__(self, owner, name: str):
        super().__init__(owner, name)

    def get_other_reservation(self, reservation):
        log.logger.info(f"{self.owner.name} app received reservation request from {reservation.initiator}")
        pass

    def get_memory(self, info):
        if info.state == "ENTANGLED":
            log.logger.info(f"{self.owner.name} app successfully entangled with {info.remote_node}")

    def start(self):
        pass
    
    # Métodso obrigatórios da classe Protocol, mas não utilizados
    def received_message(self, src: str, msg: Message):
        """
        Método obrigatório pela herança de 'Protocol'.
        Lida com mensagens clássicas direcionadas a este protocolo.
        Para nosso fluxo atual, não há lógica necessária aqui.
        """
        pass