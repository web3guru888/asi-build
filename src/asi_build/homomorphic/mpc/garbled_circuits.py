"""Garbled circuits for secure two-party computation."""

import hashlib
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class Wire:
    """Represents a wire in a garbled circuit."""

    wire_id: str
    label_0: bytes
    label_1: bytes


class GarbledCircuits:
    """Implementation of Yao's garbled circuits."""

    def __init__(self, security_parameter: int = 128):
        self.security_parameter = security_parameter
        self.label_length = security_parameter // 8

    def generate_wire_labels(self, wire_id: str) -> Wire:
        """Generate random labels for a wire."""
        label_0 = random.getrandbits(self.security_parameter).to_bytes(self.label_length, "big")
        label_1 = random.getrandbits(self.security_parameter).to_bytes(self.label_length, "big")
        return Wire(wire_id, label_0, label_1)

    def garble_and_gate(
        self, input_wire_a: Wire, input_wire_b: Wire, output_wire: Wire
    ) -> List[bytes]:
        """Garble an AND gate."""
        # Create garbled table for AND gate
        garbled_table = []

        # For each combination of input values
        for a_val in [0, 1]:
            for b_val in [0, 1]:
                output_val = a_val & b_val

                # Get input labels
                a_label = input_wire_a.label_0 if a_val == 0 else input_wire_a.label_1
                b_label = input_wire_b.label_0 if b_val == 0 else input_wire_b.label_1

                # Get output label
                output_label = output_wire.label_0 if output_val == 0 else output_wire.label_1

                # Encrypt output label with input labels
                key = hashlib.sha256(a_label + b_label).digest()[:16]
                encrypted = self._encrypt(output_label, key)
                garbled_table.append(encrypted)

        # Shuffle the table
        random.shuffle(garbled_table)
        return garbled_table

    def evaluate_and_gate(
        self, garbled_table: List[bytes], a_label: bytes, b_label: bytes
    ) -> bytes:
        """Evaluate a garbled AND gate."""
        key = hashlib.sha256(a_label + b_label).digest()[:16]

        # Try to decrypt each entry in the garbled table
        for encrypted_label in garbled_table:
            try:
                decrypted = self._decrypt(encrypted_label, key)
                if decrypted:  # Valid decryption
                    return decrypted
            except:
                continue

        raise ValueError("Could not evaluate garbled gate")

    def _encrypt(self, plaintext: bytes, key: bytes) -> bytes:
        """Simple XOR encryption."""
        return bytes(a ^ b for a, b in zip(plaintext, key * (len(plaintext) // len(key) + 1)))

    def _decrypt(self, ciphertext: bytes, key: bytes) -> bytes:
        """Simple XOR decryption."""
        return bytes(a ^ b for a, b in zip(ciphertext, key * (len(ciphertext) // len(key) + 1)))
