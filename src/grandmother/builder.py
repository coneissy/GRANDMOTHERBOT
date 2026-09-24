from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from statistics import median

from .models import BuilderEconomics
from .economics import subsidized_block


def aggregate_builder_economics(rows: list[BuilderEconomics]) -> list[BuilderEconomics]:
    """Aggregate repeated builder/searcher observations by builder identifier."""
    buckets: dict[str, list[BuilderEconomics]] = defaultdict(list)
    for row in rows:
        buckets[row.builder].append(row)

    out: list[BuilderEconomics] = []
    for builder, items in buckets.items():
        out.append(
            BuilderEconomics(
                builder=builder,
                blocks=sum(x.blocks for x in items),
                bid_value_usd=sum((x.bid_value_usd for x in items), Decimal("0")),
                builder_profit_usd=sum(
                    (x.builder_profit_usd for x in items), Decimal("0")
                ),
                searcher_pnl_usd=(
                    sum(
                        (x.searcher_pnl_usd or Decimal("0") for x in items),
                        Decimal("0"),
                    )
                    if any(x.searcher_pnl_usd is not None for x in items)
                    else None
                ),
            )
        )
    return out


def is_block_subsidized(builder_profit_usd: Decimal, searcher_pnl_usd: Decimal) -> bool:
    aggregated = builder_profit_usd + searcher_pnl_usd
    return subsidized_block(builder_profit_usd, aggregated)
