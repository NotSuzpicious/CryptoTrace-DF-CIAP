from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


BITCOIN_CLI = Path(r"C:\Program Files\Bitcoin\daemon\bitcoin-cli.exe")
BITCOIN_DATA_DIR = Path.home() / "AppData" / "Local" / "Bitcoin"


class BitcoinRPC:
    def __init__(
        self,
        cli_path: Path = BITCOIN_CLI,
        data_dir: Path = BITCOIN_DATA_DIR,
    ) -> None:
        self.cli_path = cli_path
        self.data_dir = data_dir

    def call(self, method: str, *params: Any) -> Any:
        command = [
            str(self.cli_path),
            f"-datadir={self.data_dir}",
            method,
            *[str(param) for param in params],
        ]

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            error = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"Bitcoin Core RPC failed: {error}")

        output = result.stdout.strip()

        if not output:
            return None

        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return output

    def get_blockchain_info(self) -> dict[str, Any]:
        result = self.call("getblockchaininfo")

        if not isinstance(result, dict):
            raise RuntimeError("Unexpected response from Bitcoin Core.")

        return result

    def get_block_hash(self, height: int) -> str:
        result = self.call("getblockhash", height)

        if not isinstance(result, str):
            raise RuntimeError("Unexpected block hash response from Bitcoin Core.")

        return result

    def get_block(self, block_hash: str, verbosity: int = 2) -> dict[str, Any]:
        result = self.call("getblock", block_hash, verbosity)

        if not isinstance(result, dict):
            raise RuntimeError("Unexpected block response from Bitcoin Core.")

        return result

    def get_raw_transaction(
        self,
        txid: str,
        verbose: bool = True,
        block_hash: str | None = None,
    ) -> Any:
        params: list[Any] = [txid, verbose]

        if block_hash is not None:
            params.append(block_hash)

        return self.call("getrawtransaction", *params)

    def decode_raw_transaction(self, raw_hex: str) -> dict[str, Any]:
        result = self.call("decoderawtransaction", raw_hex)

        if not isinstance(result, dict):
            raise RuntimeError("Unexpected decoded transaction response from Bitcoin Core.")

        return result

    def is_available(self) -> bool:
        try:
            self.get_blockchain_info()
            return True
        except Exception:
            return False