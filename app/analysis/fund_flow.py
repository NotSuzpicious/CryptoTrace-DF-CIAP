from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.bitcoin_rpc import BitcoinRPC
from app.blockchain.evidence_store import BlockchainEvidenceStore


@dataclass
class FlowNode:
    txid: str
    depth: int
    direction: str
    block_height: int | None = None
    value_btc: float | None = None


class FundFlowTracer:
    """
    Trace Bitcoin transaction relationships using preserved local evidence
    with Bitcoin Core as a fallback acquisition source.

    Local SQLite evidence is preferred. If a transaction is not preserved,
    Bitcoin Core is queried when the required block is available.

    The tracer does not infer ownership, identity, or criminal attribution.
    """

    def __init__(
        self,
        rpc: BitcoinRPC | None = None,
        evidence_store: BlockchainEvidenceStore | None = None,
    ) -> None:
        self.rpc = rpc or BitcoinRPC()
        self.evidence_store = evidence_store or BlockchainEvidenceStore()

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
            current_block_hash: str | None,
            depth: int,
        ) -> None:

            if depth > max_depth or current_txid in visited:
                return

            visited.add(current_txid)

            # ---------------------------------------------------------
            # 1. Prefer locally preserved forensic evidence.
            # ---------------------------------------------------------
            stored = self.evidence_store.get_transaction(current_txid)

            if stored is not None:
                inputs = stored["inputs"]

                for item in inputs:
                    previous_txid = item.get("previous_txid")

                    if not previous_txid:
                        continue

                    previous_height = item.get("previous_block_height")
                    previous_value = item.get("value_btc")

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
                        depth < max_depth
                        and previous_height is not None
                    ):
                        previous_transaction = (
                            self.evidence_store.get_transaction(
                                previous_txid
                            )
                        )

                        previous_block_hash = None

                        if previous_transaction is not None:
                            previous_block_hash = (
                                previous_transaction["transaction"]
                                .get("block_hash")
                            )

                        if previous_block_hash:
                            walk(
                                current_txid=previous_txid,
                                current_block_hash=previous_block_hash,
                                depth=depth + 1,
                            )

                return

            # ---------------------------------------------------------
            # 2. Fall back to Bitcoin Core when local evidence is absent.
            # ---------------------------------------------------------
            if not current_block_hash:
                return

            try:
                block = self.rpc.get_block(
                    current_block_hash,
                    verbosity=3,
                )
            except RuntimeError:
                # Historical block may have been pruned.
                return

            transactions = block.get("tx", [])

            transaction = next(
                (
                    item
                    for item in transactions
                    if isinstance(item, dict)
                    and item.get("txid") == current_txid
                ),
                None,
            )

            if transaction is None:
                return

            # Preserve the transaction we just acquired so future
            # investigations do not depend on Bitcoin Core retaining it.
            try:
                current_height = block.get("height")

                self.evidence_store.save_transaction(
                    transaction,
                    block_hash=current_block_hash,
                    block_height=current_height,
                )
            except Exception:
                pass

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
                    depth < max_depth
                    and previous_height is not None
                ):
                    # First try to obtain the previous transaction's
                    # block from the local evidence store.
                    previous_transaction = (
                        self.evidence_store.get_transaction(
                            previous_txid
                        )
                    )

                    if previous_transaction is not None:
                        previous_block_hash = (
                            previous_transaction["transaction"]
                            .get("block_hash")
                        )

                        walk(
                            current_txid=previous_txid,
                            current_block_hash=previous_block_hash,
                            depth=depth + 1,
                        )
                        continue

                    # Otherwise fall back to Bitcoin Core.
                    try:
                        previous_block_hash = self.rpc.get_block_hash(
                            int(previous_height)
                        )
                    except RuntimeError:
                        continue

                    walk(
                        current_txid=previous_txid,
                        current_block_hash=previous_block_hash,
                        depth=depth + 1,
                    )

        walk(
            current_txid=txid.strip(),
            current_block_hash=block_hash,
            depth=1,
        )

        return results