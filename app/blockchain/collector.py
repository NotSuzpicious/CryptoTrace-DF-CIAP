from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.bitcoin_rpc import BitcoinRPC
from app.blockchain.evidence_store import BlockchainEvidenceStore


@dataclass
class AcquisitionResult:
    start_height: int
    end_height: int
    blocks_processed: int
    transactions_stored: int
    failed_blocks: int


class BlockchainCollector:
    """
    Acquire Bitcoin block and transaction evidence from Bitcoin Core
    and preserve it in the local SQLite evidence store.
    """

    def __init__(
        self,
        rpc: BitcoinRPC | None = None,
        store: BlockchainEvidenceStore | None = None,
    ) -> None:
        self.rpc = rpc or BitcoinRPC()
        self.store = store or BlockchainEvidenceStore()

    def acquire_block(self, height: int) -> int:
        """
        Acquire one block and preserve all transactions contained in it.

        Returns the number of transactions stored.
        """

        block_hash = self.rpc.get_block_hash(height)

        block = self.rpc.get_block(
            block_hash,
            verbosity=3,
        )

        transactions = block.get("tx", [])

        stored = 0

        for transaction in transactions:
            if not isinstance(transaction, dict):
                continue

            self.store.save_transaction(
                transaction,
                block_hash=block_hash,
                block_height=height,
            )

            stored += 1

        return stored

    def acquire_range(
        self,
        start_height: int,
        end_height: int,
    ) -> AcquisitionResult:

        if start_height < 0:
            raise ValueError("Start height cannot be negative.")

        if end_height < start_height:
            raise ValueError(
                "End height must be greater than or equal to start height."
            )

        blocks_processed = 0
        transactions_stored = 0
        failed_blocks = 0

        for height in range(start_height, end_height + 1):
            try:
                stored = self.acquire_block(height)

                blocks_processed += 1
                transactions_stored += stored

            except Exception:
                failed_blocks += 1

        return AcquisitionResult(
            start_height=start_height,
            end_height=end_height,
            blocks_processed=blocks_processed,
            transactions_stored=transactions_stored,
            failed_blocks=failed_blocks,
        )