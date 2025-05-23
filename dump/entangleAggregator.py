"""
Esse script cria uma classe para um nó, que chamei de aggregator. Essa classe herda de Node. Assim, o entrelaçamento deve ocorrer de forma MUITO manual. Por isso, é necessário adicionar manualmente a memória. Uma alternativa seria herdar de de QuantumRouter e, ao invés de criar os protocolos, apenas usar os requests do network manager.

Não funciona :(
"""

from sequence.kernel.timeline import Timeline
from sequence.components.optical_channel import QuantumChannel, ClassicalChannel
from sequence.topology.node import BSMNode, Node, QuantumRouter
from sequence.components.memory import Memory
from sequence.entanglement_management.generation import EntanglementGenerationA


class MyManager():
    def __init__(self, owner, memo_name):
        self.owner = owner
        self.memo_name = memo_name
        self.raw_counter = 0
        self.ent_counter = 0

    def update(self, protocol, memory, state):
        if state == 'RAW':
            self.raw_counter += 1
            memory.reset()
        else:
            self.ent_counter += 1

class AggregatorNode(Node):
    """
    O Aggregator é um nó que estabelece conexões EPR entre hubs e cria estados GHZ para sensores.
    Ele gerencia a memória e a comunicação entre os nós.
    """
    def __init__(self, name: str, tl: Timeline): 
        super().__init__(name, tl)
        # Adiciona as memórias
        memo_name = f"{name}.memo"
        memory = Memory(memo_name, tl, 0.9, 2000, 1, -1, 500)
        memory.add_receiver(self)
        self.add_component(memory)
        
        self.resource_manager = MyManager(self, memo_name)
    def init(self):
        memory = self.get_components_by_type("Memory")[0]
        memory.reset()

    def receive_message(self, src: str, msg: "Message") -> None:
        self.protocols[0].received_message(src, msg)
    
    def get(self, photon, **kwargs):
        self.send_qubit(kwargs['dst'], photon)
        
# Cria a timeline
tl = Timeline(1e120)
tl.init()
# Cria os três nós Aggregator 
node1 = AggregatorNode("node1", tl)
node2 = AggregatorNode("node2", tl)

# Define o seed para os nós, garantindo determinismo
node1.set_seed(1)
node2.set_seed(2)

# Cria o BSM node que será usado para medição entre os aggregators
bsm = BSMNode("bsm", tl, [node1.name, node2.name])

# Canais quânticos entre os nodes e o BSM
qc1bsm = QuantumChannel("qc1_bsm", tl, attenuation=0, distance=1000)
qc2bsm = QuantumChannel("qc2_bsm", tl, attenuation=0, distance=1000)
qc1bsm.set_ends(node1, bsm.name)
qc2bsm.set_ends(node2, bsm.name)

nodes = [node1, node2, bsm]

for i in range(3):
    for j in range(3):
        if i != j:
            cc = ClassicalChannel('cc_%s_%s' % (nodes[i].name, nodes[j].name), tl, 1000, 1e8)
            cc.set_ends(nodes[i], nodes[j].name)

m1 = node1.get_components_by_type("Memory")[0]
m2 = node2.get_components_by_type("Memory")[0]


print(f"Memória 1: {m1.name} do nó {node1.name}")
print(f"Memória 2: {m2.name} do nó {node2.name}")


p1 = EntanglementGenerationA(
    node1,
    node1.name+'.eg',
    bsm.name,
    node2.name,
    m1 # pro protocolo, é a própria memória do nó
)
p2 = EntanglementGenerationA(
    node2,
    node2.name+'.eg',
    bsm.name,
    node1.name,
    m2 # pro protocolo, é a própria memória do nó
)

node1.protocols = [p1]
node2.protocols = [p2]

memory1 = node1.get_components_by_type("Memory")[0]
memory1.reset()
memory2 = node2.get_components_by_type("Memory")[0]
memory2.reset()

print(f"Protocolo 1: {p1.name} do nó {node1.name}")
print(f"Protocolo 2: {p2.name} do nó {node2.name}")

print("Canais quânticos do nó 1:")
print(node1.qchannels)
print("Canais quânticos do nó 2:")
print(node2.qchannels)

p1.set_others(p2.name, node2.name, [m2.name]) # pro set_others, é lista de nomes de memórias
p2.set_others(p1.name, node1.name, [m1.name]) # pro set_others, é lista de nomes de memórias

node1.protocols[0].start()
node2.protocols[0].start()

tl.run()