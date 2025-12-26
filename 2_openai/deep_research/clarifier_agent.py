from pydantic import BaseModel, Field
from agents import Agent, Runner

INSTRUCTIONS = """You are a research assistant who helps clarify research queries by asking insightful questions.
Given a research query and any previously asked questions, generate the next clarifying question that will help refine and focus the research.

The question should:
1. Help understand the user's specific needs or context
2. Narrow down the scope if the query is too broad
3. Identify any specific aspects, timeframes, or perspectives the user cares about
4. Be different from previously asked questions

Make the question concise, specific, and actionable. It should be a question that, when answered, will significantly improve the quality and relevance of the research."""


class SingleQuestion(BaseModel):
    question: str = Field(description="A single clarifying question to help refine the research query")


class ClarificationQuestions(BaseModel):
    questions: list[str] = Field(
        description="Exactly 3 clarifying questions to help refine the research query",
        min_length=3,
        max_length=3
    )


# Agent for generating a single question
single_question_agent = Agent(
    name="SingleQuestionAgent",
    instructions=INSTRUCTIONS,
    model="gpt-4o-mini",
    output_type=SingleQuestion,
)

# Agent for generating all 3 questions at once (for backward compatibility)
clarifier_agent = Agent(
    name="ClarifierAgent",
    instructions="""You are a research assistant who helps clarify research queries by asking insightful questions.
Given a research query, generate exactly 3 clarifying questions that will help refine and focus the research.
These questions should:
1. Help understand the user's specific needs or context
2. Narrow down the scope if the query is too broad
3. Identify any specific aspects, timeframes, or perspectives the user cares about

Make the questions concise, specific, and actionable. They should be questions that, when answered, will significantly improve the quality and relevance of the research.""",
    model="gpt-4o-mini",
    output_type=ClarificationQuestions,
)


async def generate_question_one_by_one(query: str, previous_questions: list[str] = None) -> str:
    """Generate a single clarifying question, taking into account previous questions"""
    if previous_questions is None:
        previous_questions = []
    
    context = f"Research query: {query}"
    if previous_questions:
        context += f"\n\nPreviously asked questions:\n" + "\n".join(f"- {q}" for q in previous_questions)
        context += "\n\nGenerate a NEW question that is different from the above and helps further clarify the research."
    
    result = await Runner.run(single_question_agent, context)
    return result.final_output_as(SingleQuestion).question

