from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable, Sequence


@dataclass(frozen=True)
class LayerZeroEvent:
    """Canonical cross-chain activity event derived from LayerZero sends."""

    sender: str
    call_block_time: datetime
    src_chain_id: int
    dst_chain_id: int
    tx_hash: str | None = None

    def __post_init__(self) -> None:
        if self.call_block_time.tzinfo is None:
            raise ValueError("call_block_time must be timezone-aware")
        if self.src_chain_id <= 0 or self.dst_chain_id <= 0:
            raise ValueError("chain IDs must be positive")

    @property
    def cross_chain(self) -> bool:
        return self.src_chain_id != self.dst_chain_id


@dataclass(frozen=True)
class CrossChainProfile:
    sender: str
    user_tx_count: int
    unique_source_chains: tuple[int, ...]
    unique_destination_chains: tuple[int, ...]
    unique_chain_pairs: tuple[tuple[int, int], ...]
    first_activity: datetime | None
    last_activity: datetime | None

    @property
    def source_chain_count(self) -> int:
        return len(self.unique_source_chains)

    @property
    def destination_chain_count(self) -> int:
        return len(self.unique_destination_chains)

    @property
    def chain_pair_count(self) -> int:
        return len(self.unique_chain_pairs)


def parse_dune_layerzero_rows(rows: Iterable[dict]) -> list[LayerZeroEvent]:
    """Convert Dune rows to canonical LayerZero events."""
    events: list[LayerZeroEvent] = []
    for row in rows:
        value = row["call_block_time"]
        if isinstance(value, datetime):
            timestamp = value
        else:
            timestamp = datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        events.append(
            LayerZeroEvent(
                sender=str(row["sender"]).lower(),
                call_block_time=timestamp.astimezone(timezone.utc),
                src_chain_id=int(
                    row["_srcChainId"]
                    if "_srcChainId" in row
                    else row["src_chain_id"]
                ),
                dst_chain_id=int(
                    row["_dstChainId"]
                    if "_dstChainId" in row
                    else row["dst_chain_id"]
                ),
                tx_hash=(
                    str(row["tx_hash"]).lower()
                    if row.get("tx_hash")
                    else None
                ),
            )
        )
    return events


def build_cross_chain_profiles(
    events: Sequence[LayerZeroEvent],
) -> list[CrossChainProfile]:
    grouped: dict[str, list[LayerZeroEvent]] = {}
    for event in events:
        grouped.setdefault(event.sender, []).append(event)

    profiles: list[CrossChainProfile] = []
    for sender, sender_events in grouped.items():
        sources = sorted({event.src_chain_id for event in sender_events})
        destinations = sorted(
            {event.dst_chain_id for event in sender_events}
        )
        pairs = sorted(
            {
                (event.src_chain_id, event.dst_chain_id)
                for event in sender_events
            }
        )
        timestamps = sorted(
            event.call_block_time for event in sender_events
        )
        profiles.append(
            CrossChainProfile(
                sender=sender,
                user_tx_count=len(sender_events),
                unique_source_chains=tuple(sources),
                unique_destination_chains=tuple(destinations),
                unique_chain_pairs=tuple(pairs),
                first_activity=timestamps[0] if timestamps else None,
                last_activity=timestamps[-1] if timestamps else None,
            )
        )
    return sorted(
        profiles,
        key=lambda profile: (-profile.user_tx_count, profile.sender),
    )


def attach_cross_chain_features(
    candidate_addresses: Iterable[str],
    profiles: Sequence[CrossChainProfile],
) -> dict[str, dict[str, object]]:
    """Attach descriptive cross-chain features to GM01 addresses.

    These features indicate bridge or cross-chain activity only. They are not
    an arbitrage classifier and do not prove a cross-chain hedge.
    """
    by_sender = {profile.sender: profile for profile in profiles}
    result: dict[str, dict[str, object]] = {}
    for address in candidate_addresses:
        key = str(address).lower()
        profile = by_sender.get(key)
        result[key] = {
            "layerzero_user_tx_count": (
                profile.user_tx_count if profile else 0
            ),
            "layerzero_source_chain_count": (
                profile.source_chain_count if profile else 0
            ),
            "layerzero_destination_chain_count": (
                profile.destination_chain_count if profile else 0
            ),
            "layerzero_chain_pair_count": (
                profile.chain_pair_count if profile else 0
            ),
            "layerzero_first_activity": (
                profile.first_activity if profile else None
            ),
            "layerzero_last_activity": (
                profile.last_activity if profile else None
            ),
        }
    return result


def bridge_activity_score(
    user_tx_count: int,
    source_chain_count: int,
    destination_chain_count: int,
) -> Decimal:
    """Simple descriptive feature, not a probability or ranking."""
    if min(
        user_tx_count, source_chain_count, destination_chain_count
    ) < 0:
        raise ValueError("cross-chain activity counts cannot be negative")
    return Decimal(user_tx_count) * Decimal(
        max(1, source_chain_count + destination_chain_count)
    )
