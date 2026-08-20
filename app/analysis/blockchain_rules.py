from __future__ import annotations

from dataclasses import dataclass

from app.analysis.transaction_examiner import TransactionSummary


@dataclass
class BlockchainIndicator:
    name: str
    triggered: bool
    explanation: str


class BlockchainRuleEngine:
    """
    Rule-based forensic examination of Bitcoin transaction characteristics.

    These rules identify structural characteristics that may warrant further
    investigation. They do not establish illicit activity or attribution.
    """

    HIGH_INPUT_COUNT = 10
    HIGH_OUTPUT_COUNT = 10
    LARGE_TRANSACTION_BTC = 10.0

    def analyze(
        self,
        transaction: TransactionSummary,
    ) -> list[BlockchainIndicator]:

        indicators: list[BlockchainIndicator] = []

        if transaction.is_coinbase:
            indicators.append(
                BlockchainIndicator(
                    name="Coinbase transaction",
                    triggered=False,
                    explanation=(
                        "This transaction creates a block reward and is not an "
                        "ordinary transfer between Bitcoin participants."
                    ),
                )
            )

        high_inputs = (
            not transaction.is_coinbase
            and transaction.input_count >= self.HIGH_INPUT_COUNT
        )
        indicators.append(
            BlockchainIndicator(
                name="High input count",
                triggered=high_inputs,
                explanation=(
                    f"Transaction contains {transaction.input_count} inputs. "
                    f"The review threshold is {self.HIGH_INPUT_COUNT}."
                    if not transaction.is_coinbase
                    else "Input-count review is not applied to coinbase transactions."
                ),
            )
        )

        high_outputs = (
            not transaction.is_coinbase
            and transaction.output_count >= self.HIGH_OUTPUT_COUNT
        )
        indicators.append(
            BlockchainIndicator(
                name="High output count",
                triggered=high_outputs,
                explanation=(
                    f"Transaction contains {transaction.output_count} outputs. "
                    f"The review threshold is {self.HIGH_OUTPUT_COUNT}."
                    if not transaction.is_coinbase
                    else "Output-count review is not applied to coinbase transactions."
                ),
            )
        )

        large_value = (
            not transaction.is_coinbase
            and transaction.total_output_btc >= self.LARGE_TRANSACTION_BTC
        )
        indicators.append(
            BlockchainIndicator(
                name="Large transaction value",
                triggered=large_value,
                explanation=(
                    f"Transaction outputs total approximately "
                    f"{transaction.total_output_btc:.8f} BTC. "
                    f"The review threshold is "
                    f"{self.LARGE_TRANSACTION_BTC:.8f} BTC."
                    if not transaction.is_coinbase
                    else "Large-value review is not applied to coinbase block rewards."
                ),
            )
        )

        fan_in = (
            not transaction.is_coinbase
            and transaction.input_count >= 5
        )
        indicators.append(
            BlockchainIndicator(
                name="Potential fan-in structure",
                triggered=fan_in,
                explanation=(
                    f"The transaction consolidates "
                    f"{transaction.input_count} inputs."
                    if not transaction.is_coinbase
                    else "Fan-in analysis is not applicable to coinbase transactions."
                ),
            )
        )

        fan_out = (
            not transaction.is_coinbase
            and transaction.output_count >= 5
        )
        indicators.append(
            BlockchainIndicator(
                name="Potential fan-out structure",
                triggered=fan_out,
                explanation=(
                    f"The transaction distributes funds across "
                    f"{transaction.output_count} outputs."
                    if not transaction.is_coinbase
                    else "Fan-out analysis is not applied to coinbase transactions."
                ),
            )
        )

        return indicators