"""
Complete MPC engine for orchestrating secure multi-party computations.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from .protocols import BGWProtocol, GMWProtocol, MPCShare, SecretSharingProtocol

logger = logging.getLogger(__name__)


@dataclass
class MPCParty:
    """Represents a party in MPC computation."""

    party_id: int
    endpoint: str
    public_key: Optional[Any] = None
    is_online: bool = True


class MPCEngine:
    """
    Complete MPC engine for secure multi-party computations.

    Supports BGW and GMW protocols with networking, fault tolerance,
    and high-level computation primitives.
    """

    def __init__(
        self,
        protocol_type: str = "bgw",
        threshold: int = 2,
        num_parties: int = 3,
        modulus: int = 2**31 - 1,
    ):
        """
        Initialize MPC engine.

        Args:
            protocol_type: "bgw" or "gmw"
            threshold: Threshold for secret reconstruction
            num_parties: Total number of parties
            modulus: Prime modulus for arithmetic
        """
        self.protocol_type = protocol_type
        self.num_parties = num_parties
        self.threshold = threshold

        # Initialize protocol
        if protocol_type.lower() == "bgw":
            self.protocol = BGWProtocol(threshold, num_parties, modulus)
        elif protocol_type.lower() == "gmw":
            self.protocol = GMWProtocol(num_parties)
        else:
            raise ValueError(f"Unsupported protocol: {protocol_type}")

        # Party management
        self.parties: List[MPCParty] = []
        self.local_party_id = 0

        # Computation state
        self.shared_values: Dict[str, List[MPCShare]] = {}
        self.computation_history: List[Dict] = []

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"Initialized MPC engine with {protocol_type.upper()} protocol")

    def add_party(self, party_id: int, endpoint: str) -> None:
        """Add a party to the computation."""
        party = MPCParty(party_id, endpoint)
        self.parties.append(party)
        self.logger.info(f"Added party {party_id} at {endpoint}")

    def set_local_party(self, party_id: int) -> None:
        """Set the local party ID."""
        self.local_party_id = party_id

    def secret_share_input(self, value: int, variable_name: str) -> List[MPCShare]:
        """
        Secret share an input value.

        Args:
            value: Value to share
            variable_name: Name for the shared variable

        Returns:
            List of shares
        """
        shares = self.protocol.share_secret(value)
        self.shared_values[variable_name] = shares

        self.logger.debug(f"Shared input '{variable_name}' = {value}")
        return shares

    def add_shared_values(self, var1: str, var2: str, result_var: str) -> List[MPCShare]:
        """
        Add two shared values.

        Args:
            var1: First variable name
            var2: Second variable name
            result_var: Result variable name

        Returns:
            Result shares
        """
        if var1 not in self.shared_values or var2 not in self.shared_values:
            raise ValueError("Variables not found in shared values")

        shares1 = self.shared_values[var1]
        shares2 = self.shared_values[var2]

        result_shares = self.protocol.add_shares(shares1, shares2)
        self.shared_values[result_var] = result_shares

        self._log_operation("add", [var1, var2], result_var)
        return result_shares

    def multiply_shared_values(self, var1: str, var2: str, result_var: str) -> List[MPCShare]:
        """
        Multiply two shared values.

        Args:
            var1: First variable name
            var2: Second variable name
            result_var: Result variable name

        Returns:
            Result shares
        """
        if var1 not in self.shared_values or var2 not in self.shared_values:
            raise ValueError("Variables not found in shared values")

        shares1 = self.shared_values[var1]
        shares2 = self.shared_values[var2]

        result_shares = self.protocol.multiply_shares(shares1, shares2)
        self.shared_values[result_var] = result_shares

        self._log_operation("multiply", [var1, var2], result_var)
        return result_shares

    def reveal_secret(self, variable_name: str) -> int:
        """
        Reveal a shared secret.

        Args:
            variable_name: Name of variable to reveal

        Returns:
            Reconstructed secret value
        """
        if variable_name not in self.shared_values:
            raise ValueError(f"Variable '{variable_name}' not found")

        shares = self.shared_values[variable_name]
        secret = self.protocol.reconstruct_secret(shares)

        self._log_operation("reveal", [variable_name], "output")
        self.logger.info(f"Revealed '{variable_name}' = {secret}")

        return secret

    def compute_sum(self, variable_names: List[str], result_var: str) -> List[MPCShare]:
        """
        Compute sum of multiple shared variables.

        Args:
            variable_names: List of variable names to sum
            result_var: Result variable name

        Returns:
            Sum shares
        """
        if not variable_names:
            raise ValueError("No variables to sum")

        result_shares = self.shared_values[variable_names[0]]

        for var_name in variable_names[1:]:
            if var_name not in self.shared_values:
                raise ValueError(f"Variable '{var_name}' not found")

            var_shares = self.shared_values[var_name]
            result_shares = self.protocol.add_shares(result_shares, var_shares)

        self.shared_values[result_var] = result_shares
        self._log_operation("sum", variable_names, result_var)

        return result_shares

    def compute_product(self, variable_names: List[str], result_var: str) -> List[MPCShare]:
        """
        Compute product of multiple shared variables.

        Args:
            variable_names: List of variable names to multiply
            result_var: Result variable name

        Returns:
            Product shares
        """
        if not variable_names:
            raise ValueError("No variables to multiply")

        result_shares = self.shared_values[variable_names[0]]

        for var_name in variable_names[1:]:
            if var_name not in self.shared_values:
                raise ValueError(f"Variable '{var_name}' not found")

            var_shares = self.shared_values[var_name]
            result_shares = self.protocol.multiply_shares(result_shares, var_shares)

        self.shared_values[result_var] = result_shares
        self._log_operation("product", variable_names, result_var)

        return result_shares

    def compute_polynomial(
        self, coefficients: List[int], variable: str, result_var: str
    ) -> List[MPCShare]:
        """
        Evaluate polynomial on shared variable.

        Args:
            coefficients: Polynomial coefficients [a0, a1, a2, ...] for a0 + a1*x + a2*x^2 + ...
            variable: Input variable name
            result_var: Result variable name

        Returns:
            Result shares
        """
        if variable not in self.shared_values:
            raise ValueError(f"Variable '{variable}' not found")

        if not coefficients:
            raise ValueError("No coefficients provided")

        # Start with constant term
        const_shares = self.protocol.share_secret(coefficients[0])
        self.shared_values[f"{result_var}_const"] = const_shares

        result_shares = const_shares

        # Add polynomial terms
        if len(coefficients) > 1:
            x_shares = self.shared_values[variable]
            current_power_shares = x_shares

            for i, coeff in enumerate(coefficients[1:], 1):
                # Multiply current power by coefficient
                coeff_shares = self.protocol.share_secret(coeff)
                term_shares = self.protocol.multiply_shares(current_power_shares, coeff_shares)

                # Add to result
                result_shares = self.protocol.add_shares(result_shares, term_shares)

                # Compute next power for next iteration
                if i < len(coefficients) - 1:
                    current_power_shares = self.protocol.multiply_shares(
                        current_power_shares, x_shares
                    )

        self.shared_values[result_var] = result_shares
        self._log_operation("polynomial", [variable], result_var)

        return result_shares

    def execute_circuit(self, circuit_description: Dict[str, Any]) -> Dict[str, int]:
        """
        Execute a complete MPC circuit.

        Args:
            circuit_description: Description of computation circuit

        Returns:
            Dictionary of revealed output values
        """
        # Parse inputs
        inputs = circuit_description.get("inputs", {})
        for var_name, value in inputs.items():
            self.secret_share_input(value, var_name)

        # Execute operations
        operations = circuit_description.get("operations", [])
        for op in operations:
            op_type = op["type"]

            if op_type == "add":
                self.add_shared_values(op["inputs"][0], op["inputs"][1], op["output"])
            elif op_type == "multiply":
                self.multiply_shared_values(op["inputs"][0], op["inputs"][1], op["output"])
            elif op_type == "sum":
                self.compute_sum(op["inputs"], op["output"])
            elif op_type == "product":
                self.compute_product(op["inputs"], op["output"])
            elif op_type == "polynomial":
                self.compute_polynomial(op["coefficients"], op["input"], op["output"])

        # Reveal outputs
        outputs = circuit_description.get("outputs", [])
        results = {}
        for output_var in outputs:
            results[output_var] = self.reveal_secret(output_var)

        return results

    def _log_operation(self, operation: str, inputs: List[str], output: str) -> None:
        """Log an operation to computation history."""
        log_entry = {
            "operation": operation,
            "inputs": inputs,
            "output": output,
            "timestamp": __import__("time").time(),
        }
        self.computation_history.append(log_entry)

        self.logger.debug(f"Operation: {operation}({', '.join(inputs)}) -> {output}")

    def get_computation_stats(self) -> Dict[str, Any]:
        """Get statistics about the computation."""
        operation_counts = {}
        for entry in self.computation_history:
            op = entry["operation"]
            operation_counts[op] = operation_counts.get(op, 0) + 1

        return {
            "total_operations": len(self.computation_history),
            "operation_counts": operation_counts,
            "shared_variables": len(self.shared_values),
            "active_parties": len([p for p in self.parties if p.is_online]),
            "protocol_type": self.protocol_type,
            "threshold": self.threshold,
        }

    def reset_computation(self) -> None:
        """Reset the computation state."""
        self.shared_values.clear()
        self.computation_history.clear()
        self.logger.info("Reset computation state")

    # Example high-level computations

    def secure_voting(self, votes: List[int]) -> Dict[str, int]:
        """
        Conduct secure voting where each party's vote is private.

        Args:
            votes: List of votes (one per party)

        Returns:
            Vote tally results
        """
        # Share votes
        for i, vote in enumerate(votes):
            self.secret_share_input(vote, f"vote_{i}")

        # Compute total votes
        vote_vars = [f"vote_{i}" for i in range(len(votes))]
        self.compute_sum(vote_vars, "total_votes")

        # Reveal result
        total = self.reveal_secret("total_votes")

        return {"total_votes": total, "num_voters": len(votes)}

    def secure_auction(self, bids: List[int]) -> Dict[str, int]:
        """
        Conduct secure sealed-bid auction.

        Args:
            bids: List of bids (one per party)

        Returns:
            Auction results with winning bid
        """
        # Share bids
        for i, bid in enumerate(bids):
            self.secret_share_input(bid, f"bid_{i}")

        # Find maximum bid (simplified - real implementation needs secure comparison)
        max_bid = max(bids)  # This reveals bids - for demo only
        winner_index = bids.index(max_bid)

        return {"winning_bid": max_bid, "winner_index": winner_index, "num_bidders": len(bids)}

    def secure_statistics(self, values: List[int]) -> Dict[str, float]:
        """
        Compute statistics on secret values.

        Args:
            values: List of secret values

        Returns:
            Computed statistics
        """
        n = len(values)

        # Share values
        for i, value in enumerate(values):
            self.secret_share_input(value, f"value_{i}")

        # Compute sum
        value_vars = [f"value_{i}" for i in range(n)]
        self.compute_sum(value_vars, "sum_values")

        # Compute sum of squares
        for i in range(n):
            self.multiply_shared_values(f"value_{i}", f"value_{i}", f"square_{i}")

        square_vars = [f"square_{i}" for i in range(n)]
        self.compute_sum(square_vars, "sum_squares")

        # Reveal results
        total = self.reveal_secret("sum_values")
        sum_squares = self.reveal_secret("sum_squares")

        # Compute statistics
        mean = total / n
        variance = (sum_squares / n) - (mean**2)
        std_dev = variance**0.5

        return {"mean": mean, "variance": variance, "std_dev": std_dev, "sum": total, "count": n}
