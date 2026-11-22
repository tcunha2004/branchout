import httpx
from langchain.messages import ToolMessage
from langchain.tools import ToolRuntime, tool
from langgraph.types import Command


@tool
def save_profile(
    experience: str,
    career_plan: str,
    preferences: str,
    runtime: ToolRuntime,
) -> Command:
    """Save the user profile in the Agent State.

    Call this as soon as all three pieces of information have been collected.

    Args:
        experience: what the user already knows or has built
        career_plan: the career the user wants and the time frame
        preferences: what the user likes and what motivates them
    """
    return Command(
        update={
            "profile": {
                "experience": experience,
                "career_plan": career_plan,
                "preferences": preferences,
            },
            "messages": [
                ToolMessage("Profile saved.", tool_call_id=runtime.tool_call_id)
            ],
        }
    )


@tool
def check_links(urls: list[str]) -> str:
    """Check if the given URLs are reachable. Returns which ones are invalid.

    Args:
        urls: all the links that will be given to the user
    """
    invalid = []
    for url in urls:
        try:
            r = httpx.get(url, follow_redirects=True, timeout=10)
            if r.status_code >= 400:
                invalid.append(f"{url} (HTTP {r.status_code})")
        except httpx.HTTPError as e:
            invalid.append(f"{url} ({type(e).__name__})")
    if not invalid:
        return "All links valid."
    return "Invalid links:\n" + "\n".join(invalid)
