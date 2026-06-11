"""
Unit tests for:
  - y_finance.py  : METAL_FUTURES_TICKERS guard on fundamentals functions
  - yfinance_news.py : METAL_FUTURES_NEWS_TERMS fallback search mapping
  - schemas.py     : SL/TP direction validation in render_trader_proposal and render_pm_decision
  - run_daily_reports_and_save_data.py : get_last_trading_day() logic

All tests run fully offline — no network calls, no LLM calls.
"""

import datetime
import pytest

# ---------------------------------------------------------------------------
# y_finance guards
# ---------------------------------------------------------------------------
from tradingagents.dataflows.y_finance import (
    METAL_FUTURES_TICKERS,
    _FUTURES_FUNDAMENTALS_MSG,
    get_fundamentals,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
    get_insider_transactions,
)


@pytest.mark.unit
class TestMetalFuturesTickers:
    """METAL_FUTURES_TICKERS contains the expected symbols."""

    def test_futures_tickers_contains_gold(self):
        assert "GC=F" in METAL_FUTURES_TICKERS

    def test_futures_tickers_contains_silver(self):
        assert "SI=F" in METAL_FUTURES_TICKERS

    def test_futures_tickers_contains_copper(self):
        assert "HG=F" in METAL_FUTURES_TICKERS

    def test_futures_tickers_contains_platinum(self):
        assert "PL=F" in METAL_FUTURES_TICKERS

    def test_futures_tickers_contains_palladium(self):
        assert "PA=F" in METAL_FUTURES_TICKERS

    def test_futures_tickers_contains_bare_symbols(self):
        """Bare symbols (without =F) are also guarded."""
        for sym in ("GC", "SI", "HG", "PL", "PA"):
            assert sym in METAL_FUTURES_TICKERS, f"{sym} should be guarded"


@pytest.mark.unit
class TestFundamentalsGuard:
    """Fundamentals functions short-circuit immediately for metal tickers."""

    METAL_TICKERS = ["GC=F", "SI=F", "HG=F", "PL=F", "PA=F",
                     "gc=f", "si=f",           # lower-case variants
                     "GC", "SI", "HG", "PL", "PA"]

    @pytest.mark.parametrize("ticker", METAL_TICKERS)
    def test_get_fundamentals_returns_msg(self, ticker):
        result = get_fundamentals(ticker)
        assert result == _FUTURES_FUNDAMENTALS_MSG, (
            f"get_fundamentals({ticker!r}) should return the guard message, got: {result!r}"
        )

    @pytest.mark.parametrize("ticker", METAL_TICKERS)
    def test_get_balance_sheet_returns_msg(self, ticker):
        result = get_balance_sheet(ticker)
        assert result == _FUTURES_FUNDAMENTALS_MSG

    @pytest.mark.parametrize("ticker", METAL_TICKERS)
    def test_get_cashflow_returns_msg(self, ticker):
        result = get_cashflow(ticker)
        assert result == _FUTURES_FUNDAMENTALS_MSG

    @pytest.mark.parametrize("ticker", METAL_TICKERS)
    def test_get_income_statement_returns_msg(self, ticker):
        result = get_income_statement(ticker)
        assert result == _FUTURES_FUNDAMENTALS_MSG

    @pytest.mark.parametrize("ticker", METAL_TICKERS)
    def test_get_insider_transactions_returns_msg(self, ticker):
        result = get_insider_transactions(ticker)
        assert result == _FUTURES_FUNDAMENTALS_MSG

    def test_equity_ticker_not_guarded(self):
        """AAPL should NOT be guarded (goes to the yfinance path).
        We just check the guard doesn't fire — a yfinance call will error in CI
        without network, so we patch it to verify control flow.
        """
        from unittest.mock import patch
        # Patch at the point get_fundamentals calls yf.Ticker so no network needed
        with patch("tradingagents.dataflows.y_finance.yf.Ticker") as mock_ticker:
            mock_ticker.return_value.info = {"shortName": "Apple Inc.", "sector": "Technology"}
            result = get_fundamentals("AAPL")
        # Result should NOT be the guard message
        assert result != _FUTURES_FUNDAMENTALS_MSG


# ---------------------------------------------------------------------------
# yfinance_news — news terms mapping
# ---------------------------------------------------------------------------
from tradingagents.dataflows.yfinance_news import METAL_FUTURES_NEWS_TERMS


