from pydantic import BaseModel, Field
from agents import Agent

HOW_MANY_SEARCHES = 5

INSTRUCTIONS = f"""You are a helpful research assistant. Given a query and clarifying information, 
come up with a set of web searches to perform to best answer the query.

When planning searches:
1. Consider the original query carefully
2. Take into account any clarifying information or answers provided
3. Create search terms that are specific and targeted based on the clarifications
4. Ensure searches cover different aspects of the refined query
5. Output {HOW_MANY_SEARCHES} search terms to query for.

The searches should be tuned to the specific needs revealed by the clarifications."""


class WebSearchItem(BaseModel):
    reason: str = Field(description="Your reasoning for why this search is important to the query, considering the clarifications.")
    query: str = Field(description="The search term to use for the web search, tuned based on clarifications.")


class WebSearchPlan(BaseModel):
    searches: list[WebSearchItem] = Field(description="A list of web searches to perform to best answer the query, tuned based on clarifications.")
    
planner_agent = Agent(
    name="PlannerAgent",
    instructions=INSTRUCTIONS,
    model="gpt-4o-mini",
    output_type=WebSearchPlan,
)