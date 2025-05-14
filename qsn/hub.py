from sequence.entanglement_management.generation import EntanglementGenerationA
from sequence.resource_management.rule_manager import Rule
from sequence.resource_management.resource_manager import ResourceManager

# condition
def epr_condition(memory_info, args):
    return [memory_info] if memory_info.state == "RAW" else []
# action
def epr_action(memories_info, args):
    memory = memories_info[0].memory
    remote_node = args["remote_node"]
    session_id = args["session_id"]
    remote_memory = args["remote_memory"]
    
    protocol = EntanglementGenerationA(
        # Ver certinho
        )
    
    # adiciona o protocolo ao nó
    memory.owner.protocols.append(protocol)
    # inicia o protoclo de geração de entrelaçamento
    protocol.start()
        
    
from sequence.topology.node import QuantumRouter

class AggregatorNode(QuantumRouter):
    """
    O Aggregator é um nó que estabelece conexões EPR entre hubs e cria estados GHZ para sensores.
    Ele gerencia a memória e a comunicação entre os nós.
    """
    def __init__(self, name: str, tl): 
        super().__init__(name, tl)
    
    def __init__(self, name, timeline):
        super().__init__(name, timeline, memo_size=10)  # Substituindo MemoryArray manual
        self.resource_manager = ResourceManager(self, f"{self.name}.memory_array")
    
    def create_epr_protocol(self, remote_node: "node"):
        pass
    
    def create_ghz_protocol(self, remote_node: "node"):
        pass
    
    