@pytest.mark.unit
class TestMetalFuturesNewsTerms:
    """METAL_FUTURES_NEWS_TERMS maps every guarded futures ticker to a search term."""

    def test_gold_mapping(self):
        assert "GC=F" in METAL_FUTURES_NEWS_TERMS
        assert "gold" in METAL_FUTURES_NEWS_TERMS["GC=F"].lower()

    def test_silver_mapping(self):
        assert "SI=F" in METAL_FUTURES_NEWS_TERMS
        assert "silver" in METAL_FUTURES_NEWS_TERMS["SI=F"].lower()

    def test_copper_mapping(self):
        assert "HG=F" in METAL_FUTURES_NEWS_TERMS
        assert "copper" in METAL_FUTURES_NEWS_TERMS["HG=F"].lower()

    def test_platinum_mapping(self):
        assert "PL=F" in METAL_FUTURES_NEWS_TERMS
        assert "platinum" in METAL_FUTURES_NEWS_TERMS["PL=F"].lower()

    def test_palladium_mapping(self):
        assert "PA=F" in METAL_FUTURES_NEWS_TERMS
        assert "palladium" in METAL_FUTURES_NEWS_TERMS["PA=F"].lower()

    def test_global_news_handles_none_search_result(self):
        from unittest.mock import patch
        from tradingagents.dataflows.yfinance_news import get_global_news_yfinance
        with patch("tradingagents.dataflows.yfinance_news.yf.Search") as mock_search:
            mock_search.return_value = None
            result = get_global_news_yfinance("2026-06-11")
        assert "No global news found" in result


# ---------------------------------------------------------------------------
# schemas.py — SL/TP direction guards
# ---------------------------------------------------------------------------
from tradingagents.agents.schemas import (
    TraderAction,
    TraderProposal,
    PortfolioRating,
    PortfolioDecision,
    render_trader_proposal,
    render_pm_decision,
)


@pytest.mark.unit
class TestTraderProposalDirectionGuard:
    """render_trader_proposal corrects inverted SL/TP for BUY and SELL signals."""

    def _make_proposal(self, action, entry, sl, tp):
        return TraderProposal(
            action=action,
            entry_price=entry,
            stop_loss=sl,
            take_profit=tp,
            risk_reward_ratio="1:2",
            reasoning="test",
            conviction="High",
        )

    # --- BUY: correct (sl < entry < tp) — should NOT be corrected ---
    def test_buy_correct_levels_unchanged(self):
        p = self._make_proposal(TraderAction.BUY, 1700.0, 1680.0, 1740.0)
        render_trader_proposal(p)
        assert p.stop_loss == 1680.0
        assert p.take_profit == 1740.0

    # --- BUY: inverted (sl > entry) — should be corrected ---
    def test_buy_inverted_sl_tp_corrected(self):
        """Model output SL above entry for a BUY — guard must correct it."""
        p = self._make_proposal(TraderAction.BUY, 1700.0, 1740.0, 1660.0)
        render_trader_proposal(p)
        # After correction: sl < entry and tp > entry
        assert p.stop_loss is not None
        assert p.entry_price is not None
        assert p.take_profit is not None
        assert p.stop_loss < p.entry_price, (
            f"BUY stop_loss {p.stop_loss} should be < entry {p.entry_price}"
        )
        assert p.take_profit > p.entry_price, (
            f"BUY take_profit {p.take_profit} should be > entry {p.entry_price}"
        )


    # --- SELL: correct (tp < entry < sl) — should NOT be corrected ---
    def test_sell_correct_levels_unchanged(self):
        p = self._make_proposal(TraderAction.SELL, 1700.0, 1730.0, 1660.0)
        render_trader_proposal(p)
        assert p.stop_loss == 1730.0
        assert p.take_profit == 1660.0

    # --- SELL: inverted (TP above entry, SL below entry — BUY-style) ---
    def test_sell_inverted_sl_tp_corrected(self):
        """Platinum SELL bug: entry=1700, sl=1680, tp=1730 (BUY-style). Guard must swap."""
        p = self._make_proposal(TraderAction.SELL, 1700.0, 1680.0, 1730.0)
        render_trader_proposal(p)
        assert p.stop_loss is not None
        assert p.entry_price is not None
        assert p.take_profit is not None
        assert p.stop_loss > p.entry_price, (
            f"SELL stop_loss {p.stop_loss} should be > entry {p.entry_price}"
        )
        assert p.take_profit < p.entry_price, (
            f"SELL take_profit {p.take_profit} should be < entry {p.entry_price}"
        )

    # --- After swap, the specific values should be the original TP/SL swapped ---
    def test_sell_inverted_values_are_swapped(self):
        """Check the exact swap: original SL=1680 becomes TP, original TP=1730 becomes SL."""
        p = self._make_proposal(TraderAction.SELL, 1700.0, 1680.0, 1730.0)
        render_trader_proposal(p)
        assert p.take_profit == pytest.approx(1680.0)
        assert p.stop_loss == pytest.approx(1730.0)

    # --- HOLD: no SL/TP fields — no correction needed ---
    def test_hold_with_no_levels_no_error(self):
        p = TraderProposal(
            action=TraderAction.HOLD,
            entry_price=1700.0,
            stop_loss=None,
            take_profit=None,
            risk_reward_ratio=None,
            reasoning="Neutral",
            conviction="Low",
        )
        rendered = render_trader_proposal(p)
        assert "HOLD" in rendered or "Hold" in rendered


