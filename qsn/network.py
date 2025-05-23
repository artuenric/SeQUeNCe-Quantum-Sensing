from sequence.kernel.timeline import Timeline
from dump.aggregator import AggregatorNode

# Não consigo saber o quão necessário é cada coisa que eu faço aqui.

class Network:
    def __init__(self, tl: Timeline):
        self.timeline = tl
        self.nodes = {}
    
    def create_aggregators(self, node_count: int):
        """
        Create a specified number of Aggregator nodes.
        """
        for i in range(node_count):
            node_name = f"aggregator-{i+1}"
            node = AggregatorNode(node_name, self.timeline)
            self.nodes[node_name] = node
            node.set_seed(i+1)
    
    