"""A scripted ADK BaseLlm adapter. Real Runner/tool orchestration; zero simulated intelligence claims."""

import json
from collections.abc import AsyncGenerator

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from pydantic import PrivateAttr


class DemoModel(BaseLlm):
    role: str
    _turn: int = PrivateAttr(default=0)

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        turn = self._turn
        self._turn += 1
        calls = {
            "lead_research": {
                0: ("search_web", {"query": "Thailand fintech expansion local hiring partnership"}),
                2: ("search_web", {"query": "Northstar compliance hiring Thailand verify signal"}),
            },
            "lead_critic": {
                1: ("finish_research", {"reason": "Two searches complete; fixture gaps disclosed"})
            },
            "cli_worker": {
                0: (
                    "gemini_cli",
                    {
                        "task": "Explain the DFS bug and propose regression tests",
                        "relative_path": "review_target",
                    },
                )
            },
            "bug_assistant": {
                0: ("search_issues", {"query": "duplicate checkout"}),
                1: ("get_issue", {"issue_id": "BUG-101"}),
                2: ("search_knowledge", {"query": "checkout idempotency"}),
            },
            "shop_assistant": {
                0: ("search_products", {"query": "running", "max_price_cents": 15000}),
                1: ("find_stores", {"city": "San Jose"}),
                2: ("prepare_order", {"product_id": "SHOE-001", "quantity": 1}),
            },
        }
        action = calls.get(self.role, {}).get(turn)
        if action:
            name, args = action
            part = types.Part.from_function_call(name=name, args=args)
        else:
            messages = {
                "lead_plan": "Research plan: discover expansion signals, verify with follow-up, rank with citations.",
                "lead_research": "Fixture evidence recorded. Report limitations and cite retrieved sources only.",
                "lead_critic": "Coverage gap: verify hiring signal with a second search before finishing.",
                "cli_plan": "Delegate read-only source analysis to the CLI tool, then summarize the returned evidence.",
                "cli_worker": "Subprocess completed. See the recorded tool result for the actual test plan.",
                "cli_report": "The CLI fixture found DFS and checkout functions. Fix stack initialization and test retries.",
                "bug_assistant": json.dumps(
                    {
                        "duplicate": "BUG-101",
                        "knowledge": ["KB-001"],
                        "reproduction": [
                            "Submit checkout twice with the same key",
                            "Compare order IDs and stock",
                        ],
                        "hypothesis": "Missing atomic idempotency enforcement; verify before changing code.",
                        "recommendation": "Unique customer/key constraint in one inventory transaction.",
                        "actions_taken": "Read existing issue and knowledge through real MCP; no new issue created.",
                    }
                ),
                "shop_assistant": "A 12900-cent quote was prepared using MCP. No order or payment exists yet. "
                "Review the quote and use the trusted confirmation endpoint.",
                "review_synthesis": json.dumps(
                    {
                        "summary": "Deterministic review found a DFS stack bug and unsafe SQL.",
                        "recommendations": [
                            "Initialize stack as [start]",
                            "Bind SQL parameters",
                            "Add regression tests",
                        ],
                    }
                ),
            }
            if self.role == "lead_report":
                message = json.dumps(
                    {
                        "market": "Thailand fintech (fictional demo)",
                        "patterns": ["local hiring", "regional partnership", "market pilot"],
                        "leads": [
                            {
                                "company": "Northstar Payments (fictional)",
                                "website": "https://northstar.example/",
                                "signals": ["local hiring", "regional partnership"],
                                "citations": [
                                    "https://northstar.example/expansion",
                                    "https://northstar.example/careers",
                                ],
                                "rationale": "Fixture evidence shows two market-entry signals, verified by a follow-up.",
                            },
                            {
                                "company": "Meridian Ledger (fictional)",
                                "website": "https://meridian.example/",
                                "signals": ["local hiring", "market pilot"],
                                "citations": ["https://meridian.example/news"],
                                "rationale": "Fixture evidence suggests early market exploration; verify before outreach.",
                            },
                        ],
                        "limitations": [
                            "All demo companies and sources are fictional .example fixtures.",
                            "Scores are heuristics; no contacts are harvested or messaged.",
                        ],
                    }
                )
            else:
                message = messages[self.role]
            part = types.Part.from_text(text=message)
        yield LlmResponse(
            content=types.Content(role="model", parts=[part]),
            partial=False,
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=0, candidates_token_count=0, total_token_count=0
            ),
        )
