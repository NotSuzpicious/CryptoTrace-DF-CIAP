from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.evidence import TransactionEvidence


@dataclass
class TransactionSummary:
    txid: str
    is_coinbase: bool
    input_count: int
    output_count: int
    total_output_btc: float
    size: int
    virtual_size: int
    weight: int
    confirmations: int | None
    block_time: int | None


def examine_transaction(evidence: TransactionEvidence) -> TransactionSummary:
    total_output_btc = 0.0

    for output in evidence.outputs:
        value = output.get("value", 0)
        try:
            total_output_btc += float(value)
        except (TypeError, ValueError):
            continue

    return TransactionSummary(
        txid=evidence.txid,
        is_coinbase=evidence.is_coinbase,
        input_count=len(evidence.inputs),
        output_count=len(evidence.outputs),
        total_output_btc=total_output_btc,
        size=evidence.size,
        virtual_size=evidence.virtual_size,
        weight=evidence.weight,
        confirmations=evidence.confirmations,
        block_time=evidence.block_time,
    )