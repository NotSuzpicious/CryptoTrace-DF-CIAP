from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.analysis.investigation import BlockchainInvestigator
from app.blockchain.bitcoin_rpc import BitcoinRPC


def main() -> None:
    rpc = BitcoinRPC()

    if not rpc.is_available():
        raise SystemExit(
            "Bitcoin Core is not running. Start bitcoind before running this test."
        )

    # Use block 100 because it is already available in our locally
    # synchronized blockchain data.
    block_hash = rpc.get_block_hash(100)
    block = rpc.get_block(block_hash, verbosity=2)

    transactions = block.get("tx", [])

    if not transactions:
        raise RuntimeError("Block 100 contains no transactions.")

    transaction = transactions[0]
    txid = transaction["txid"]

    investigator = BlockchainInvestigator()

    result = investigator.investigate_transaction(
        txid=txid,
        block_hash=block_hash,
    )

    print("\n=== CRYPTOTRACE FORENSIC INVESTIGATION TEST ===")
    print(f"Transaction ID: {result.summary.txid}")
    print(f"Coinbase: {result.summary.is_coinbase}")
    print(f"Block hash: {result.evidence.block_hash}")
    print(f"Confirmations: {result.summary.confirmations}")
    print(f"Inputs: {result.summary.input_count}")
    print(f"Outputs: {result.summary.output_count}")
    print(f"Total output: {result.summary.total_output_btc:.8f} BTC")
    print(f"Size: {result.summary.size} bytes")
    print(f"Virtual size: {result.summary.virtual_size} vbytes")
    print(f"Weight: {result.summary.weight}")

    print("\nTransaction Inputs:")
    for index, item in enumerate(result.details.inputs, start=1):
        print(
            f"- Input {index}: "
            f"previous_txid={item.previous_txid}, "
            f"previous_vout={item.previous_vout}, "
            f"coinbase={item.is_coinbase}"
        )

    print("\nTransaction Outputs:")
    for item in result.details.outputs:
        print(
            f"- Output {item.index}: "
            f"value={item.value_btc:.8f} BTC, "
            f"type={item.script_type}, "
            f"address={item.address}"
        )

    print("\nForensic Indicators:")

    for indicator in result.indicators:
        status = "TRIGGERED" if indicator.triggered else "Not triggered"
        print(f"- {indicator.name}: {status}")
        print(f"  {indicator.explanation}")


if __name__ == "__main__":
    main()