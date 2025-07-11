from sequence.utils import log
from sequence.protocol import Protocol
from sequence.message import Message
from .message_ghz_active import GHZMessageType, GHZMessage
from sequence.components.circuit import Circuit

class SensorGHZActiveFallBackApp(Protocol):
    """Uma aplicação/protocolo para nós sensores.
    Reage a solicitações de emaranhamento de um hub.
    """
    def __init__(self, owner, hub_name):
        name = f"{owner.name}-ghz-fallback-app"
        super().__init__(owner, name)
        self.owner.protocols.append(self)
        self.hub_name = hub_name
        self.hub_app_name = f"{hub_name}-ghz-app"
    
    def get_other_reservation(self, reservation):
        pass

    def get_memory(self, info):
        pass
    
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
        log.logger.info(f"{self.owner.name} sent classical result {classical_result} to node {self.hub_name}.")
    
    def start(self):
        log.logger.info(f"{self.owner.name} app starting fallback process.")
        self.fallback()
    
    # Métodso obrigatórios da classe Protocol, mas não utilizados
    def received_message(self, src: str, msg: Message):
        pass