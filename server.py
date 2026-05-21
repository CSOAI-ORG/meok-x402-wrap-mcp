#!/usr/bin/env python3
"""
MEOK x402 Wrap MCP — 1-line USDC paywall for any FastMCP tool
================================================================

By MEOK AI Labs · https://meok.ai · MIT
<!-- mcp-name: io.github.CSOAI-ORG/meok-x402-wrap-mcp -->

WHAT THIS DOES
--------------
Coinbase x402 = HTTP 402 + on-chain settlement. ~165M agent transactions through
the protocol as of May 2026, moved to Linux Foundation Sept 2025.

Coinbase + Cloudflare + Vercel all ship examples — but nobody ships a universal
*wrapper* you can drop onto any FastMCP tool. This MCP gives you exactly that:
one decorator turns any tool into a pay-per-call endpoint settled in USDC on
Base / Polygon / Solana / Lightning.

PAIRS WITH
----------
- `agent-x402-paywall-mcp` (the FULL paywall MCP — this is a 1-liner)
- `agent-mcp-router-mcp` (route ALL your tools through one x402 wrapper)
- `agent-cost-allocator-mcp` (attribute x402 spend back to tenant)

TOOLS
-----
- wrap_tool(tool_name, price_micro_usd, settlement_chain): emit decorator config
- decode_payment_header(header_value): parse incoming x402 payment
- generate_402_challenge(price_micro_usd, accepted_chains): build 402 response
- verify_settlement(tx_hash, chain): check the settlement happened
- list_chains(): supported settlement chains
- sign_receipt(payment): HMAC-signed payment receipt for audit

PRICING
-------
Free MIT self-host · £29/mo Starter · £79/mo Pro · A2A Substrate £999/mo.
"""

from __future__ import annotations
import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timezone
from typing import Optional
from mcp.server.fastmcp import FastMCP


mcp = FastMCP("meok-x402-wrap")
_HMAC_SECRET = os.environ.get("MEOK_HMAC_SECRET", "")


# ──────────────────────────────────────────────────────────────────────
# x402 settlement chains supported as of May 2026
# ──────────────────────────────────────────────────────────────────────
CHAINS = {
    "base":      {"name": "Base (Coinbase L2)", "asset": "USDC", "decimals": 6,  "min_fee_micro_usd": 100},
    "polygon":   {"name": "Polygon",            "asset": "USDC", "decimals": 6,  "min_fee_micro_usd": 100},
    "solana":    {"name": "Solana",             "asset": "USDC", "decimals": 6,  "min_fee_micro_usd": 50},
    "lightning": {"name": "Bitcoin Lightning",  "asset": "BTC",  "decimals": 8,  "min_fee_micro_usd": 1},
}


def _sign(payload: dict) -> str:
    if not _HMAC_SECRET:
        return "unsigned-no-key-configured"
    return hmac.new(_HMAC_SECRET.encode(), json.dumps(payload, sort_keys=True).encode(), hashlib.sha256).hexdigest()


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


# ──────────────────────────────────────────────────────────────────────
# Tools
# ──────────────────────────────────────────────────────────────────────

@mcp.tool()
def wrap_tool(
    tool_name: str,
    price_micro_usd: int,
    settlement_chains: Optional[list[str]] = None,
    receiver_address: Optional[str] = None,
) -> dict:
    """
    Emit FastMCP decorator config that adds x402 paywall to a tool.

    Args:
        tool_name: Name of the tool to gate.
        price_micro_usd: Price per call in micro-USD (1,000,000 = $1).
        settlement_chains: List of accepted chains. Defaults to ["base"].
        receiver_address: On-chain address to receive settlement.

    Returns:
        {decorator_snippet, http_402_response_template}
    """
    chains = settlement_chains or ["base"]
    invalid = [c for c in chains if c not in CHAINS]
    if invalid:
        return {"error": f"Unsupported chains: {invalid}. Use one of {list(CHAINS)}"}

    snippet = f'''# Drop above your tool definition:
from meok_x402_wrap import x402

@x402(price_micro_usd={price_micro_usd}, chains={chains!r}, receiver={receiver_address!r})
@mcp.tool()
def {tool_name}(...):
    ...
'''
    http_402_template = {
        "status": 402,
        "x-x402-version": "1",
        "x-x402-price-micro-usd": price_micro_usd,
        "x-x402-accepted-chains": ",".join(chains),
        "x-x402-receiver": receiver_address or "<configure receiver_address>",
        "x-x402-nonce": "<server-generated-per-request>",
        "body": {
            "error": "payment_required",
            "settlement_chains": chains,
            "price_micro_usd": price_micro_usd,
            "hint": "Set X-X402-Payment-Tx-Hash header on retry to satisfy.",
        },
    }
    return {
        "decorator_snippet": snippet,
        "http_402_response_template": http_402_template,
        "next_step": "pip install meok-x402-wrap and add the decorator. See docs.meok.ai/x402.",
    }