@pytest.mark.unit
class TestPortfolioDecisionDirectionGuard:
    """render_pm_decision corrects inverted SL/TP for BUY/Overweight and SELL/Underweight."""

    def _make_decision(self, rating, entry, sl, tp):
        return PortfolioDecision(
            rating=rating,
            entry_price=entry,
            stop_loss=sl,
            take_profit=tp,
            risk_reward_ratio="1:2",
            executive_summary="test",
            investment_thesis="test",
            risk_assessment="test",
            final_recommendation="test",
        )

    def test_sell_inverted_corrected(self):
        d = self._make_decision(PortfolioRating.SELL, 1700.0, 1660.0, 1740.0)
        render_pm_decision(d)
        assert d.stop_loss is not None
        assert d.entry_price is not None
        assert d.take_profit is not None
        assert d.stop_loss > d.entry_price
        assert d.take_profit < d.entry_price

    def test_underweight_inverted_corrected(self):
        d = self._make_decision(PortfolioRating.UNDERWEIGHT, 1700.0, 1660.0, 1740.0)
        render_pm_decision(d)
        assert d.stop_loss is not None
        assert d.entry_price is not None
        assert d.take_profit is not None
        assert d.stop_loss > d.entry_price
        assert d.take_profit < d.entry_price

    def test_buy_inverted_corrected(self):
        d = self._make_decision(PortfolioRating.BUY, 1700.0, 1740.0, 1660.0)
        render_pm_decision(d)
        assert d.stop_loss is not None
        assert d.entry_price is not None
        assert d.take_profit is not None
        assert d.stop_loss < d.entry_price
        assert d.take_profit > d.entry_price

    def test_hold_no_error(self):
        d = PortfolioDecision(
            rating=PortfolioRating.HOLD,
            entry_price=1700.0,
            stop_loss=None,
            take_profit=None,
            risk_reward_ratio=None,
            executive_summary="x",
            investment_thesis="x",
            risk_assessment="x",
            final_recommendation="x",
        )
        rendered = render_pm_decision(d)
        assert "Hold" in rendered or "HOLD" in rendered


# ---------------------------------------------------------------------------
# get_last_trading_day()
# ---------------------------------------------------------------------------
import sys
import importlib
import types

# Import the function directly from the pipeline script
import importlib.util, pathlib

_pipeline_path = pathlib.Path(__file__).parent.parent / "run_daily_reports_and_save_data.py"
_spec = importlib.util.spec_from_file_location("pipeline", _pipeline_path)
_pipeline_mod = importlib.util.module_from_spec(_spec)   # type: ignore[arg-type]
# Stub heavy imports so we don't trigger yfinance at import time
for _mod_name in ("yfinance", "run_metal_analysis"):
    _m = sys.modules.setdefault(_mod_name, types.ModuleType(_mod_name))
    if _mod_name == "run_metal_analysis":
        setattr(_m, "run_analysis_for_ticker", lambda *args, **kwargs: None)
_spec.loader.exec_module(_pipeline_mod)   # type: ignore[union-attr]

get_last_trading_day = _pipeline_mod.get_last_trading_day


@pytest.mark.unit
class TestGetLastTradingDay:
    """get_last_trading_day() skips weekends and CME holidays."""

    def test_weekday_returns_same_day(self):
        # Wednesday 2026-06-10
        d = datetime.date(2026, 6, 10)
        assert get_last_trading_day(d) == d

    def test_saturday_returns_friday(self):
        sat = datetime.date(2026, 6, 13)  # Saturday
        fri = datetime.date(2026, 6, 12)  # Friday
        assert sat.weekday() == 5         # sanity check
        assert get_last_trading_day(sat) == fri

    def test_sunday_returns_friday(self):
        sun = datetime.date(2026, 6, 14)
        fri = datetime.date(2026, 6, 12)
        assert get_last_trading_day(sun) == fri

    def test_christmas_2025_returns_previous_trading_day(self):
        # 25 Dec 2025 is Thursday (CME holiday); 24 Dec is Wednesday (regular)
        xmas = datetime.date(2025, 12, 25)
        expected = datetime.date(2025, 12, 24)
        assert get_last_trading_day(xmas) == expected

    def test_new_year_2026_returns_dec_31_2025(self):
        # 1 Jan 2026 is CME holiday; 31 Dec 2025 is Wednesday
        jan1 = datetime.date(2026, 1, 1)
        expected = datetime.date(2025, 12, 31)
        assert get_last_trading_day(jan1) == expected

    def test_returns_date_not_string(self):
        d = datetime.date(2026, 6, 10)
        result = get_last_trading_day(d)
        assert isinstance(result, datetime.date)
