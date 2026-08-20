from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class TransactionEvidence:
    txid: str
    block_hash: str | None
    confirmations: int | None
    block_time: int | None
    version: int
    size: int
    virtual_size: int
    weight: int
    locktime: int
    inputs: list[dict[str, Any]]
    outputs: list[dict[str, Any]]


def transaction_from_rpc(data: dict[str, Any]) -> TransactionEvidence:
    return TransactionEvidence(
        txid=str(data.get("txid", "")),
        block_hash=data.get("blockhash"),
        confirmations=data.get("confirmations"),
        block_time=data.get("blocktime"),
        version=int(data.get("version", 0)),
        size=int(data.get("size", 0)),
        virtual_size=int(data.get("vsize", 0)),
        weight=int(data.get("weight", 0)),
        locktime=int(data.get("locktime", 0)),
        inputs=list(data.get("vin", [])),
        outputs=list(data.get("vout", [])),
    )