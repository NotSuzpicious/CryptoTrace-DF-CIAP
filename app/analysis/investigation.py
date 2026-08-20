from __future__ import annotations

from dataclasses import dataclass

from app.analysis.blockchain_rules import BlockchainIndicator, BlockchainRuleEngine
from app.analysis.transaction_examiner import TransactionSummary, examine_transaction
from app.blockchain.acquisition import EvidenceAcquisition
from app.blockchain.evidence import TransactionEvidence


@dataclass
class InvestigationResult:
    evidence: TransactionEvidence
    summary: TransactionSummary
    indicators: list[BlockchainIndicator]


class BlockchainInvestigator:
    """
    Coordinates blockchain evidence acquisition, examination,
    and rule-based forensic analysis.
    """

    def __init__(
        self,
        acquisition: EvidenceAcquisition | None = None,
        rule_engine: BlockchainRuleEngine | None = None,
    ) -> None:
        self.acquisition = acquisition or EvidenceAcquisition()
        self.rule_engine = rule_engine or BlockchainRuleEngine()

    def investigate_transaction(
        self,
        txid: str,
        block_hash: str | None = None,
    ) -> InvestigationResult:

        evidence = self.acquisition.acquire_transaction(
            txid=txid,
            block_hash=block_hash,
        )

        summary = examine_transaction(evidence)

        indicators = self.rule_engine.analyze(summary)

        return InvestigationResult(
            evidence=evidence,
            summary=summary,
            indicators=indicators,
        )