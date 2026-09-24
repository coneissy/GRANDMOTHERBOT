from __future__ import annotations

from decimal import Decimal

from .builder import is_block_subsidized
from .economics import TradeEconomics
from .liquidity import LiquidityPoint, choose_size
from .models import MarkoutPoint, HedgeObservation
from .reconstruction import reconstruct_effective_trade
from .markout import optimal_horizon, classify_pattern
from .execution import PaperExecutor
from .models import PoolSwap


def demo() -> None:
    prices = {"WETH": Decimal("3500"), "USDC": Decimal("1"), "DAI": Decimal("1")}
    swaps = (
        PoolSwap("pool-1", "uniswap_v3", "WETH", "USDC", Decimal("1"), Decimal("3490")),
        PoolSwap("pool-2", "uniswap_v3", "USDC", "DAI", Decimal("3490"), Decimal("3490")),
    )
    effective = reconstruct_effective_trade(swaps, prices)
    points = tuple(
        MarkoutPoint(
            Decimal("-1.0") + Decimal("0.5") * i,
            Decimal("3500") + Decimal(i) * Decimal("0.5"),
            Decimal("1"),
        )
        for i in range(23)
    )
    obs = HedgeObservation(
        token_a="WETH",
        token_b="USDC",
        amount_a=effective.amount_a,
        amount_b=effective.amount_b,
        dex_volume_usd=effective.volume_token_a_usd,
        cex_taker_fee_usd=Decimal("0.50"),
        markouts=points,
    )
    t_star = optimal_horizon([obs])
    pattern = classify_pattern([obs])
    size = choose_size([
        LiquidityPoint(Decimal("1000"), Decimal("1004"), Decimal("1000"), Decimal("2"), Decimal("1")),
        LiquidityPoint(Decimal("2000"), Decimal("2010"), Decimal("2000"), Decimal("3"), Decimal("2")),
    ])
    economics = TradeEconomics(Decimal("15"), Decimal("2"), Decimal("3"))
    decision = PaperExecutor().decide(economics.estimated_pnl_usd, Decimal("1"))
    print("GrandMother demo")
    print({"effective_trade": effective, "t_star_s": t_star, "pattern": pattern.value})
    print({"best_size_usd": size.size_usd, "expected_size_pnl_usd": size.expected_pnl_usd})
    print({"estimated_ev_usd": economics.estimated_ev_usd,
           "estimated_pnl_usd": economics.estimated_pnl_usd,
           "profit_margin": economics.profit_margin,
           "paper_execute": decision.execute})
    print({"subsidized_example": is_block_subsidized(Decimal("-1"), Decimal("0.5"))})


def main() -> None:
    demo()


if __name__ == "__main__":
    main()
