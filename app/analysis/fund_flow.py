from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.bitcoin_rpc import BitcoinRPC


@dataclass
class FlowNode:
    txid: str
    depth: int
    direction: str
    block_height: int | None = None
    value_btc: float | None = None


class FundFlowTracer:
    """
    Trace Bitcoin transaction relationships using block data from Bitcoin Core.

    This implementation is compatible with a pruned node and does not require
    txindex. It uses getblock(..., verbosity=3) so that input prevout metadata
    can be examined directly.

    If historical blocks required for deeper tracing have already been pruned,
    the tracer returns the partial flow discovered so far instead of failing
    the entire investigation.

    The tracer does not infer ownership, identity, or criminal attribution.
    """

    def __init__(self, rpc: BitcoinRPC | None = None) -> None:
        self.rpc = rpc or BitcoinRPC()

    def trace_backward_from_block(
        self,
        txid: str,
        block_hash: str,
        max_depth: int = 2,
    ) -> list[FlowNode]:

        results: list[FlowNode] = []
        visited: set[str] = set()

        def walk(
            current_txid: str,
            current_block_hash: str,
            depth: int,
        ) -> None:

            if depth > max_depth or current_txid in visited:
                return

            visited.add(current_txid)

            try:
                block = self.rpc.get_block(
                    current_block_hash,
                    verbosity=3,
                )
            except RuntimeError:
                # The block may have been pruned. Stop this branch while
                # preserving any flow nodes already discovered.
                return

            transactions = block.get("tx", [])

            transaction = next(
                (
                    item
                    for item in transactions
                    if item.get("txid") == current_txid
                ),
                None,
            )

            if transaction is None:
                return

            for item in transaction.get("vin", []):
                previous_txid = item.get("txid")
                prevout = item.get("prevout")

                if not previous_txid or not isinstance(prevout, dict):
                    continue

                previous_height = prevout.get("height")
                previous_value = prevout.get("value")

                results.append(
                    FlowNode(
                        txid=previous_txid,
                        depth=depth,
                        direction="backward",
                        block_height=previous_height,
                        value_btc=(
                            float(previous_value)
                            if previous_value is not None
                            else None
                        ),
                    )
                )

                if (
                    previous_height is not None
                    and depth < max_depth
                ):
                    try:
                        previous_block_hash = self.rpc.get_block_hash(
                            int(previous_height)
                        )

                        walk(
                            current_txid=previous_txid,
                            current_block_hash=previous_block_hash,
                            depth=depth + 1,
                        )

                    except RuntimeError:
                        # The previous block may no longer be available
                        # because the Bitcoin Core node is pruned.
                        continue

        walk(
            current_txid=txid.strip(),
            current_block_hash=block_hash,
            depth=1,
        )

        return results