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

This system currently uses SHA-256 for content hashing and ECDSA (secp256k1) for XRP transaction signing. While SHA-256 is considered quantum-resistant (Grover's algorithm only provides a quadratic speedup), the ECDSA signing keys are vulnerable to Shor's algorithm on a sufficiently powerful quantum computer.

**What this means:**
- Content hashes remain trustworthy in a post-quantum world
- Transaction signing keys could theoretically be forged by a future quantum computer
- The XRP Ledger community is exploring post-quantum signature schemes

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

## License

MIT — Aksel Cichocki

## Related

- [Quantum Security Lab](https://p11.akselcichocki.com) — Post-quantum security research
- [Bitcoin Quantum Exposure Tester](https://p11.akselcichocki.com/tester) — Check Bitcoin address quantum exposure
- [XRP Ledger Documentation](https://xrpl.org)
