from __future__ import annotations

def obfuscation_indicators(graph, tx_id: int) -> list[str]:
    if not graph.contains(tx_id): return []
    result = []; stats = graph.stats(tx_id)
    if stats["out_degree"] >= 5: result.append("Potential fan-out: the selected transaction branches to multiple downstream transactions.")
    if stats["in_degree"] >= 5: result.append("Potential fan-in: the selected transaction combines multiple upstream transactions.")
    downstream = set(graph.graph.successors(tx_id))
    for node in list(downstream)[:25]:
        if graph.graph.out_degree(node) >= 4:
            result.append("Potential rapid splitting: a downstream node branches again within one hop."); break
    upstream = set(graph.graph.predecessors(tx_id))
    for node in list(upstream)[:25]:
        if graph.graph.in_degree(node) >= 4:
            result.append("Potential rapid recombination: an upstream node combines multiple inputs."); break
    return result
