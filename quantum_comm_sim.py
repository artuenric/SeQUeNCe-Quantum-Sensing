import math
import random

from sequence.kernel.timeline import Timeline
from sequence.kernel.event import Event
from sequence.kernel.process import Process
from sequence.components.memory import Memory
from sequence.components.optical_channel import QuantumChannel
from sequence.components.detector import Detector
from sequence.topology.node import Node

import sequence.utils.log as log

# Simulation parameters
NUM_TRIALS = 500  # Reduced number of trials for demonstration
FREQUENCY = 500  # Transmission frequency
CHANNEL_LOSS = 0.2  # Simulating some channel loss


class QubitCounter:
    """Enhanced counter to track successful and failed transmissions"""
    def __init__(self):
        self.successful_count = 0
        self.failed_count = 0

    def trigger(self, detector, info):
        """Increment successful detections"""
        self.successful_count += 1

    def log_failed_transmission(self):
        """Log failed transmissions"""
        self.failed_count += 1


class QuantumSender:
    """Advanced sender with more complex qubit preparation"""
    def __init__(self, owner, memory_name):
        self.owner = owner
        self.memory = owner.components[memory_name]

    def prepare_entangled_state(self):
        """Prepare a Bell state (entangled qubit)"""
        # Preparing a Bell state (equal superposition)
        return [complex(math.sqrt(1/2)), complex(math.sqrt(1/2))]

    def start(self, period):
        """Schedule qubit transmission events"""
        for i in range(NUM_TRIALS):
            # Prepare qubit
            qubit_state = self.prepare_entangled_state()
            process1 = Process(self.memory, "update_state", [qubit_state])
            
            # Schedule qubit transmission
            event1 = Event(i * period, process1)
            event2 = Event(i * period + (period / 10), Process(self.memory, "excite", ["receiver_node"]))
            
            self.owner.timeline.schedule(event1)
            self.owner.timeline.schedule(event2)


class QuantumSenderNode(Node):
    """Enhanced sender node with more robust qubit management"""
    def __init__(self, name, timeline):
        super().__init__(name, timeline)
        
        # Create quantum memory with improved parameters
        memory_name = name + ".memory"
        memory = Memory(memory_name, timeline, 
                        fidelity=0.95,  # Improved fidelity
                        frequency=FREQUENCY, 
                        efficiency=0.9,  # Higher efficiency
                        coherence_time=1e-3,  # Longer coherence time
                        wavelength=800)  # Different wavelength
        
        self.add_component(memory)
        memory.add_receiver(self)

        self.quantum_sender = QuantumSender(self, memory_name)

    def get(self, photon, **kwargs):
        """Handle received photons"""
        self.send_qubit(kwargs['dst'], photon)


class QuantumReceiverNode(Node):
    """Advanced receiver node with detailed detection"""
    def __init__(self, name, timeline):
        super().__init__(name, timeline)

        # Create high-efficiency detector
        detector_name = name + ".detector"
        detector = Detector(detector_name, timeline, efficiency=0.95)
        self.add_component(detector)
        self.set_first_component(detector_name)
        detector.owner = self

        # Enhanced counter
        self.qubit_counter = QubitCounter()
        detector.attach(self.qubit_counter)

    def receive_qubit(self, src, qubit):
        """Process received qubits"""
        # Simulate potential transmission loss
        if random.random() > CHANNEL_LOSS:
            self.components[self.first_component_name].get(qubit)
        else:
            # Log failed transmission
            self.qubit_counter.log_failed_transmission()


def run_quantum_simulation():
    """Main simulation runner"""
    runtime = 5e12  # Extended runtime
    timeline = Timeline(runtime)

    # Configure logging
    log_filename = 'quantum_comm_simulation_log'
    log.set_logger(__name__, timeline, log_filename)
    log.set_logger_level('DEBUG')
    modules = ['timeline']
    for module in modules:
        log.track_module(module)

    # Create quantum communication setup
    sender_node = QuantumSenderNode("sender_node", timeline)
    receiver_node = QuantumReceiverNode("receiver_node", timeline)
    
    # Create quantum channel with some attenuation
    quantum_channel = QuantumChannel("qc.sender.receiver", timeline, 
                                     attenuation=0.1,  # Some channel loss
                                     distance=500)  # Shorter distance
    quantum_channel.set_ends(sender_node, receiver_node.name)

    timeline.init()

    # Schedule transmission events
    period = int(1e12 / FREQUENCY)
    print(f'Transmission period: {period:,} ps')
    sender_node.quantum_sender.start(period)

    # Run simulation
    timeline.run()

    # Report results
    total_trials = receiver_node.qubit_counter.successful_count + receiver_node.qubit_counter.failed_count
    success_rate = 100 * receiver_node.qubit_counter.successful_count / total_trials
    failure_rate = 100 * receiver_node.qubit_counter.failed_count / total_trials

    print(f"\nSimulation Results:")
    print(f"Total Transmission Attempts: {total_trials}")
    print(f"Successful Transmissions: {receiver_node.qubit_counter.successful_count}")
    print(f"Failed Transmissions: {receiver_node.qubit_counter.failed_count}")
    print(f"Success Rate: {success_rate:.2f}%")
    print(f"Failure Rate: {failure_rate:.2f}%")


if __name__ == "__main__":
    run_quantum_simulation()
