# MEOK x402 Wrap MCP

> ## 🧱 Part of the MEOK A2A Substrate (£999/mo)
> See [meok.ai/a2a](https://meok.ai/a2a).

# 1-line USDC paywall for any FastMCP tool

<!-- mcp-name: io.github.CSOAI-ORG/meok-x402-wrap-mcp -->

[![PyPI](https://img.shields.io/pypi/v/meok-x402-wrap-mcp)](https://pypi.org/project/meok-x402-wrap-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## What this does

Coinbase x402 = HTTP 402 + on-chain settlement. ~165M agent transactions through the protocol as of May 2026; moved to Linux Foundation Sept 2025. Coinbase + Cloudflare + Vercel all ship examples but nobody ships a *universal* wrapper.

This MCP gives you exactly that — one decorator turns any FastMCP tool into a pay-per-call endpoint settled in **USDC on Base / Polygon / Solana** or **BTC on Lightning**.

```python
from meok_x402_wrap import x402

@x402(price_micro_usd=5000, chains=["base"], receiver="0xYourAddress")
@mcp.tool()
def my_pay_per_call_tool(arg: str) -> dict:
    ...
```

## Tools

| Tool | Purpose |
|---|---|
| `wrap_tool(tool_name, price_micro_usd, chains, receiver?)` | Emit decorator config |
| `decode_payment_header(header_value)` | Parse incoming X-X402-Payment header |
| `generate_402_challenge(price_micro_usd, chains)` | Build HTTP 402 response |
| `verify_settlement(tx_hash, chain, expected_amount?)` | On-chain check |
| `list_chains()` | Supported settlement chains |
| `sign_receipt(payment)` | HMAC-signed audit receipt |

## Sister MCPs

- `agent-x402-paywall-mcp` — full x402 paywall MCP (this is the 1-line wrapper variant)
- `agent-commerce-protocol-mcp` — Stripe ACP + Google AP2 + x402 bridge
- `agent-cost-allocator-mcp` — attribute x402 spend back to upstream tenant
- `agent-mcp-router-mcp` — route ALL your tools through one x402 wrapper

Full catalogue: [meok.ai/anthropic-registry](https://meok.ai/anthropic-registry)

## Pricing

| Option | Price |
|---|---|
| Self-host MIT | £0 |
| Universal PAYG | £29/mo + £0.0002/call |
| A2A Substrate | £999/mo |
| Universe | £1,499/mo |
| Defence | £4,990/mo |

Buy: https://meok.ai/a2a

## Licence

MIT. By [MEOK AI Labs](https://meok.ai) (CSOAI LTD, UK Companies House 16939677).
