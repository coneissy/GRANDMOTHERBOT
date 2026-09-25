from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, Mapping, Sequence

from .tardis import NormalizedCexEvent


@dataclass(frozen=True)
class BboPoint:
    local_timestamp_us: int
    bid: Decimal | None
    bid_amount: Decimal | None
    ask: Decimal | None
    ask_amount: Decimal | None
    source: str
    capture_sequence: int

    @property
    def mid(self) -> Decimal | None:
        if self.bid is None or self.ask is None:
            return None
        return (self.bid + self.ask) / Decimal("2")

    @property
    def spread(self) -> Decimal | None:
        if self.bid is None or self.ask is None:
            return None
        return self.ask - self.bid

    @property
    def spread_bps(self) -> Decimal | None:
        mid = self.mid
        spread = self.spread
        if mid is None or spread is None or mid <= 0:
            return None
        return spread / mid * Decimal("10000")


@dataclass(frozen=True)
class FillResult:
    side: str
    requested_amount: Decimal
    filled_amount: Decimal
    vwap: Decimal | None
    notional: Decimal
    best_price: Decimal | None
    slippage_bps: Decimal | None
    complete: bool


@dataclass(frozen=True)
class PairHedgeResult:
    sell_a: FillResult
    buy_b: FillResult
    gross_proceeds_usd: Decimal
    gross_cost_usd: Decimal
    cex_fee_usd: Decimal
    net_hedge_value_usd: Decimal
    complete: bool


@dataclass
class OrderBookState:
    bids: dict[Decimal, Decimal]
    asks: dict[Decimal, Decimal]
    last_update_id: int | None = None
    valid: bool = True

    def reset(self) -> None:
        self.bids.clear()
        self.asks.clear()
        self.last_update_id = None
        self.valid = True

    def apply_snapshot(
        self,
        bids: Sequence[tuple[str, str]],
        asks: Sequence[tuple[str, str]],
        update_id: int | None,
    ) -> None:
        self.bids = {
            Decimal(price): Decimal(amount)
            for price, amount in bids
            if Decimal(amount) > 0
        }
        self.asks = {
            Decimal(price): Decimal(amount)
            for price, amount in asks
            if Decimal(amount) > 0
        }
        self.last_update_id = update_id
        self.valid = True

    def apply_depth(
        self,
        first_update_id: int | None,
        final_update_id: int | None,
        bids: Sequence[tuple[str, str]],
        asks: Sequence[tuple[str, str]],
    ) -> bool:
        if not self.valid:
            return False
        if final_update_id is None:
            self.valid = False
            return False

        if self.last_update_id is not None:
            if final_update_id <= self.last_update_id:
                return True
            if first_update_id is None:
                self.valid = False
                return False
            if not (
                first_update_id <= self.last_update_id + 1 <= final_update_id
            ):
                self.valid = False
                return False

        for price_text, amount_text in bids:
            price = Decimal(price_text)
            amount = Decimal(amount_text)
            if amount == 0:
                self.bids.pop(price, None)
            elif amount > 0:
                self.bids[price] = amount

        for price_text, amount_text in asks:
            price = Decimal(price_text)
            amount = Decimal(amount_text)
            if amount == 0:
                self.asks.pop(price, None)
            elif amount > 0:
                self.asks[price] = amount

        self.last_update_id = final_update_id
        return True

    def best(self) -> tuple[Decimal | None, Decimal | None, Decimal | None, Decimal | None]:
        best_bid = max(self.bids) if self.bids else None
        best_ask = min(self.asks) if self.asks else None
        return (
            best_bid,
            self.bids.get(best_bid) if best_bid is not None else None,
            best_ask,
            self.asks.get(best_ask) if best_ask is not None else None,
        )

    def levels(
        self,
        side: str,
        max_levels: int | None = None,
    ) -> list[tuple[Decimal, Decimal]]:
        if side == "buy":
            levels = sorted(self.asks.items(), key=lambda item: item[0])
        elif side == "sell":
            levels = sorted(
                self.bids.items(),
                key=lambda item: item[0],
                reverse=True,
            )
        else:
            raise ValueError("side must be buy or sell")
        return levels if max_levels is None else levels[:max_levels]


def reconstruct_bbo_from_l2(
    events: Iterable[NormalizedCexEvent],
) -> list[BboPoint]:
    ordered = sorted(
        (
            event
            for event in events
            if event.channel in {"depthSnapshot", "depth"}
        ),
        key=lambda event: (
            event.local_timestamp_us,
            event.capture_sequence,
        ),
    )
    book = OrderBookState(bids={}, asks={})
    points: list[BboPoint] = []
    seen_snapshot = False

    for event in ordered:
        if event.channel == "depthSnapshot" or event.is_snapshot:
            book.apply_snapshot(
                event.bids,
                event.asks,
                event.book_update_id,
            )
            seen_snapshot = True
        else:
            if not seen_snapshot:
                continue
            if not book.apply_depth(
                event.first_update_id,
                event.final_update_id,
                event.bids,
                event.asks,
            ):
                continue

        bid, bid_amount, ask, ask_amount = book.best()
        points.append(
            BboPoint(
                local_timestamp_us=event.local_timestamp_us,
                bid=bid,
                bid_amount=bid_amount,
                ask=ask,
                ask_amount=ask_amount,
                source="l2",
                capture_sequence=event.capture_sequence,
            )
        )
    return points


