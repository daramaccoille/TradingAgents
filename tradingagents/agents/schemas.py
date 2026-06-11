"""Pydantic schemas used by agents that produce structured output.

The framework's primary artifact is still prose: each agent's natural-language
reasoning is what users read in the saved markdown reports and what the
downstream agents read as context.  Structured output is layered onto the
three decision-making agents (Research Manager, Trader, Portfolio Manager)
so that:

- Their outputs follow consistent section headers across runs and providers
- Each provider's native structured-output mode is used (json_schema for
  OpenAI/xAI, response_schema for Gemini, tool-use for Anthropic)
- Schema field descriptions become the model's output instructions, freeing
  the prompt body to focus on context and the rating-scale guidance
- A render helper turns the parsed Pydantic instance back into the same
  markdown shape the rest of the system already consumes, so display,
  memory log, and saved reports keep working unchanged
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared rating types
# ---------------------------------------------------------------------------


class PortfolioRating(str, Enum):
    """5-tier rating used by the Research Manager and Portfolio Manager."""

    BUY = "Buy"
    OVERWEIGHT = "Overweight"
    HOLD = "Hold"
    UNDERWEIGHT = "Underweight"
    SELL = "Sell"


class TraderAction(str, Enum):
    """3-tier transaction direction used by the Trader.

    The Trader's job is to translate the Research Manager's investment plan
    into a concrete transaction proposal: should the desk execute a Buy, a
    Sell, or sit on Hold this round.  Position sizing and the nuanced
    Overweight / Underweight calls happen later at the Portfolio Manager.
    """

    BUY = "Buy"
    HOLD = "Hold"
    SELL = "Sell"


# ---------------------------------------------------------------------------
# Research Manager
# ---------------------------------------------------------------------------


class ResearchPlan(BaseModel):
    """Structured investment plan produced by the Research Manager.

    Hand-off to the Trader: the recommendation pins the directional view,
    the rationale captures which side of the bull/bear debate carried the
    argument, and the strategic actions translate that into concrete
    instructions the trader can execute against.
    """

    recommendation: PortfolioRating = Field(
        description=(
            "The investment recommendation. Exactly one of Buy / Overweight / "
            "Hold / Underweight / Sell. Reserve Hold for situations where the "
            "evidence on both sides is genuinely balanced; otherwise commit to "
            "the side with the stronger arguments."
        ),
    )
    rationale: str = Field(
        description=(
            "Conversational summary of the key points from both sides of the "
            "debate, ending with which arguments led to the recommendation. "
            "Speak naturally, as if to a teammate."
        ),
    )
    strategic_actions: str = Field(
        description=(
            "Concrete steps for the trader to implement the recommendation, "
            "including position sizing guidance consistent with the rating."
        ),
    )


def render_research_plan(plan: ResearchPlan) -> str:
    """Render a ResearchPlan to markdown for storage and the trader's prompt context."""
    return "\n".join([
        f"**Recommendation**: {plan.recommendation.value}",
        "",
        f"**Rationale**: {plan.rationale}",
        "",
        f"**Strategic Actions**: {plan.strategic_actions}",
    ])


# ---------------------------------------------------------------------------
# Trader
# ---------------------------------------------------------------------------


class TraderProposal(BaseModel):
    """Structured transaction proposal produced by the Trader.

    The trader reads the Research Manager's investment plan and the analyst
    reports, then turns them into a concrete transaction: what action to
    take, the reasoning that justifies it, and the practical levels for
    entry, stop-loss, and sizing.
    """

    action: TraderAction = Field(
        description="The transaction direction. Exactly one of Buy / Hold / Sell.",
    )
    reasoning: str = Field(
        description=(
            "The case for this action, anchored in the analysts' reports and "
            "the research plan. Two to four sentences."
        ),
    )
    entry_price: Optional[float] = Field(
        default=None,
        description="Optional entry price target in the instrument's quote currency.",
    )
    stop_loss: Optional[float] = Field(
        default=None,
        description=(
            "Stop-loss price in the instrument's quote currency. "
            "Direction rule: for a BUY action, stop_loss MUST be BELOW entry_price (protect against downside). "
            "For a SELL action, stop_loss MUST be ABOVE entry_price (protect against upside). "
            "Example BUY: entry=1700, stop_loss=1680. Example SELL: entry=1700, stop_loss=1720."
        ),
    )
    take_profit: Optional[float] = Field(
        default=None,
        description=(
            "Take-profit price in the instrument's quote currency. "
            "Direction rule: for a BUY action, take_profit MUST be ABOVE entry_price (capture upside). "
            "For a SELL action, take_profit MUST be BELOW entry_price (capture downside). "
            "Example BUY: entry=1700, take_profit=1740. Example SELL: entry=1700, take_profit=1660."
        ),
    )
    risk_reward_ratio: Optional[str] = Field(
        default=None,
        description="Optional risk-to-reward ratio, e.g., '1:2.0'.",
    )
    position_sizing: Optional[str] = Field(
        default=None,
        description="Optional sizing guidance, e.g. '5% of portfolio'.",
    )


