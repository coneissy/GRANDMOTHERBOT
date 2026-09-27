from decimal import Decimal

from grandmotherbot_paper.cex_mapping import BinanceToken, build_contract_index, map_effective_pair
from grandmotherbot_paper.tardis import TardisQuote
from grandmotherbot_paper.tardis_runner import MarkoutInput, build_markout_observation, two_leg_cex_fee


def quote(symbol: str, ts: int, price: str) -> TardisQuote:
    return TardisQuote(
        symbol=symbol,
        exchange_timestamp_us=ts,
        local_timestamp_us=ts,
        bid=Decimal(price) - Decimal("1"),
        ask=Decimal(price) + Decimal("1"),
    )


def test_contract_mapping_is_exact_and_case_insensitive():
    index = build_contract_index([
        BinanceToken("AAA", "0x0000000000000000000000000000000000000001"),
        BinanceToken("BBB", "0x0000000000000000000000000000000000000002"),
    ])
    bought, sold = map_effective_pair(
        "0x0000000000000000000000000000000000000001",
        "0x0000000000000000000000000000000000000002",
        index,
    )
    assert bought.matched and bought.symbol == "AAA"
    assert sold.matched and sold.symbol == "BBB"


def test_unmapped_contract_is_not_symbol_inferred():
    index = build_contract_index([
        BinanceToken("AAA", "0x0000000000000000000000000000000000000001"),
    ])
    bought, _ = map_effective_pair(
        "0x0000000000000000000000000000000000000003",
        "0x0000000000000000000000000000000000000001",
        index,
    )
    assert not bought.matched
    assert bought.reason == "not_in_binance_universe"


def test_two_leg_fee_uses_two_dex_notionals():
    assert two_leg_cex_fee(Decimal("1000"), Decimal("0.0001725")) == Decimal("0.345")


def test_runner_builds_all_23_points_without_lookahead():
    base = 1_700_000_000_000_000
    a = [quote("AAA", base - 1_000_000 + i * 500_000, "100") for i in range(25)]
    b = [quote("BBB", base - 1_000_000 + i * 500_000, "1") for i in range(25)]
    trade = MarkoutInput(
        Decimal("10"), Decimal("99"), Decimal("1000"), base,
        "AAA", "BBB",
    )
    obs = build_markout_observation(
        trade, {"AAA": a, "BBB": b}, Decimal("0.0001725")
    )
    assert len(obs.markouts) == 23
    assert obs.markouts[0].horizon_s == Decimal("-1.0")
    assert obs.markouts[-1].horizon_s == Decimal("10.0")
    assert obs.cex_taker_fees_usd == Decimal("0.345")