def bbo_from_book_ticker(
    events: Iterable[NormalizedCexEvent],
) -> list[BboPoint]:
    points: list[BboPoint] = []
    for event in sorted(
        (
            event
            for event in events
            if event.channel == "bookTicker"
        ),
        key=lambda event: (
            event.local_timestamp_us,
            event.capture_sequence,
        ),
    ):
        bid = (
            Decimal(event.best_bid)
            if event.best_bid is not None
            else None
        )
        bid_amount = (
            Decimal(event.best_bid_amount)
            if event.best_bid_amount is not None
            else None
        )
        ask = (
            Decimal(event.best_ask)
            if event.best_ask is not None
            else None
        )
        ask_amount = (
            Decimal(event.best_ask_amount)
            if event.best_ask_amount is not None
            else None
        )
        points.append(
            BboPoint(
                local_timestamp_us=event.local_timestamp_us,
                bid=bid,
                bid_amount=bid_amount,
                ask=ask,
                ask_amount=ask_amount,
                source="bookTicker",
                capture_sequence=event.capture_sequence,
            )
        )
    return points


def select_bbo(
    points: Sequence[BboPoint],
    target_timestamp_us: int,
    *,
    policy: str = "first_at_or_after",
) -> BboPoint | None:
    ordered = sorted(
        points,
        key=lambda item: (
            item.local_timestamp_us,
            item.capture_sequence,
        ),
    )
    if policy == "first_at_or_after":
        for point in ordered:
            if point.local_timestamp_us >= target_timestamp_us:
                return point
        return None
    if policy == "last_at_or_before":
        selected = None
        for point in ordered:
            if point.local_timestamp_us > target_timestamp_us:
                break
            selected = point
        return selected
    raise ValueError(
        "policy must be first_at_or_after or last_at_or_before"
    )


def markout_return(
    reference: BboPoint,
    target: BboPoint,
    *,
    direction: str,
) -> Decimal | None:
    if (
        reference.mid is None
        or target.mid is None
        or reference.mid <= 0
    ):
        return None
    direction_multiplier = (
        Decimal("1")
        if direction == "long"
        else Decimal("-1")
    )
    return (
        direction_multiplier
        * (target.mid - reference.mid)
        / reference.mid
    )


def _vwap_from_levels(
    side: str,
    levels: Sequence[tuple[Decimal, Decimal]],
    requested_amount: Decimal,
) -> FillResult:
    if side not in {"buy", "sell"}:
        raise ValueError("side must be buy or sell")
    if requested_amount <= 0:
        raise ValueError("requested amount must be positive")

    remaining = requested_amount
    notional = Decimal("0")
    filled = Decimal("0")
    best_price = levels[0][0] if levels else None

    for price, available in levels:
        if remaining <= 0:
            break
        take = min(remaining, available)
        if take <= 0:
            continue
        notional += price * take
        filled += take
        remaining -= take

    if filled <= 0:
        return FillResult(
            side=side,
            requested_amount=requested_amount,
            filled_amount=Decimal("0"),
            vwap=None,
            notional=Decimal("0"),
            best_price=best_price,
            slippage_bps=None,
            complete=False,
        )

    vwap = notional / filled
    if best_price is None or best_price <= 0:
        slippage = None
    elif side == "buy":
        slippage = (
            (vwap - best_price)
            / best_price
            * Decimal("10000")
        )
    else:
        slippage = (
            (best_price - vwap)
            / best_price
            * Decimal("10000")
        )

    return FillResult(
        side=side,
        requested_amount=requested_amount,
        filled_amount=filled,
        vwap=vwap,
        notional=notional,
        best_price=best_price,
        slippage_bps=slippage,
        complete=remaining == 0,
    )


def simulate_fill(
    book: OrderBookState,
    *,
    side: str,
    amount: Decimal,
    max_levels: int | None = 25,
) -> FillResult:
    return _vwap_from_levels(
        side=side,
        levels=book.levels(side, max_levels=max_levels),
        requested_amount=amount,
    )


def simulate_pair_hedge(
    *,
    symbol_a_book: OrderBookState,
    amount_a: Decimal,
    symbol_b_book: OrderBookState,
    amount_b: Decimal,
    cex_fee_rate: Decimal = Decimal("0"),
    max_levels: int | None = 25,
) -> PairHedgeResult:
    # A DEX trade that buys A and sells B can be neutralized by
    # selling A on Binance and buying B on Binance.
    sell_a = simulate_fill(
        symbol_a_book,
        side="sell",
        amount=amount_a,
        max_levels=max_levels,
    )
    buy_b = simulate_fill(
        symbol_b_book,
        side="buy",
        amount=amount_b,
        max_levels=max_levels,
    )
    proceeds = sell_a.notional
    cost = buy_b.notional
    fee_usd = (proceeds + cost) * cex_fee_rate
    net_value = proceeds - cost - fee_usd

    return PairHedgeResult(
        sell_a=sell_a,
        buy_b=buy_b,
        gross_proceeds_usd=proceeds,
        gross_cost_usd=cost,
        cex_fee_usd=fee_usd,
        net_hedge_value_usd=net_value,
        complete=sell_a.complete and buy_b.complete,
    )


def points_by_symbol(
    events: Iterable[NormalizedCexEvent],
    *,
    prefer: str = "bookTicker",
) -> Mapping[str, list[BboPoint]]:
    grouped: dict[str, list[NormalizedCexEvent]] = {}
    for event in events:
        grouped.setdefault(event.symbol, []).append(event)

    output: dict[str, list[BboPoint]] = {}
    for symbol, symbol_events in grouped.items():
        if prefer == "bookTicker" and any(
            event.channel == "bookTicker"
            for event in symbol_events
        ):
            output[symbol] = bbo_from_book_ticker(symbol_events)
        else:
            output[symbol] = reconstruct_bbo_from_l2(symbol_events)
    return output
