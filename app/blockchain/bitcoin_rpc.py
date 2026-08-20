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