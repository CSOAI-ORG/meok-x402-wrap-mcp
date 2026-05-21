"""Smoke tests for meok-x402-wrap-mcp."""
import sys, os, inspect, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import (
    wrap_tool,
    decode_payment_header,
    generate_402_challenge,
    verify_settlement,
    list_chains,
    sign_receipt,
    CHAINS,
)


def test_wrap_tool_emits_decorator_snippet():
    r = wrap_tool("my_tool", 5000, ["base"], "0x123")
    assert "@x402(price_micro_usd=5000" in r["decorator_snippet"]
    assert r["http_402_response_template"]["status"] == 402


def test_wrap_tool_rejects_bad_chain():
    r = wrap_tool("my_tool", 1000, ["fake_chain"])
    assert "error" in r


def test_decode_payment_header_extracts_tx_chain():
    r = decode_payment_header("tx=0xabc,chain=base")
    assert r["tx_hash"] == "0xabc"
    assert r["chain"] == "base"
    assert r["valid_format"] is True


def test_decode_payment_header_invalid_returns_false():
    r = decode_payment_header("just-some-text")
    assert r["valid_format"] is False


def test_generate_402_challenge_returns_status():
    r = generate_402_challenge(2500, ["base", "solana"])
    assert r["status"] == 402
    assert r["headers"]["X-X402-Price-Micro-USD"] == "2500"
    assert "base,solana" in r["headers"]["X-X402-Accepted-Chains"]


def test_verify_settlement_unknown_chain():
    r = verify_settlement("0xabcdef1234", "nope")
    assert "error" in r


def test_verify_settlement_empty_tx():
    r = verify_settlement("", "base")
    assert r["verified"] is False


def test_verify_settlement_stub_passes_valid_input():
    r = verify_settlement("0xabcdef1234", "base", expected_amount_micro_usd=5000)
    assert r["verified"] is True


def test_list_chains_has_four():
    r = list_chains()
    assert r["count"] == 4
    assert "base" in r["chains"]
    assert "lightning" in r["chains"]


def test_sign_receipt_emits_receipt():
    r = sign_receipt({"tx_hash": "0xabc", "chain": "base", "amount_micro_usd": 100})
    assert r["receipt_id"].startswith("R402_")
    assert "signature" in r


if __name__ == "__main__":
    g = dict(globals())
    fns = [v for k, v in g.items() if k.startswith("test_") and inspect.isfunction(v)]
    p = f = 0
    for fn in fns:
        try:
            fn(); print(f"OK {fn.__name__}"); p += 1
        except Exception as e:
            print(f"X  {fn.__name__}: {type(e).__name__}: {e}"); traceback.print_exc(); f += 1
    print(f"\n{p} passed, {f} failed")
