from abc import ABC, abstractmethod
from sequence.message import Message

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
