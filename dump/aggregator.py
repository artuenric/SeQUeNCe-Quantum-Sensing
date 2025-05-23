from sequence.topology.node import QuantumRouter, BSMNode, Node
from sequence.kernel.timeline import Timeline
class AggregatorNode(QuantumRouter):
    """
    O Aggregator é um nó que estabelece conexões EPR entre hubs e cria estados GHZ para sensores.
    Ele gerencia a memória e a comunicação entre os nós.
    """
    def __init__(self, name: str, tl): 
        super().__init__(name, tl)
        self.bsm_nodes = []

    def add_sensor(self, sensor: "sensor"):
        """
        Cria um novo BSMNode para o sensor que será adicionado. E coloca na lista de BSMNodes
        """
        bsm_node = BSMNode(f"bsm_to_{sensor.name}", self.tl, [self.name, sensor.name])
        self.bsm_nodes.append(bsm_node)
        sensor.connect_to_bsm_node(bsm_node)
    
    def entangle_to_aggregator(self, remote_node):
        pass

class SensorNode(Node):
    pass


