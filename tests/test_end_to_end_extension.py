from decimal import Decimal

import pandas as pd

from grandmotherbot_extension.dynamic_hedge import evaluate_dynamic_hedge
from grandmotherbot_extension.hedge_alignment import align_quotes_to_swaps
from grandmotherbot_extension.hedge_simulator import simulate_hedge
from grandmotherbot_extension.normalization import normalize_book_ticker, normalize_swaps
from grandmotherbot_extension.token_mapping import build_contract_index, resolve_contract, CexToken


def test_dex_to_cex_hedge_extension_end_to_end():
    token_address = "0x" + "a" * 40
    index = build_contract_index([
        CexToken(symbol="ETH", contract_address=token_address, source="paper_crosscheck")
    ])
    mapped = resolve_contract(token_address.upper(), index=index)
    assert mapped is not None
    assert mapped.symbol == "ETH"

    swaps = normalize_swaps([{
        "tx_hash": "0xswap",
        "block_number": 100,
        "block_time": "2025-01-01T00:00:00Z",
        "tx_index": 3,
        "log_index": 12,
        "dex": "uniswap",
        "pool": "0x" + "b" * 40,
        "token_in": "0x" + "c" * 40,
        "token_out": token_address,
        "amount_in": "200",
        "amount_out": "2",
    }])
    swaps["cex_symbol"] = "ETHUSDT"
    swaps["event_time"] = "2025-01-01T00:00:01Z"

    raw_events = [{
        "capture_time": "2025-01-01T00:00:01.100Z",
        "message": {
            "e": "bookTicker",
            "E": 1735689601100,
            "s": "ETHUSDT",
            "b": "99.5",
            "a": "100.5",
            "B": "10",
            "A": "10",
        },
    }]
    quotes = normalize_book_ticker(raw_events)
    aligned = align_quotes_to_swaps(swaps, quotes, max_age_ms=500)
    assert aligned.iloc[0]["symbol"] == "ETHUSDT"
    assert aligned.iloc[0]["quote_stale"] is False

    order_book = pd.DataFrame([
        {"price": Decimal("99.5"), "quantity": Decimal("10"), "side": "bid"},
        {"price": Decimal("100.5"), "quantity": Decimal("10"), "side": "ask"},
    ])
    result = simulate_hedge(
        token_amount=Decimal("2"),
        inventory_delta=Decimal("2"),
        mid=Decimal("100"),
        order_book=order_book,
        taker_fee_bps=Decimal("15"),
        future_mid=Decimal("101"),
    )

    assert result["side"] == "sell"
    assert result["requested_qty"] == Decimal("2")
    assert result["filled_qty"] == Decimal("2")
    assert result["execution_price"] == Decimal("99.5")
    assert result["cex_fee_usd"] == Decimal("0.2985")
    assert result["residual_inventory_qty"] == Decimal("0")
    assert result["fully_filled"] is True