def render_trader_proposal(proposal: TraderProposal) -> str:
    """Render a TraderProposal to markdown.

    Validates and corrects the SL/TP direction before rendering:
    - BUY:  stop_loss < entry_price < take_profit
    - SELL: take_profit < entry_price < stop_loss

    The trailing ``FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL**`` line is
    preserved for backward compatibility with the analyst stop-signal text
    and any external code that greps for it.
    """
    # Direction validation and correction
    if (
        proposal.action in (TraderAction.BUY, TraderAction.SELL)
        and proposal.entry_price is not None
        and proposal.stop_loss is not None
        and proposal.take_profit is not None
    ):
        entry = proposal.entry_price
        sl = proposal.stop_loss
        tp = proposal.take_profit
        if proposal.action == TraderAction.BUY:
            # BUY: sl < entry < tp
            if sl > entry or tp < entry:
                logger.warning(
                    "[TraderProposal] BUY signal has inverted SL/TP — "
                    "correcting: entry=%.2f sl=%.2f tp=%.2f",
                    entry, sl, tp,
                )
                # Swap if they look reversed
                if sl > tp:
                    sl, tp = tp, sl
                proposal.stop_loss = min(sl, entry - abs(entry - sl))
                proposal.take_profit = max(tp, entry + abs(tp - entry))
        elif proposal.action == TraderAction.SELL:
            # SELL: tp < entry < sl
            if sl < entry or tp > entry:
                logger.warning(
                    "[TraderProposal] SELL signal has inverted SL/TP — "
                    "correcting: entry=%.2f sl=%.2f tp=%.2f",
                    entry, sl, tp,
                )
                # Swap SL and TP (model gave BUY-style levels for a SELL)
                proposal.stop_loss, proposal.take_profit = tp, sl

    parts = [
        f"**Action**: {proposal.action.value}",
        "",
        f"**Reasoning**: {proposal.reasoning}",
    ]
    if proposal.entry_price is not None:
        parts.extend(["", f"**Entry Price**: {proposal.entry_price}"])
    if proposal.stop_loss is not None:
        parts.extend(["", f"**Stop Loss**: {proposal.stop_loss}"])
    if proposal.take_profit is not None:
        parts.extend(["", f"**Take Profit**: {proposal.take_profit}"])
    if proposal.risk_reward_ratio:
        parts.extend(["", f"**Risk Reward Ratio**: {proposal.risk_reward_ratio}"])
    if proposal.position_sizing:
        parts.extend(["", f"**Position Sizing**: {proposal.position_sizing}"])
    parts.extend([
        "",
        f"FINAL TRANSACTION PROPOSAL: **{proposal.action.value.upper()}**",
    ])
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Portfolio Manager
# ---------------------------------------------------------------------------


