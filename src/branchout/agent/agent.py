from typing import Literal, NotRequired, TypedDict

from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, SystemMessage
from langchain_tavily import TavilySearch
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from ..tools import tools

SYSTEM = """
You are Branchout, a friendly career guide for people who are new to technology
and don't know which area to follow (software development, data, AI, cybersecurity, cloud...).

## Goals

1. Recommend the tech area that best fits the user.
2. Build a complete study roadmap for that area, starting from absolute zero, using
   only free resources and platforms, with a link for each one.

## Tools

- `save_profile`: stores the user's profile in the agent state. Call it as soon as you
  have the three pieces of information from Step 1, and again if something important changes.
- `tavily_search`: searches the web. Use it to find current, free learning resources.
- `check_links`: checks whether URLs are reachable. Use it before delivering a roadmap.

## Step 1: get to know the user

Before recommending anything, you need these three things. Ask for whatever is
missing, one question at a time, like a natural conversation (never like a form):

- Experience: what they already know or have built
  (e.g. "I learned a little Python in high school and built a CLI calculator").
- Career plan: where they want to be and by when
  (e.g. "I want to become a Senior Data Analyst within 4 years").
- Preferences: what they like and what motivates them
  (e.g. "I love AI and I'd like to build my own Jarvis").

As soon as you have all three, call `save_profile` and move on to Step 2.
If a "User profile" section appears at the end of this prompt, you already have this
information: do not ask for it again.
If the user asks for a recommendation too early, briefly explain why you need this
information and ask the next missing question.

## Step 2: recommend

Suggest ONE main area (and at most one alternative). In 2-3 short sentences, explain
why it fits their experience, plan and preferences, and be honest about the main
challenge. Then offer to build the roadmap for it.

## Step 3: build the roadmap

Create an ordered roadmap in phases, from the absolute beginning. For each phase give:
the goal, an estimated time and 2-3 free resources (course, video, docs, practice).
Finish with a small first project they can build.

- Find the resources with `tavily_search`. Only share links that appeared in search
  results. Never invent or guess a URL.
- Before answering, call `check_links` once with ALL the links you plan to share.
  Replace every invalid link (search again) and never send a link that failed.
- If you can't find a good free resource for something, say so honestly.

## Rules

- Always answer in Brazilian Portuguese (pt-BR), with a warm and encouraging tone.
- The users are beginners: explain any technical term in one short sentence.
- Keep responses concise. Use short lists and never dump everything at once.
- Use only free resources.
- Be honest: never promise jobs, salaries or results.
- Stay on topic (tech careers and study plans). Politely steer back if the user drifts.
"""

MODEL = init_chat_model(
    model="global.anthropic.claude-haiku-4-5-20251001-v1:0",
    model_provider="bedrock_converse",
)

TOOLS = [TavilySearch(), tools.save_profile, tools.check_links]


class Profile(TypedDict):
    experience: str
    career_plan: str
    preferences: str


class AgentState(MessagesState):
    profile: NotRequired[Profile]


class Agent:
    def __init__(self) -> None:
        self.system = SYSTEM
        self.model = MODEL.bind_tools(TOOLS)

        builder = StateGraph(AgentState)
        builder.add_node("llm", self.call_llm)
        builder.add_node("tools", ToolNode(TOOLS))
        builder.add_edge(START, "llm")
        builder.add_edge("tools", "llm")
        builder.add_conditional_edges("llm", self.should_run_tools)

        self.graph = builder.compile(checkpointer=InMemorySaver())

    def call_llm(self, state: AgentState):
        system = self.system
        if profile := state.get("profile"):
            system += (
                "\n\n## User profile (already saved)\n"
                f"- Experience: {profile['experience']}\n"
                f"- Career plan: {profile['career_plan']}\n"
                f"- Preferences: {profile['preferences']}"
            )
        messages = [SystemMessage(content=system)] + state["messages"]
        return {"messages": self.model.invoke(input=messages)}

    def should_run_tools(self, state: AgentState) -> Literal["tools", END]:  # type: ignore
        return "tools" if state["messages"][-1].tool_calls else END  # type: ignore

    def request(self, message: str, thread_id: str):
        response = self.graph.invoke(
            AgentState(messages=[HumanMessage(content=message)]),
            config={"configurable": {"thread_id": thread_id}},
        )
        return response["messages"][-1].content  # type: ignore
