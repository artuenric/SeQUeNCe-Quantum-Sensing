from sequence.kernel.timeline import Timeline
from sequence.components.optical_channel import QuantumChannel, ClassicalChannel
from sequence.topology.node import QuantumRouter, BSMNode, Node
from aggregator import AggregatorNode

# Cria a timeline com duração de simulação
tl = Timeline(1e12)
tl.show_progress = True

# Cria os seis nós
node1 = AggregatorNode("Node1", tl)
node2 = AggregatorNode("Node2", tl)
node3 = AggregatorNode("Node3", tl)
node4 = AggregatorNode("Node4", tl)
node5 = AggregatorNode("Node5", tl)
node6 = AggregatorNode("Node6", tl)
node1.set_seed(1)
node2.set_seed(2)
node3.set_seed(3)
node4.set_seed(4)
node5.set_seed(5)
node6.set_seed(6)

# Cria os nós BSM
bsm12 = BSMNode("bsm_1_2", tl, [node1.name, node2.name])
bsm14 = BSMNode("bsm_1_4", tl, [node1.name, node4.name])
bsm23 = BSMNode("bsm_2_3", tl, [node2.name, node3.name])
bsm25 = BSMNode("bsm_2_5", tl, [node2.name, node5.name])
bsm34 = BSMNode("bsm_3_4", tl, [node3.name, node4.name])
bsm45 = BSMNode("bsm_4_5", tl, [node4.name, node5.name])
bsm56 = BSMNode("bsm_5_6", tl, [node5.name, node6.name])

# Conecta os canais quânticos (bidirecional, mas só 1 sentido necessário se for simples)
qc12 = QuantumChannel("qc_1_2", tl, attenuation=0, distance=1000)
qc12.set_ends(node1, bsm12.name)
qc12.set_ends(bsm12, node2.name)

qc14 = QuantumChannel("qc_1_4", tl, attenuation=0, distance=1000)
qc14.set_ends(node1, bsm14.name)
qc14.set_ends(bsm14, node4.name)

qc23 = QuantumChannel("qc_2_3", tl, attenuation=0, distance=1000)
qc23.set_ends(node2, bsm23.name)
qc23.set_ends(bsm23, node3.name)

qc25 = QuantumChannel("qc_2_5", tl, attenuation=0, distance=1000)
qc25.set_ends(node2, bsm25.name)
qc25.set_ends(bsm25, node5.name)

qc34 = QuantumChannel("qc_3_4", tl, attenuation=0, distance=1000)
qc34.set_ends(node3, bsm34.name)
qc34.set_ends(bsm34, node4.name)

qc45 = QuantumChannel("qc_4_5", tl, attenuation=0, distance=1000)
qc45.set_ends(node4, bsm45.name)
qc45.set_ends(bsm45, node5.name)

qc56 = QuantumChannel("qc_5_6", tl, attenuation=0, distance=1000)
qc56.set_ends(node5, bsm56.name)
qc56.set_ends(bsm56, node6.name)