from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import (
    build_instrument_context,
    get_balance_sheet,
    get_cashflow,
    get_fundamentals,
    get_income_statement,
    get_insider_transactions,
    get_language_instruction,
    bind_tools_safe,
)
from tradingagents.dataflows.config import get_config


def create_fundamentals_analyst(llm):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_fundamentals,
            get_balance_sheet,
            get_cashflow,
            get_income_statement,
        ]

        system_message = (
            "You are a researcher tasked with analyzing fundamental information over the past week about a company. Please write a comprehensive report of the company's fundamental information such as financial documents, company profile, basic company financials, and company financial history to gain a full view of the company's fundamental information to inform traders. Make sure to include as much detail as possible. Provide specific, actionable insights with supporting evidence to help traders make informed decisions."
            + " Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."
            + " Use the available tools: `get_fundamentals` for comprehensive company analysis, `get_balance_sheet`, `get_cashflow`, and `get_income_statement` for specific financial statements."
            + get_language_instruction()
        )

        is_ollama = get_config().get("llm_provider") == "ollama"
        if is_ollama:
            system_message += (
                "\n\n--- LOCAL MODEL (QWEN) INSTRUCTIONS ---\n"
                "You must perform your analysis and then IMMEDIATELY output your final report. "
                "Do NOT output function signatures, XML tags, or code comments. "
                "Output your analysis in clean Markdown. "
                "At the end of your report, you MUST append a formatted Markdown table summarizing the metrics. "
                "Here is an example of a high-quality final report structure:\n"
                "### Fundamental Analysis of [Metal Name] ([Ticker])\n"
                "Provide a detailed overview of the macroeconomic and fundamental data.\n\n"
                "### Key Observations\n"
                "- **Supply & Demand**: Discuss mine production, recycling, industrial/investment demand.\n"
                "- **Financial Data**: Summarize key metrics (e.g. 52-week range, moving average trends).\n"
                "- **Inventory Levels**: Discuss warehouse inventories (LME, COMEX, etc.).\n\n"
                "### Final Transaction Proposal\n"
                "**BUY/HOLD/SELL**: **[PROPOSAL]**\n\n"
                "### Summary Table\n"
                "| Metric | Value | Implications |\n"
                "|---|---|---|\n"
                "| 52 Week High | [Value] | [Comment] |\n"
                "| 52 Week Low | [Value] | [Comment] |\n"
                "| 50 Day Average | [Value] | [Comment] |\n"
                "| 200 Day Average | [Value] | [Comment] |\n"
            )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. {instrument_context}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(instrument_context=instrument_context)

        chain = prompt | bind_tools_safe(llm, tools)

        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "fundamentals_report": report,
        }

    return fundamentals_analyst_node
