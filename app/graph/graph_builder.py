from __future__ import annotations

from pathlib import Path
import pandas as pd
import networkx as nx

class TransactionGraph:
    def __init__(self, edge_path: str | Path):
        edges = pd.read_csv(edge_path, usecols=["txId1", "txId2"])
        self.graph = nx.DiGraph()
        self.graph.add_edges_from(edges.itertuples(index=False, name=None))

    def contains(self, tx_id: int) -> bool:
        return self.graph.has_node(tx_id)

    def neighborhood(self, tx_id: int, hops: int = 1) -> nx.DiGraph:
        if not self.contains(tx_id):
            return nx.DiGraph()
        nodes = {tx_id}
        frontier = {tx_id}
        for _ in range(max(1, min(hops, 3))):
            frontier = {neighbor for node in frontier for neighbor in self.graph.predecessors(node)} | {neighbor for node in frontier for neighbor in self.graph.successors(node)}
            nodes |= frontier
        return self.graph.subgraph(nodes).copy()

    def flow(self, tx_id: int, direction: str = "forward", depth: int = 3) -> list[list[int]]:
        if not self.contains(tx_id): return []
        follow = self.graph.successors if direction == "forward" else self.graph.predecessors
        paths = []
        def walk(path: list[int]) -> None:
            if len(path) > depth: paths.append(path); return
            next_nodes = list(follow(path[-1]))
            if not next_nodes: paths.append(path); return
            for node in next_nodes[:25]:
                if node not in path: walk(path + [node])
        walk([tx_id])
        return paths[:100]

    def stats(self, tx_id: int) -> dict[str, int]:
        if not self.contains(tx_id): return {"in_degree": 0, "out_degree": 0}
        return {"in_degree": self.graph.in_degree(tx_id), "out_degree": self.graph.out_degree(tx_id)}
