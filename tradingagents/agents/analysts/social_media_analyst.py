from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from tradingagents.agents.utils.agent_utils import build_instrument_context, get_language_instruction, get_news, bind_tools_safe
from tradingagents.dataflows.config import get_config


def create_social_media_analyst(llm):
    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        tools = [
            get_news,
        ]

        system_message = (
            "You are a social media and metal or company specific news researcher/analyst tasked with analyzing social media posts, recent company news, and public sentiment for a specific company over the past week. You will be given a company's name your objective is to write a comprehensive long report detailing your analysis, insights, and implications for traders and investors on this company's current state after looking at social media and what people are saying about that company, analyzing sentiment data of what people feel each day about the company, and looking at recent company news. Use the get_news(query, start_date, end_date) tool to search for company-specific news and social media discussions. Try to look at all sources possible from social media to sentiment to news. Provide specific, actionable insights with supporting evidence to help traders make informed decisions."
            + """ Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."""
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
                "### Social Media & Sentiment Analysis of [Metal Name] ([Ticker])\n"
                "Provide a detailed overview of public sentiment and social trends.\n\n"
                "### Key Observations\n"
                "- **Public/Retail Sentiment**: Summarize what people are saying on Twitter, Reddit, and forums.\n"
                "- **Media Mentions**: Public sentiment and media coverage tone.\n\n"
                "### Final Transaction Proposal\n"
                "**BUY/HOLD/SELL**: **[PROPOSAL]**\n\n"
                "### Summary Table\n"
                "| Platform | Sentiment Tone | Key Discussion Points |\n"
                "|---|---|---|\n"
                "| Social Media | [Positive/Negative/Neutral] | [Main talking points] |\n"
                "| Industry Forums | [Positive/Negative/Neutral] | [Main talking points] |\n"
                "| News Sentiment | [Positive/Negative/Neutral] | [Main talking points] |\n"
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
            "sentiment_report": report,
        }

    return social_media_analyst_node
