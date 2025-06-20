from sequence.kernel.timeline import Timeline
from sequence.topology.node import Node, BSMNode, QuantumRouter
from sequence.components.memory import Memory
from sequence.components.optical_channel import QuantumChannel, ClassicalChannel

import sequence.utils.log as log

tl = Timeline(1e20)
q1 = QuantumRouter("q1", tl, seed=1)
q2 = QuantumRouter("q2", tl, seed=2)
bsm = BSMNode("bsm", tl, [q1.name, q2.name])

qc_q1_bsm = QuantumChannel("qc_q1_bsm", tl, attenuation=0, distance=10)
qc_q1_bsm.set_ends(q1, bsm.name)

qc_q1_q2 = QuantumChannel("qc_q1_q2", tl, attenuation=0, distance=10)
qc_q1_q2.set_ends(q1, q2.name)

qc_q2_bsm = QuantumChannel("qc_q2_bsm", tl, attenuation=0, distance=10)
qc_q2_bsm.set_ends(q2, bsm.name)

cc_q1_bsm = ClassicalChannel("cc_q1_bsm", tl, distance=10)
cc_q1_bsm.set_ends(q1, bsm.name)

cc_q1_q2 = ClassicalChannel("cc_q1_q2", tl, distance=10)
cc_q1_q2.set_ends(q1, q2.name)

cc_q2_bsm = ClassicalChannel("cc_q2_bsm", tl, distance=10)
cc_q2_bsm.set_ends(q2, bsm.name)

print(f"Canais quanticos q1: {q1.qchannels}")
print(f"Canais quanticos q2: {q2.qchannels}\n")

print(f"Canais classicos q1: {q1.cchannels}")
print(f"Canais classicos q2: {q2.cchannels}\n")


print("Network Manager: ", q1.network_manager, end="\n\n")

nm = q1.network_manager
nm.request(q2.name, start_time=1e12, end_time=10e12, memory_size=5, target_fidelity=0.9)







tl.run()
# tentativa de log
log_filename = 'qr_log'
log.set_logger(__name__, tl, log_filename)
log.set_logger_level('DEBUG')
modules = ['timeline']
for module in modules:
    log.track_module(module)