@mcp.tool()
def decode_payment_header(header_value: str) -> dict:
    """
    Parse an X-X402-Payment header from an incoming MCP request.

    Args:
        header_value: The full X-X402-Payment-* header values (e.g. "tx=0x...,chain=base").

    Returns:
        {tx_hash, chain, parsed}
    """
    parsed = {}
    for part in header_value.split(","):
        if "=" in part:
            k, v = part.strip().split("=", 1)
            parsed[k.strip()] = v.strip()
    return {
        "tx_hash": parsed.get("tx"),
        "chain": parsed.get("chain"),
        "parsed": parsed,
        "valid_format": "tx" in parsed and "chain" in parsed,
    }


@mcp.tool()
def generate_402_challenge(price_micro_usd: int, accepted_chains: Optional[list[str]] = None) -> dict:
    """
    Build a complete HTTP 402 response for a paywall challenge.

    Args:
        price_micro_usd: Price in micro-USD.
        accepted_chains: List of accepted settlement chains.

    Returns:
        {status, headers, body}
    """
    chains = accepted_chains or ["base"]
    nonce = os.urandom(8).hex()
    return {
        "status": 402,
        "headers": {
            "X-X402-Version": "1",
            "X-X402-Price-Micro-USD": str(price_micro_usd),
            "X-X402-Accepted-Chains": ",".join(chains),
            "X-X402-Nonce": nonce,
            "Content-Type": "application/json",
        },
        "body": {
            "error": "payment_required",
            "price_micro_usd": price_micro_usd,
            "settlement_chains": chains,
            "nonce": nonce,
        },
    }


@mcp.tool()
def verify_settlement(tx_hash: str, chain: str = "base", expected_amount_micro_usd: Optional[int] = None) -> dict:
    """
    Verify an on-chain settlement matches the expected amount.

    NOTE: Scaffold — production calls each chain's RPC. Returns deterministic
    stub useful for unit tests + mocking.

    Args:
        tx_hash: Transaction hash from the X-X402-Payment header.
        chain: Settlement chain.
        expected_amount_micro_usd: Optional amount to validate against.

    Returns:
        {verified, chain, tx_hash, settlement_block, hint}
    """
    if chain not in CHAINS:
        return {"error": f"Unknown chain: {chain}. Use one of {list(CHAINS)}"}
    if not tx_hash or len(tx_hash) < 8:
        return {"verified": False, "reason": "tx_hash too short or empty"}
    # Scaffold result — production hits the chain RPC.
    return {
        "verified": True,
        "chain": chain,
        "tx_hash": tx_hash,
        "settlement_block": "scaffold_block",
        "amount_micro_usd": expected_amount_micro_usd,
        "hint": "Production replaces this stub with a chain RPC call (e.g. eth_getTransactionByHash).",
        "verified_at": _ts(),
    }


@mcp.tool()
def list_chains() -> dict:
    """Return the supported settlement chains + their parameters."""
    return {"chains": CHAINS, "count": len(CHAINS)}


@mcp.tool()
def sign_receipt(payment: dict) -> dict:
    """
    Emit a HMAC-signed payment receipt for audit chains.

    Args:
        payment: Dict of {tx_hash, chain, amount_micro_usd, tool_name, ...}

    Returns:
        {receipt_id, receipt, signature}
    """
    rid = f"R402_{int(time.time())}_{os.urandom(4).hex()}"
    sealed = {
        "receipt_id": rid,
        "spec": "X402_HMAC_v1",
        "payment": payment,
        "sealed_at": _ts(),
        "issuer": "MEOK AI Labs (CSOAI LTD)",
    }
    sig = _sign(sealed)
    return {
        "receipt_id": rid,
        "receipt": sealed,
        "signature": sig,
        "verify_url": f"https://meok-attestation-api.vercel.app/verify/{rid}",
    }


if __name__ == "__main__":
    mcp.run()
