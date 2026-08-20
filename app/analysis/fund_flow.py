from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.bitcoin_rpc import BitcoinRPC


@dataclass
class FlowNode:
    txid: str
    depth: int
    direction: str


class FundFlowTracer:
    """
    Trace Bitcoin transaction relationships backward through inputs
    and forward through known child transactions where available.

    The tracer operates on transaction IDs only and does not infer
    ownership, identity, or criminal attribution.
    """

    def __init__(self, rpc: BitcoinRPC | None = None) -> None:
        self.rpc = rpc or BitcoinRPC()

    def trace_backward(
        self,
        txid: str,
        block_hash: str | None = None,
        max_depth: int = 2,
    ) -> list[FlowNode]:

        results: list[FlowNode] = []
        visited: set[str] = set()

        def walk(
            current_txid: str,
            current_block_hash: str | None,
            depth: int,
        ) -> None:

            if depth > max_depth or current_txid in visited:
                return

            visited.add(current_txid)

            transaction = self.rpc.get_raw_transaction(
                current_txid,
                verbose=True,
                block_hash=current_block_hash,
            )

            if not isinstance(transaction, dict):
                return

            for item in transaction.get("vin", []):
                previous_txid = item.get("txid")

                if not previous_txid:
                    continue

                results.append(
                    FlowNode(
                        txid=previous_txid,
                        depth=depth,
                        direction="backward",
                    )
                )

                walk(
                    current_txid=previous_txid,
                    current_block_hash=None,
                    depth=depth + 1,
                )

        walk(
            current_txid=txid.strip(),
            current_block_hash=block_hash,
            depth=1,
        )

        return results