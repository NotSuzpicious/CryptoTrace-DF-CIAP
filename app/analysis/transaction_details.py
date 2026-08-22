from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.evidence import TransactionEvidence


@dataclass
class InputDetail:
    previous_txid: str | None
    previous_vout: int | None
    sequence: int | None
    is_coinbase: bool


@dataclass
class OutputDetail:
    index: int
    value_btc: float
    script_type: str | None
    address: str | None


@dataclass
class TransactionDetails:
    inputs: list[InputDetail]
    outputs: list[OutputDetail]


def extract_transaction_details(
    evidence: TransactionEvidence,
) -> TransactionDetails:

    inputs: list[InputDetail] = []

    for item in evidence.inputs:
        inputs.append(
            InputDetail(
                previous_txid=item.get("txid"),
                previous_vout=item.get("vout"),
                sequence=item.get("sequence"),
                is_coinbase="coinbase" in item,
            )
        )

    outputs: list[OutputDetail] = []

    for item in evidence.outputs:
        script = item.get("scriptPubKey", {})

        address = script.get("address")

        # Some Bitcoin Core responses may expose multiple addresses.
        if address is None:
            addresses = script.get("addresses", [])
            if addresses:
                address = addresses[0]

        try:
            value = float(item.get("value", 0))
        except (TypeError, ValueError):
            value = 0.0

        outputs.append(
            OutputDetail(
                index=int(item.get("n", 0)),
                value_btc=value,
                script_type=script.get("type"),
                address=address,
            )
        )

    return TransactionDetails(
        inputs=inputs,
        outputs=outputs,
    )