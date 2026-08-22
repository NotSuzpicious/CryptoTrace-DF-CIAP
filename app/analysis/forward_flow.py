from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.bitcoin_rpc import BitcoinRPC


@dataclass
class OutputStatus:
    txid: str
    vout: int
    value_btc: float | None
    spent: bool
    spending_txid: str | None


class ForwardFlowAnalyzer:
    """
    Examine whether transaction outputs remain unspent or have been spent.

    This uses Bitcoin Core's UTXO set and does not require txindex.
    It does not infer wallet ownership or criminal attribution.
    """

    def __init__(self, rpc: BitcoinRPC | None = None) -> None:
        self.rpc = rpc or BitcoinRPC()

    def examine_output(
        self,
        txid: str,
        vout: int,
    ) -> OutputStatus:

        transaction = self.rpc.get_raw_transaction(
            txid,
            verbose=True,
        )

        if not isinstance(transaction, dict):
            raise RuntimeError(
                "Bitcoin Core returned an unexpected transaction response."
            )

        outputs = transaction.get("vout", [])

        selected_output = next(
            (
                output
                for output in outputs
                if int(output.get("n", -1)) == vout
            ),
            None,
        )

        if selected_output is None:
            raise ValueError(
                f"Output {vout} was not found in transaction {txid}."
            )

        value = selected_output.get("value")

        value_btc = (
            float(value)
            if value is not None
            else None
        )

        try:
            utxo = self.rpc.call(
                "gettxout",
                txid,
                vout,
                True,
            )
        except RuntimeError:
            utxo = None

        if isinstance(utxo, dict):
            return OutputStatus(
                txid=txid,
                vout=vout,
                value_btc=value_btc,
                spent=False,
                spending_txid=None,
            )

        return OutputStatus(
            txid=txid,
            vout=vout,
            value_btc=value_btc,
            spent=True,
            spending_txid=None,
        )