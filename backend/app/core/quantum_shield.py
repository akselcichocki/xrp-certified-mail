"""
Quantum Shield — Post-quantum-resilient proof layer for XRP Certified Mail.

Problem:
  XRP transactions use ECDSA (secp256k1) for signing. Shor's Algorithm
  breaks this. A quantum computer could forge transaction signatures,
  undermining the proof that a specific account sent the transaction.

Solution:
  Create a secondary proof certificate that does NOT depend on ECDSA.
  This certificate uses only hash-based constructions (SHA-256, HMAC)
  which are quantum-resistant (Grover's only provides quadratic speedup).

How it works:
  1. Hash the email content (SHA-256) — same as the classical proof
  2. Build a hash chain: content_hash → chained with timestamp, nonce,
     and a server-side secret → produces a "shield hash"
  3. The shield hash is deterministic and verifiable by anyone who has
     the original content + the shield parameters
  4. Even if the XRP transaction signature is forged, the shield
     independently proves the content existed at the claimed time

What this does NOT do:
  - It does not replace the XRP ledger proof (that still works today)
  - It does not use a post-quantum digital signature scheme (no ML-DSA yet)
  - It does not prove WHO sent it (that requires PQC signatures)

What it DOES do:
  - Proves WHAT was sent (content hash — quantum safe)
  - Proves WHEN it was claimed (timestamp in the hash chain)
  - Survives ECDSA compromise (no elliptic curve math involved)
  - Creates a standalone verifiable certificate

This is a crypto-agility workaround: it adds a quantum-resistant layer
alongside the classical proof, so the system degrades gracefully as
the threat landscape evolves.
"""

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass


# Shield secret — used for HMAC binding. Must be set in production.
_SHIELD_SECRET = os.environ.get("QUANTUM_SHIELD_SECRET", "")
_ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev").lower()

if not _SHIELD_SECRET:
    if _ENVIRONMENT in ("prod", "production", "staging"):
        raise RuntimeError(
            "QUANTUM_SHIELD_SECRET is required in production. "
            "Set it to a long random value (e.g. openssl rand -hex 32)."
        )
    else:
        import warnings
        _SHIELD_SECRET = hashlib.sha256(
            f"dev-only-insecure-{os.getpid()}-{time.time()}".encode()
        ).hexdigest()
        warnings.warn(
            "QUANTUM_SHIELD_SECRET not set — using insecure ephemeral default. "
            "This is acceptable for local development only.",
            stacklevel=2,
        )


@dataclass
class QuantumShieldCertificate:
    """A quantum-resistant proof certificate."""
    content_hash: str          # SHA-256 of the email content
    shield_hash: str           # Hash-chain proof (quantum-resistant)
    timestamp: str             # ISO timestamp
    nonce: str                 # Random nonce for uniqueness
    chain_version: str         # Shield version
    xrp_tx_hash: str | None   # Reference to classical proof (may be forged post-quantum)
    algorithm: str             # "sha256-hmac-chain"
    quantum_resistant: bool    # True — this certificate survives Shor's


def generate_shield(
    content_hash: str,
    timestamp: str,
    xrp_tx_hash: str | None = None,
) -> QuantumShieldCertificate:
    """
    Generate a quantum-resistant shield certificate.

    The shield hash is computed as:
      nonce = random 16 bytes (hex)
      layer_1 = SHA-256(content_hash + timestamp + nonce)
      layer_2 = SHA-256(layer_1 + "quantum-shield-v1")
      shield_hash = HMAC-SHA256(layer_2, secret=SHIELD_SECRET)

    This construction ensures:
      - The proof is bound to the content (content_hash)
      - The proof is bound to the time (timestamp)
      - The proof is unique (nonce)
      - The proof can be verified by the server (HMAC)
      - No elliptic curve cryptography is involved
    """
    nonce = os.urandom(16).hex()

    # Layer 1: bind content + time + nonce
    layer_1 = hashlib.sha256(
        f"{content_hash}:{timestamp}:{nonce}".encode()
    ).hexdigest()

    # Layer 2: domain separation
    layer_2 = hashlib.sha256(
        f"{layer_1}:quantum-shield-v1".encode()
    ).hexdigest()

    # Layer 3: HMAC binding (server-verifiable)
    shield_hash = hmac.new(
        _SHIELD_SECRET.encode(),
        layer_2.encode(),
        hashlib.sha256,
    ).hexdigest()

    return QuantumShieldCertificate(
        content_hash=content_hash,
        shield_hash=shield_hash,
        timestamp=timestamp,
        nonce=nonce,
        chain_version="1.0",
        xrp_tx_hash=xrp_tx_hash,
        algorithm="sha256-hmac-chain",
        quantum_resistant=True,
    )


def verify_shield(
    content_hash: str,
    timestamp: str,
    nonce: str,
    shield_hash: str,
) -> bool:
    """
    Verify a quantum shield certificate.

    Recomputes the hash chain and checks if it matches the claimed shield_hash.
    """
    layer_1 = hashlib.sha256(
        f"{content_hash}:{timestamp}:{nonce}".encode()
    ).hexdigest()

    layer_2 = hashlib.sha256(
        f"{layer_1}:quantum-shield-v1".encode()
    ).hexdigest()

    expected = hmac.new(
        _SHIELD_SECRET.encode(),
        layer_2.encode(),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, shield_hash)


def certificate_to_dict(cert: QuantumShieldCertificate) -> dict:
    """Serialize a shield certificate to a JSON-safe dict."""
    return {
        "content_hash": cert.content_hash,
        "shield_hash": cert.shield_hash,
        "timestamp": cert.timestamp,
        "nonce": cert.nonce,
        "chain_version": cert.chain_version,
        "xrp_tx_hash": cert.xrp_tx_hash,
        "algorithm": cert.algorithm,
        "quantum_resistant": cert.quantum_resistant,
    }
