from enum import Enum, auto
from sequence.message import Message

class GHZMessageType(Enum):
    """
    Define os tipos de mensagens para nosso protocolo de criação de estado GHZ.
    
    Attributes:
        INIT: Mensagem enviada pelo Hub ao Sensor para iniciar o protocolo e informar o prazo final da requisição.
        PLANB: Mensagem enviada pelo Sensor ao Hub contendo o resultado clássico da medição local (Plano B) após uma falha.
    """
    PROPOSE_GHZ = auto() # Hub -> Sensor
    ACEPT_GHZ = auto() # Sensor -> Hub
    REJECT_GHZ = auto() # Sensor -> Hub
    STATUS_UPDATE = auto() # Sensor -> Hub
    ATTEMPT_FAILED = auto() # Hub -> Sensor
    CLASSICAL_FALLBACK = auto() # Sensor -> Hub
    

class GHZMessage(Message):
    """
    Mensagem customizada para a comunicação no protocolo GHZ.

    Attributes:
        msg_type (GHZMessageType): O tipo da mensagem, definido pelo Enum.
        payload (dict): Um dicionário flexível para carregar os dados
                        específicos de cada tipo de mensagem (ex: 'end_time', 'result').
    """
    def __init__(self, msg_type: GHZMessageType, receiver: str, **kwargs):
        """
        Construtor da GHZMessage.

        Args:
            msg_type (GHZMessageType): O tipo da mensagem.
            receiver (str): O nome do protocolo que vai receber a mensagem.
            **kwargs: Argumentos chave-valor para compor o payload da mensagem.
                      Ex: end_time=10e12, result=1.
        """
        
    def __init__(self, msg_type: GHZMessageType, receiver: str, **kwargs):
        super().__init__(msg_type, receiver)

        if msg_type is GHZMessageType.PROPOSE_GHZ:
            self.hub_name = kwargs.get("hub_name")
            self.star_time = kwargs.get("start_time")
            self.end_time = kwargs.get("end_time")
            self.num_memories = kwargs.get("num_memories")
        elif msg_type is GHZMessageType.STATUS_UPDATE:
            self.status = kwargs.get("status")
        elif msg_type is GHZMessageType.CLASSICAL_FALLBACK:
            self.classical_result = kwargs.get("classical_result")
