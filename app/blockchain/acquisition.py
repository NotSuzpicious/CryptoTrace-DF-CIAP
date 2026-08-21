from __future__ import annotations

from app.blockchain.bitcoin_rpc import BitcoinRPC
from app.blockchain.evidence import TransactionEvidence, transaction_from_rpc


class EvidenceAcquisition:
    """Acquire blockchain evidence directly from a Bitcoin Core node."""

    def __init__(self, rpc: BitcoinRPC | None = None) -> None:
        self.rpc = rpc or BitcoinRPC()

    def acquire_transaction(
        self,
        txid: str,
        block_hash: str | None = None,
    ) -> TransactionEvidence:
        txid = txid.strip()

        if not txid:
            raise ValueError("Transaction ID cannot be empty.")

        try:
            raw_transaction = self.rpc.get_raw_transaction(
                txid,
                verbose=True,
                block_hash=block_hash,
            )

        except RuntimeError as exc:
            if not block_hash:
                raise

            # Pruned-node fallback:
            # retrieve the retained block and locate the full
            # transaction object inside the block.
            block = self.rpc.get_block(
                block_hash,
                verbosity=2,
            )

            transactions = block.get("tx", [])

            raw_transaction = next(
                (
                    transaction
                    for transaction in transactions
                    if isinstance(transaction, dict)
                    and transaction.get("txid") == txid
                ),
                None,
            )

            if raw_transaction is None:
                raise RuntimeError(
                    f"Transaction {txid} was not found in "
                    f"block {block_hash}. Original RPC error: {exc}"
                ) from exc

        if not isinstance(raw_transaction, dict):
            raise RuntimeError(
                "Bitcoin Core returned an unexpected transaction response."
            )

        evidence = transaction_from_rpc(raw_transaction)

        if not evidence.txid:
            raise RuntimeError(
                "Acquired transaction evidence does not contain a transaction ID."
            )

        return evidence

#Some random comment