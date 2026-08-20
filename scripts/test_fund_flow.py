from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.analysis.fund_flow import FundFlowTracer
from app.blockchain.bitcoin_rpc import BitcoinRPC


def main() -> None:
    rpc = BitcoinRPC()

    if not rpc.is_available():
        raise SystemExit(
            "Bitcoin Core is not running. Start bitcoind before running this test."
        )

    # Use block 100 and select its first transaction.
    block_hash = rpc.get_block_hash(100)
    block = rpc.get_block(block_hash, verbosity=2)

    transactions = block.get("tx", [])

    if not transactions:
        raise RuntimeError("Block 100 contains no transactions.")

    txid = transactions[0]["txid"]

    tracer = FundFlowTracer(rpc)

    results = tracer.trace_backward(
        txid=txid,
        block_hash=block_hash,
        max_depth=2,
    )

    print("\n=== CRYPTOTRACE BACKWARD FUND FLOW TEST ===")
    print(f"Starting transaction: {txid}")
    print(f"Block hash: {block_hash}")

    if not results:
        print("No previous transactions found.")
        print(
            "This is expected for a coinbase transaction because "
            "coinbase inputs do not reference previous transactions."
        )
        return

    print("\nBackward flow:")

    for node in results:
        print(
            f"- depth={node.depth}, "
            f"direction={node.direction}, "
            f"txid={node.txid}"
        )


if __name__ == "__main__":
    main()