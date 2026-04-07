import hashlib
import json
from datetime import datetime, timezone
from typing import Optional

import structlog
import xrpl
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from xrpl.clients import JsonRpcClient
from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.models.requests import Tx
from xrpl.models.transactions import Memo, Payment
from xrpl.transaction import submit_and_wait
from xrpl.wallet import Wallet

from app.core.config import settings
from app.core.quantum_shield import generate_shield, verify_shield, certificate_to_dict

logger = structlog.get_logger()
router = APIRouter()

# XRP network endpoints
NETWORK_URLS = {
    "mainnet": "https://xrplcluster.com",
    "testnet": "https://s.altnet.rippletest.net:51234",
    "devnet": "https://s.devnet.rippletest.net:51234",
}

EXPLORER_URLS = {
    "mainnet": "https://livenet.xrpl.org/transactions",
    "testnet": "https://testnet.xrpl.org/transactions",
    "devnet": "https://devnet.xrpl.org/transactions",
}


def _get_client() -> JsonRpcClient:
    url = NETWORK_URLS.get(settings.XRP_NETWORK)
    if not url:
        raise HTTPException(status_code=500, detail=f"Unknown XRP network: {settings.XRP_NETWORK}")
    return JsonRpcClient(url)


def _compute_hash(to: str, subject: str, body: str, timestamp: str) -> str:
    canonical = json.dumps(
        {
            "to": to.lower().strip(),
            "subject": subject.strip(),
            "body": body.strip(),
            "timestamp": timestamp,
        },
        sort_keys=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _explorer_url(tx_hash: str) -> str:
    base = EXPLORER_URLS.get(settings.XRP_NETWORK, EXPLORER_URLS["testnet"])
    return f"{base}/{tx_hash}"


# --- Request / Response models ---


class CertifyRequest(BaseModel):
    to: str
    subject: str
    body: str
    timestamp: Optional[str] = None


class VerifyRequest(BaseModel):
    transaction_hash: str
    to: Optional[str] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    timestamp: Optional[str] = None


class HashRequest(BaseModel):
    to: str
    subject: str
    body: str
    timestamp: Optional[str] = None


# --- Endpoints ---


@router.post("/certify")
async def certify(req: CertifyRequest):
    """Hash email content and write the proof to the XRP Ledger."""
    ts = datetime.now(timezone.utc).isoformat()  # Server-authoritative — client timestamps ignored for certification
    content_hash = _compute_hash(req.to, req.subject, req.body, ts)

    if not settings.XRP_WALLET_SEED:
        raise HTTPException(status_code=500, detail="XRP_WALLET_SEED not configured")

    wallet = Wallet.from_seed(settings.XRP_WALLET_SEED)
    client = _get_client()

    memo_payload = json.dumps(
        {
            "type": "certified-mail",
            "version": "1.0",
            "hash": content_hash,
            "algorithm": "sha256",
            "timestamp": ts,
            "recipient_hash": hashlib.sha256(req.to.lower().strip().encode()).hexdigest()[:16],
        }
    )

    memo = Memo(
        memo_type=bytes("text/plain", "utf-8").hex().upper(),
        memo_data=bytes(memo_payload, "utf-8").hex().upper(),
    )

    payment = Payment(
        account=wallet.address,
        destination=wallet.address,
        amount="1",  # 1 drop
        memos=[memo],
    )

    logger.info("certify_submitting", content_hash=content_hash, network=settings.XRP_NETWORK)

    try:
        response = submit_and_wait(payment, client, wallet)
    except Exception as e:
        logger.error("certify_failed", error=str(e))
        raise HTTPException(status_code=502, detail=f"XRP transaction failed: {e}")

    result = response.result
    tx_hash = result.get("hash", "")
    ledger_index = result.get("ledger_index", 0)
    fee = result.get("Fee", "0")

    logger.info("certify_success", tx_hash=tx_hash, ledger_index=ledger_index)

    # Generate quantum-resistant shield certificate
    shield = generate_shield(
        content_hash=content_hash,
        timestamp=ts,
        xrp_tx_hash=tx_hash,
    )
    logger.info("quantum_shield_generated", shield_hash=shield.shield_hash[:16])

    return {
        "success": True,
        "receipt": {
            "transaction_hash": tx_hash,
            "content_hash": content_hash,
            "ledger_index": ledger_index,
            "timestamp": ts,
            "network": settings.XRP_NETWORK,
            "fee": f"{fee} drops",
            "explorer_url": _explorer_url(tx_hash),
        },
        "quantum_shield": certificate_to_dict(shield),
    }


@router.post("/verify")
async def verify(req: VerifyRequest):
    """Verify a certified-mail proof on the XRP Ledger."""
    client = _get_client()

    try:
        tx_response = client.request(Tx(transaction=req.transaction_hash))
    except Exception as e:
        logger.error("verify_fetch_failed", error=str(e))
        raise HTTPException(status_code=502, detail=f"Failed to fetch transaction: {e}")

    result = tx_response.result

    if "meta" not in result and "validated" not in result:
        raise HTTPException(status_code=404, detail="Transaction not found or not validated")

    # Extract memo data
    memos = result.get("Memos", [])
    proof = None
    for m in memos:
        memo_obj = m.get("Memo", {})
        raw_data = memo_obj.get("MemoData", "")
        try:
            decoded = bytes.fromhex(raw_data).decode("utf-8")
            parsed = json.loads(decoded)
            if parsed.get("type") == "certified-mail":
                proof = parsed
                break
        except (ValueError, json.JSONDecodeError):
            continue

    if not proof:
        raise HTTPException(status_code=404, detail="No certified-mail proof found in transaction")

    # Content match check
    content_match = None
    if req.to and req.subject and req.body:
        ts = req.timestamp or proof.get("timestamp", "")
        computed = _compute_hash(req.to, req.subject, req.body, ts)
        content_match = computed == proof.get("hash")

    validated = result.get("validated", False)

    tx_hash = req.transaction_hash
    return {
        "verified": True,
        "content_match": content_match,
        "transaction_hash": tx_hash,
        "content_hash": proof.get("hash"),
        "timestamp": proof.get("timestamp"),
        "proof": {
            "hash": proof.get("hash"),
            "timestamp": proof.get("timestamp"),
            "recipient": proof.get("recipient", proof.get("recipient_hash", "")),
        },
        "transaction": {
            "hash": tx_hash,
            "ledger_index": result.get("ledger_index"),
            "validated": validated,
        },
        "explorer_url": _explorer_url(tx_hash),
    }


class ShieldVerifyRequest(BaseModel):
    content_hash: str
    timestamp: str
    nonce: str
    shield_hash: str


@router.post("/verify-shield")
async def verify_quantum_shield(req: ShieldVerifyRequest):
    """Verify a quantum shield certificate — no blockchain needed."""
    is_valid = verify_shield(
        content_hash=req.content_hash,
        timestamp=req.timestamp,
        nonce=req.nonce,
        shield_hash=req.shield_hash,
    )

    return {
        "verified": is_valid,
        "quantum_resistant": True,
        "algorithm": "sha256-hmac-chain",
        "note": "This verification uses only hash-based cryptography. It does not depend on ECDSA and remains valid even if transaction signatures are quantum-compromised.",
    }


@router.post("/hash")
async def hash_content(req: HashRequest):
    """Compute the SHA-256 hash of email content without submitting to the ledger."""
    ts = req.timestamp or datetime.now(timezone.utc).isoformat()
    content_hash = _compute_hash(req.to, req.subject, req.body, ts)
    return {"hash": content_hash, "algorithm": "sha256"}


@router.post("/generate-test-wallet")
async def generate_test_wallet():
    """Generate a funded testnet wallet for development."""
    if settings.ENVIRONMENT not in ("dev", "development", "test"):
        raise HTTPException(status_code=403, detail="Wallet generation disabled in production")
    if settings.XRP_NETWORK not in ("testnet", "devnet"):
        raise HTTPException(
            status_code=400,
            detail="Wallet generation only available on testnet or devnet",
        )

    client = _get_client()

    try:
        funded = xrpl.wallet.generate_faucet_wallet(client)
    except Exception as e:
        logger.error("wallet_generation_failed", error=str(e))
        raise HTTPException(status_code=502, detail=f"Faucet request failed: {e}")

    logger.info("test_wallet_generated", address=funded.address)

    return {
        "address": funded.address,
        "seed": funded.seed,
        "balance": "100 XRP (testnet)",
    }
