from grandmotherbot.verification_contracts import (
    all_pass,
    verify_book_cap,
    verify_profit_chain,
    verify_timestamp_order,
)


def test_profit_chain_is_explicit():
    results = verify_profit_chain(120.0, 10.0, 5.0, 110.0, 105.0)
    assert all_pass(results)


def test_profit_chain_detects_wrong_accounting():
    results = verify_profit_chain(120.0, 10.0, 5.0, 111.0, 105.0)
    assert not all_pass(results)


def test_book_cap_is_fail_closed():
    assert verify_book_cap(100).passed
    assert not verify_book_cap(101).passed


def test_timestamp_contract():
    assert verify_timestamp_order(10, 11).passed
    assert not verify_timestamp_order(11, 10).passed
