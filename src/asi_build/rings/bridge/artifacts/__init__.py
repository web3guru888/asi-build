"""
Compiled Solidity contract artifacts (ABI + bytecode) for the Rings↔Ethereum Bridge.

Built with Foundry (forge) from the Solidity sources in
``blockchain/contracts/contracts/``.  Each JSON file follows the standard
Forge output format and contains at minimum:

* ``abi`` — The contract ABI (list of function/event/error descriptors).
* ``bytecode.object`` — The creation bytecode (hex string with ``0x`` prefix).
* ``deployedBytecode.object`` — The runtime bytecode.

Usage::

    from asi_build.rings.bridge.artifacts import load_artifact

    abi, bytecode = load_artifact("RingsBridge")

Artifacts included:

* **RingsBridge** — Main bridge contract (deposits, withdrawals, sync committee).
* **Groth16Verifier** — BN254 pairing-based ZK proof verifier.
* **BridgedToken** — ERC20 with BRIDGE_ROLE-gated mint/burn.
* **IBridgedToken** — Interface only (no bytecode).
* **IGroth16Verifier** — Interface only (no bytecode).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_ARTIFACTS_DIR = Path(__file__).parent

# Cache loaded artifacts
_cache: dict[str, dict[str, Any]] = {}


def load_artifact(name: str) -> tuple[list[dict[str, Any]], str]:
    """Load a compiled contract artifact by name.

    Parameters
    ----------
    name:
        Contract name (e.g. ``"RingsBridge"``, ``"BridgedToken"``).
        Must correspond to a ``.json`` file in this directory.

    Returns
    -------
    tuple[list, str]
        ``(abi, bytecode)`` where *abi* is the parsed ABI list and
        *bytecode* is the hex creation bytecode string (with ``0x`` prefix).

    Raises
    ------
    FileNotFoundError
        If no artifact JSON exists for the given name.
    KeyError
        If the JSON is missing expected keys.
    """
    if name not in _cache:
        path = _ARTIFACTS_DIR / f"{name}.json"
        if not path.exists():
            raise FileNotFoundError(f"No artifact found: {path}")
        with open(path) as f:
            _cache[name] = json.load(f)

    artifact = _cache[name]
    abi = artifact["abi"]

    # Forge output nests bytecode under bytecode.object
    bytecode_section = artifact.get("bytecode", {})
    if isinstance(bytecode_section, dict):
        bytecode = bytecode_section.get("object", "0x")
    else:
        bytecode = "0x"

    return abi, bytecode


def load_abi(name: str) -> list[dict[str, Any]]:
    """Load only the ABI for a contract (convenience wrapper)."""
    abi, _ = load_artifact(name)
    return abi


def load_bytecode(name: str) -> str:
    """Load only the creation bytecode for a contract (convenience wrapper)."""
    _, bytecode = load_artifact(name)
    return bytecode


# Pre-define available artifacts
AVAILABLE_ARTIFACTS = [
    "RingsBridge",
    "Groth16Verifier",
    "BridgedToken",
    "IBridgedToken",
    "IGroth16Verifier",
]

__all__ = [
    "load_artifact",
    "load_abi",
    "load_bytecode",
    "AVAILABLE_ARTIFACTS",
]