class PortfolioDecision(BaseModel):
    """Structured output produced by the Portfolio Manager.

    The model fills every field as part of its primary LLM call; no separate
    extraction pass is required. Field descriptions double as the model's
    output instructions, so the prompt body only needs to convey context and
    the rating-scale guidance.
    """

    rating: PortfolioRating = Field(
        description=(
            "The final position rating. Exactly one of Buy / Overweight / Hold / "
            "Underweight / Sell, picked based on the analysts' debate."
        ),
    )
    executive_summary: str = Field(
        description=(
            "A concise action plan covering entry strategy, position sizing, "
            "key risk levels, and time horizon. Two to four sentences."
        ),
    )
    investment_thesis: str = Field(
        description=(
            "Detailed reasoning anchored in specific evidence from the analysts' "
            "debate. If prior lessons are referenced in the prompt context, "
            "incorporate them; otherwise rely solely on the current analysis."
        ),
    )
    price_target: Optional[float] = Field(
        default=None,
        description="Optional target price in the instrument's quote currency.",
    )
    time_horizon: Optional[str] = Field(
        default=None,
        description="Optional recommended holding period, e.g. '3-6 months'.",
    )
    entry_price: Optional[float] = Field(
        default=None,
        description="Optional entry price or zone target in the instrument's quote currency.",
    )
    stop_loss: Optional[float] = Field(
        default=None,
        description=(
            "Stop-loss price in the instrument's quote currency. "
            "Direction rule: for a BUY/Overweight rating, stop_loss MUST be BELOW entry_price. "
            "For a SELL/Underweight rating, stop_loss MUST be ABOVE entry_price. "
            "Example BUY: entry=1700, stop_loss=1680. Example SELL: entry=1700, stop_loss=1720."
        ),
    )
    take_profit: Optional[float] = Field(
        default=None,
        description=(
            "Take-profit price in the instrument's quote currency. "
            "Direction rule: for a BUY/Overweight rating, take_profit MUST be ABOVE entry_price. "
            "For a SELL/Underweight rating, take_profit MUST be BELOW entry_price. "
            "Example BUY: entry=1700, take_profit=1740. Example SELL: entry=1700, take_profit=1660."
        ),
    )
    risk_reward_ratio: Optional[str] = Field(
        default=None,
        description="Optional risk-to-reward ratio, e.g., '1:2.0'.",
    )


def render_pm_decision(decision: PortfolioDecision) -> str:
    """Render a PortfolioDecision back to the markdown shape the rest of the system expects.

    Validates and corrects the SL/TP direction before rendering:
    - BUY / Overweight: stop_loss < entry_price < take_profit
    - SELL / Underweight: take_profit < entry_price < stop_loss

    Memory log, CLI display, and saved report files all read this markdown,
    so the rendered output preserves the exact section headers (``**Rating**``,
    ``**Executive Summary**``, ``**Investment Thesis**``) that downstream
    parsers and the report writers already handle.
    """
    # Direction validation and correction
    long_ratings = (PortfolioRating.BUY, PortfolioRating.OVERWEIGHT)
    short_ratings = (PortfolioRating.SELL, PortfolioRating.UNDERWEIGHT)
    if (
        decision.rating in long_ratings or decision.rating in short_ratings
    ) and (
        decision.entry_price is not None
        and decision.stop_loss is not None
        and decision.take_profit is not None
    ):
        entry = decision.entry_price
        sl = decision.stop_loss
        tp = decision.take_profit
        if decision.rating in long_ratings:
            if sl > entry or tp < entry:
                logger.warning(
                    "[PortfolioDecision] %s signal has inverted SL/TP — "
                    "correcting: entry=%.2f sl=%.2f tp=%.2f",
                    decision.rating.value, entry, sl, tp,
                )
                if sl > tp:
                    sl, tp = tp, sl
                decision.stop_loss = min(sl, entry - abs(entry - sl))
                decision.take_profit = max(tp, entry + abs(tp - entry))
        elif decision.rating in short_ratings:
            if sl < entry or tp > entry:
                logger.warning(
                    "[PortfolioDecision] %s signal has inverted SL/TP — "
                    "correcting: entry=%.2f sl=%.2f tp=%.2f",
                    decision.rating.value, entry, sl, tp,
                )
                decision.stop_loss, decision.take_profit = tp, sl

    parts = [
        f"**Rating**: {decision.rating.value}",
        "",
        f"**Executive Summary**: {decision.executive_summary}",
        "",
        f"**Investment Thesis**: {decision.investment_thesis}",
    ]
    if decision.price_target is not None:
        parts.extend(["", f"**Price Target**: {decision.price_target}"])
    if decision.time_horizon:
        parts.extend(["", f"**Time Horizon**: {decision.time_horizon}"])
    if decision.entry_price is not None:
        parts.extend(["", f"**Entry Price**: {decision.entry_price}"])
    if decision.stop_loss is not None:
        parts.extend(["", f"**Stop Loss**: {decision.stop_loss}"])
    if decision.take_profit is not None:
        parts.extend(["", f"**Take Profit**: {decision.take_profit}"])
    if decision.risk_reward_ratio:
        parts.extend(["", f"**Risk Reward Ratio**: {decision.risk_reward_ratio}"])
    return "\n".join(parts)
