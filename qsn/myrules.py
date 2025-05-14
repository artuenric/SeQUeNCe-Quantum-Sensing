from sequence.entanglement_management.generation import EntanglementGenerationA
from sequence.resource_management.rule_manager import Rule

def handshake_rule_condition(memory_info, args):
    return [memory_info] if memory_info.state == "RAW" else []

def handshake_rule_action(memories_info, args):
    memory = memories_info[0].memory
    remote_node = args["remote_node"]
    session_id = args["session_id"]

    protocol = EntanglementGenerationA(
        memory.owner, 
        name=f"EPR_{remote_node}_{session_id}",
        memory=memory,
        remote_node=remote_node,
        remote_memory=None  # pode ser definido via mensagem depois
    )
    memory.owner.protocols.append(protocol)
    protocol.start()

rule = Rule(
    priority=10,
    action=handshake_rule_action,
    condition=handshake_rule_condition,
    action_args={"remote_node": "B", "session_id": "sess123"},
    condition_args={}
)

