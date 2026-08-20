from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any


class BlockchainEvidenceStore:
    """
    Local SQLite evidence store for Bitcoin blockchain data.

    The database preserves transaction, input, and output evidence acquired
    from Bitcoin Core so that forensic analysis can continue even after a
    pruned Bitcoin Core node removes historical block data.
    """

    def __init__(self, db_path: str | Path = "data/blockchain_evidence.db") -> None:
        self.db_path = Path(db_path)

        if self.db_path.parent:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._initialize_database()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize_database(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS transactions (
                    txid TEXT PRIMARY KEY,
                    block_hash TEXT,
                    block_height INTEGER,
                    block_time INTEGER,
                    confirmations INTEGER,
                    is_coinbase INTEGER NOT NULL DEFAULT 0,
                    version INTEGER NOT NULL DEFAULT 0,
                    size INTEGER NOT NULL DEFAULT 0,
                    virtual_size INTEGER NOT NULL DEFAULT 0,
                    weight INTEGER NOT NULL DEFAULT 0,
                    locktime INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS inputs (
                    txid TEXT NOT NULL,
                    input_index INTEGER NOT NULL,
                    previous_txid TEXT,
                    previous_vout INTEGER,
                    value_btc REAL,
                    previous_block_height INTEGER,
                    is_coinbase INTEGER NOT NULL DEFAULT 0,

                    PRIMARY KEY (txid, input_index),

                    FOREIGN KEY (txid)
                        REFERENCES transactions(txid)
                        ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS outputs (
                    txid TEXT NOT NULL,
                    output_index INTEGER NOT NULL,
                    value_btc REAL NOT NULL DEFAULT 0,
                    script_type TEXT,
                    address TEXT,

                    PRIMARY KEY (txid, output_index),

                    FOREIGN KEY (txid)
                        REFERENCES transactions(txid)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_inputs_previous_txid
                    ON inputs(previous_txid);

                CREATE INDEX IF NOT EXISTS idx_inputs_txid
                    ON inputs(txid);

                CREATE INDEX IF NOT EXISTS idx_outputs_txid
                    ON outputs(txid);

                CREATE INDEX IF NOT EXISTS idx_transactions_block_height
                    ON transactions(block_height);
                """
            )

    def save_transaction(
        self,
        transaction: dict[str, Any],
        block_hash: str | None = None,
        block_height: int | None = None,
    ) -> None:
        txid = str(transaction.get("txid", "")).strip()

        if not txid:
            raise ValueError("Transaction does not contain a TXID.")

        vin = transaction.get("vin", [])
        vout = transaction.get("vout", [])

        is_coinbase = bool(
            vin
            and isinstance(vin, list)
            and isinstance(vin[0], dict)
            and "coinbase" in vin[0]
        )

        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO transactions (
                    txid,
                    block_hash,
                    block_height,
                    block_time,
                    confirmations,
                    is_coinbase,
                    version,
                    size,
                    virtual_size,
                    weight,
                    locktime
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    txid,
                    block_hash or transaction.get("blockhash"),
                    block_height,
                    transaction.get("blocktime"),
                    transaction.get("confirmations"),
                    int(is_coinbase),
                    int(transaction.get("version", 0)),
                    int(transaction.get("size", 0)),
                    int(transaction.get("vsize", 0)),
                    int(transaction.get("weight", 0)),
                    int(transaction.get("locktime", 0)),
                ),
            )

            connection.execute(
                "DELETE FROM inputs WHERE txid = ?",
                (txid,),
            )

            connection.execute(
                "DELETE FROM outputs WHERE txid = ?",
                (txid,),
            )

            for index, item in enumerate(vin):
                prevout = item.get("prevout", {})
                if not isinstance(prevout, dict):
                    prevout = {}

                connection.execute(
                    """
                    INSERT INTO inputs (
                        txid,
                        input_index,
                        previous_txid,
                        previous_vout,
                        value_btc,
                        previous_block_height,
                        is_coinbase
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        txid,
                        index,
                        item.get("txid"),
                        item.get("vout"),
                        prevout.get("value"),
                        prevout.get("height"),
                        int("coinbase" in item),
                    ),
                )

            for index, item in enumerate(vout):
                script_pub_key = item.get("scriptPubKey", {})
                if not isinstance(script_pub_key, dict):
                    script_pub_key = {}

                address = script_pub_key.get("address")

                addresses = script_pub_key.get("addresses")
                if not address and isinstance(addresses, list) and addresses:
                    address = addresses[0]

                connection.execute(
                    """
                    INSERT INTO outputs (
                        txid,
                        output_index,
                        value_btc,
                        script_type,
                        address
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        txid,
                        index,
                        float(item.get("value", 0)),
                        script_pub_key.get("type"),
                        address,
                    ),
                )

    def transaction_exists(self, txid: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM transactions
                WHERE txid = ?
                """,
                (txid.strip(),),
            ).fetchone()

        return row is not None

    def get_transaction(self, txid: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            transaction = connection.execute(
                """
                SELECT *
                FROM transactions
                WHERE txid = ?
                """,
                (txid.strip(),),
            ).fetchone()

            if transaction is None:
                return None

            inputs = connection.execute(
                """
                SELECT *
                FROM inputs
                WHERE txid = ?
                ORDER BY input_index
                """,
                (txid.strip(),),
            ).fetchall()

            outputs = connection.execute(
                """
                SELECT *
                FROM outputs
                WHERE txid = ?
                ORDER BY output_index
                """,
                (txid.strip(),),
            ).fetchall()

        return {
            "transaction": dict(transaction),
            "inputs": [dict(row) for row in inputs],
            "outputs": [dict(row) for row in outputs],
        }

    def count_transactions(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM transactions"
            ).fetchone()

        return int(row["count"])

    def count_inputs(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM inputs"
            ).fetchone()

        return int(row["count"])

    def count_outputs(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM outputs"
            ).fetchone()

        return int(row["count"])