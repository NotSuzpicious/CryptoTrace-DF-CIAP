from __future__ import annotations

from dataclasses import dataclass

from app.analysis.blockchain_rules import BlockchainIndicator, BlockchainRuleEngine
from app.analysis.transaction_details import (
    TransactionDetails,
    extract_transaction_details,
)
from app.analysis.transaction_examiner import TransactionSummary, examine_transaction
from app.blockchain.acquisition import EvidenceAcquisition
from app.blockchain.evidence import TransactionEvidence
from app.blockchain.evidence_store import BlockchainEvidenceStore

@dataclass
class InvestigationResult:
    evidence: TransactionEvidence
    summary: TransactionSummary
    details: TransactionDetails
    indicators: list[BlockchainIndicator]


class BlockchainInvestigator:
    """
    Coordinates blockchain evidence acquisition, examination,
    detailed transaction parsing, and rule-based forensic analysis.
    """

    def __init__(
        self,
        acquisition: EvidenceAcquisition | None = None,
        rule_engine: BlockchainRuleEngine | None = None,
        evidence_store: BlockchainEvidenceStore | None = None,
    ) -> None:
        self.acquisition = acquisition or EvidenceAcquisition()
        self.rule_engine = rule_engine or BlockchainRuleEngine()
        self.evidence_store = evidence_store or BlockchainEvidenceStore()

    def investigate_transaction(
        self,
        txid: str,
        block_hash: str | None = None,
    ) -> InvestigationResult:

        txid = txid.strip()

        if not txid:
            raise ValueError("Transaction ID cannot be empty.")

        # Prefer preserved local forensic evidence.
        stored = self.evidence_store.get_transaction(txid)

        if stored is not None:
            transaction = stored["transaction"]

            stored_inputs = []

            for item in stored["inputs"]:
                if item.get("is_coinbase"):
                    stored_inputs.append(
                        {
                            "coinbase": "",
                            "sequence": 0,
                        }
                    )
                else:
                    stored_inputs.append(
                        {
                            "txid": item.get("previous_txid"),
                            "vout": item.get("previous_vout"),
                            "prevout": {
                                "value": item.get("value_btc"),
                                "height": item.get("previous_block_height"),
                            },
                        }
                    )

            stored_outputs = []

            for item in stored["outputs"]:
                script_pub_key = {
                    "type": item.get("script_type"),
                }

                if item.get("address"):
                    script_pub_key["address"] = item["address"]

                stored_outputs.append(
                    {
                        "value": item.get("value_btc", 0),
                        "n": item.get("output_index", 0),
                        "scriptPubKey": script_pub_key,
                    }
                )

            evidence = TransactionEvidence(
                txid=transaction["txid"],
                is_coinbase=bool(transaction["is_coinbase"]),
                block_hash=transaction["block_hash"],
                confirmations=transaction["confirmations"],
                block_time=transaction["block_time"],
                version=transaction["version"],
                size=transaction["size"],
                virtual_size=transaction["virtual_size"],
                weight=transaction["weight"],
                locktime=transaction["locktime"],
                inputs=stored_inputs,
                outputs=stored_outputs,
            )

        else:
            # Evidence is not locally preserved, so acquire it from
            # Bitcoin Core and immediately preserve it.
            evidence = self.acquisition.acquire_transaction(
                txid=txid,
                block_hash=block_hash,
            )

            self.evidence_store.save_transaction(
                {
                    "txid": evidence.txid,
                    "blockhash": evidence.block_hash,
                    "confirmations": evidence.confirmations,
                    "blocktime": evidence.block_time,
                    "version": evidence.version,
                    "size": evidence.size,
                    "vsize": evidence.virtual_size,
                    "weight": evidence.weight,
                    "locktime": evidence.locktime,
                    "vin": evidence.inputs,
                    "vout": evidence.outputs,
                },
                block_hash=evidence.block_hash,
            )

        summary = examine_transaction(evidence)

        details = extract_transaction_details(evidence)

        indicators = self.rule_engine.analyze(summary)

        return InvestigationResult(
            evidence=evidence,
            summary=summary,
            details=details,
            indicators=indicators,
        )