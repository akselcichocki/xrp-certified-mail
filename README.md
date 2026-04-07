# XRP Certified Mail

**Blockchain-verified email proof system using the XRP Ledger.**

Certified mail for the internet age. Send an email, create a tamper-proof receipt on a public blockchain, and verify it forever — for less than a penny.

## How It Works

1. **Hash** — Email content (recipient, subject, body, timestamp) is hashed with SHA-256
2. **Certify** — The hash is written to an XRP Ledger transaction memo
3. **Receipt** — The transaction hash becomes your certified receipt
4. **Verify** — Anyone can look up the transaction on the public ledger and compare the hash

The XRP Ledger is used because transactions settle in 3-5 seconds and cost fractions of a cent (typically 10-12 drops, or ~$0.00001).

## Quantum Security Considerations

This system currently uses SHA-256 for content hashing and ECDSA (secp256k1) for XRP transaction signing.

**What is quantum-resistant:**
- SHA-256 content hashes — Grover's algorithm only provides a quadratic speedup, leaving effective security at 2^128

**What is NOT quantum-resistant:**
- ECDSA transaction signatures — Shor's algorithm can derive private keys from public keys in polynomial time
- XRP account keys — same ECDSA vulnerability

**Quantum Shield (experimental):**
The app includes an experimental "Quantum Shield" — a secondary proof layer using SHA-256 + HMAC hash chains that does not depend on ECDSA. This provides a server-side tamper-evident record alongside the blockchain proof.

Important limitations:
- The Shield is a server-side proof, not a publicly verifiable proof like the blockchain transaction
- It requires trust in the certifying server's HMAC secret
- It does not replace a post-quantum digital signature scheme
- The server-authoritative timestamp is used (client timestamps are ignored for certification)
- Recipient email addresses are hashed before writing to the public ledger

For research on post-quantum migration for digital assets, see the [Quantum Security Lab](https://p11.akselcichocki.com).

## Quick Start

### Using Docker
```bash
docker compose up
```
- Frontend: http://localhost:3001
- API: http://localhost:8001

### Manual Setup
```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --port 8000

# Frontend
cd frontend
npm install
node server.js
```

### Generate a Test Wallet
```bash
curl -X POST http://localhost:8001/api/v1/generate-test-wallet
```

### Certify an Email
```bash
curl -X POST http://localhost:8001/api/v1/certify \
  -H "Content-Type: application/json" \
  -d '{
    "to": "recipient@example.com",
    "subject": "Important Document",
    "body": "Please review the attached contract."
  }'
```

### Verify a Receipt
```bash
curl -X POST http://localhost:8001/api/v1/verify \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_hash": "YOUR_TX_HASH_HERE"
  }'
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/certify | Certify email content on the XRP Ledger |
| POST | /api/v1/verify | Verify a certified mail receipt |
| POST | /api/v1/hash | Compute content hash without submitting |
| POST | /api/v1/generate-test-wallet | Generate a funded XRP testnet wallet |
| GET | /api/v1/health | Health check |

## Architecture

Built on the Magic Runtime pattern:
- **Backend**: FastAPI (Python) with xrpl-py
- **Frontend**: Static HTML/CSS/JS served by Express
- **Ledger**: XRP Testnet (configurable to mainnet)

## Security Notes

This is an experimental prototype, not production-grade software.

- **Rate limiting**: Basic in-memory rate limiting (30 req/min per IP)
- **CORS**: Restricted to certmail.akselcichocki.com and localhost
- **Privacy**: Recipient email is hashed (not stored raw) on the public ledger
- **Timestamps**: Server-authoritative — client-supplied timestamps are ignored for certification
- **Wallet generation**: Disabled outside dev/test environments
- **Shield secret**: Requires `QUANTUM_SHIELD_SECRET` env var — warns loudly if missing

For production use, additional safeguards would be required including proper key management, authentication, and audit logging.

## License

MIT — Aksel Cichocki

## Related

- [Quantum Security Lab](https://p11.akselcichocki.com) — Post-quantum security research
- [Bitcoin Quantum Exposure Tester](https://p11.akselcichocki.com/tester) — Check Bitcoin address quantum exposure
- [XRP Ledger Documentation](https://xrpl.org)
