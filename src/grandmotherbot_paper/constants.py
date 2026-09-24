from decimal import Decimal

PAPER_START_BLOCK = 17866488
PAPER_END_BLOCK = 21998438
PAPER_START_DATE = "2023-08-08"
PAPER_END_DATE = "2025-03-08"

HORIZONS = tuple(Decimal("-1.0") + Decimal("0.5") * i for i in range(23))

MAJOR_TOKENS = frozenset({
    "WETH", "WBTC", "USDT", "USDC", "TUSD", "FDUSD", "BUSD", "DAI"
})

# The paper removes these additional addresses manually in Appendix F.3.
MANUAL_EXCLUDED_ADDRESSES = frozenset({
    "0x00000000003b3cc22af3ae1eac0440bcee416b40",
    "0x000000d40b595b94918a28b27d1e2c66f43a51d3",
    "0x5ff137d4b0fdcd49dca30c7cf57e578a026d2789",
    "0xa8c1c98aaf99a5dfc907d61b892b2ad624901185",
    "0xfcb51642a2a33eafefd79c236480e295ccbd4a44",
})

KNOWN_PATTERN_BY_SEARCHER = {
    "Wintermute": (Decimal("1.5"), 1),
    "SCP": (Decimal("0.5"), 1),
    "Kayle": (Decimal("1.0"), 1),
    "Galio": (Decimal("0.5"), 1),
    "Shen": (Decimal("1.5"), 1),
    "Taric": (Decimal("1.0"), 2),
    "Lucian": (Decimal("1.0"), 2),
    "Riven": (Decimal("1.5"), 1),
    "Thresh": (Decimal("2.0"), 1),
    "Ahri": (Decimal("2.0"), 1),
    "Darius": (Decimal("0.5"), 1),
    "Karma": (Decimal("2.0"), 2),
    "Bard": (None, 3),
    "Senna": (Decimal("0.5"), 1),
    "Maokai": (Decimal("1.0"), 2),
    "Zed": (Decimal("1.5"), 2),
    "Jinx": (None, 3),
    "Tristana": (None, 3),
    "Graves": (Decimal("1.5"), 1),
    "Lux": (None, 3),
    "Caitlyn": (Decimal("1.0"), 1),
    "Akali": (Decimal("1.0"), 2),
    "Poppy": (Decimal("1.5"), 2),
}
