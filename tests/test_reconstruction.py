from decimal import Decimal

import pytest

from grandmotherbot_paper.reconstruction import Swap, reconstruct_effective_trade


def test_multi_swap_reconstruction():
    result = reconstruct_effective_trade((
        Swap("A", "B", Decimal("10"), Decimal("20"), 0),
        Swap("B", "C", Decimal("20"), Decimal("30"), 1),
    ))
    assert result.token_bought == "C"
    assert result.amount_bought == Decimal("30")
    assert result.token_sold == "A"
    assert result.amount_sold == Decimal("10")


@pytest.mark.parametrize(
    "swaps",
    [
        (Swap("A", "B", Decimal("0"), Decimal("1")),),
        (Swap("A", "B", Decimal("1"), Decimal("0")),),
        (Swap("", "B", Decimal("1"), Decimal("1")),),
        (Swap("A", "", Decimal("1"), Decimal("1")),),
        (Swap("A", "A", Decimal("1"), Decimal("1")),),
    ],
)
def test_multi_swap_reconstruction_rejects_invalid_swap_legs(swaps):
    with pytest.raises(ValueError):
        reconstruct_effective_trade(swaps)
