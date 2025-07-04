from sequence.utils import log
from sequence.protocol import Protocol
from sequence.message import Message
from sequence.components.circuit import Circuit

class EntanglamentResponderApp(Protocol):
    """Uma aplicação/protocolo para nós sensores.
    Reage a solicitações de emaranhamento de um hub.
    """
    def __init__(self, owner, name: str):
        super().__init__(owner, name)
        self.hub_name = self.set_hub_name()
        
    def set_hub_name(self):
        """Identifica o nome do Hub a partir dos canais clássicos do nó."""
        channnels = self.owner.cchannels.values()
        for channel in channnels:
            sender = channel.sender.name # Sender é sempre um nó
            receiver = channel.receiver # Receiver é sempre uma string do nome do nó
            if sender.startswith("Hub") or receiver.startswith("Hub"):
                hub_name = sender if sender.startswith("Hub") else receiver
                log.logger.info(f"{self.owner.name} app identified hub as {hub_name}.")
                return hub_name
        raise ValueError(f"{self.owner.name} app could not identify the hub name from channels: {channnels}. ")
        
    def get_other_reservation(self, reservation):
        log.logger.info(f"{self.owner.name} app received reservation request from {reservation.initiator}")
        pass
    
    def get_memory(self, info):
        # Caso a memória estiver entangled, consideramos um SUCESSO
        if info.state == "ENTANGLED":
            log.logger.info(f"{self.owner.name} app successfully entangled with {info.remote_node}")
        
        # Se a memória estava ocupada e voltou para RAW, consideramos uma FALHA
        elif info.state == "RAW" and info.remote_node == self.hub_name:
            log.logger.warning(self, f"entanglement with {self.hub_name} failed. Initiating classical fallback.")
            self.send_classical_result(info)
    
    def send_classical_result(self, info):
        """Realiza medição local e envia o resultado para o Hub."""

        # 1. Criar e executar um circuito de medição local
        circuit = Circuit(1)
        circuit.measure(0)
        
        qstate_key = info.memory.qstate_key
        meas_samp = self.owner.get_generator().random()

        # Mede o qubit local
        measurement_results = self.owner.timeline.quantum_manager.run_circuit(
            circuit=circuit,
            keys=[qstate_key],
            meas_samp=meas_samp
        )
        classical_bit = measurement_results[0]
        log.logger.info(self, f"local measurement result is {classical_bit}.")

        # 2. Criar a mensagem clássica para o Hub
        msg_content = {
            "type": "classical_fallback",
            "bit": classical_bit
        }
        msg = Message(msg_type="classical_measurement",
                      receiver=self.hub_name, # O destinatário é a App no Hub
                      content=msg_content)

        # 3. Enviar a mensagem
        self.owner.send_message(self.hub_name, msg)
        log.logger.info(self, f"sent classical result {classical_bit} to {self.hub_name}.")
    
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