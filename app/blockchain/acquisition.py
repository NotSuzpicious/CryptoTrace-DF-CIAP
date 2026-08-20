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

        raw_transaction = self.rpc.get_raw_transaction(
            txid,
            verbose=True,
            block_hash=block_hash,
        )

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