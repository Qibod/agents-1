from agents import Agent, Runner, trace, gen_trace_id
from search_agent import search_agent
from planner_agent import planner_agent, WebSearchItem, WebSearchPlan
from writer_agent import writer_agent, ReportData
from email_agent import email_agent
from clarifier_agent import clarifier_agent, ClarificationQuestions, generate_question_one_by_one
import asyncio

# Convert agents to tools for the manager agent
clarifier_tool = clarifier_agent.as_tool(
    tool_name="generate_clarifying_questions",
    tool_description="Generate 3 clarifying questions based on a research query to help refine and focus the research."
)

planner_tool = planner_agent.as_tool(
    tool_name="plan_searches",
    tool_description="Plan web searches based on a research query and clarifying information. Takes the original query and clarifications, returns a search plan."
)

search_tool = search_agent.as_tool(
    tool_name="perform_search",
    tool_description="Perform a web search with a specific search term, tuned based on clarifying context. Takes search term, reason, and clarifications."
)

writer_tool = writer_agent.as_tool(
    tool_name="write_report",
    tool_description="Write a comprehensive research report based on the original query, clarifications, and search results. Takes query, clarifications, and search results."
)

# Email agent as handoff
email_agent.handoff_description = "Format and send the research report as an HTML email"

MANAGER_INSTRUCTIONS = """You are a Research Manager coordinating a team of specialized research agents.

Your workflow:
1. **Clarify the Query**: First, use the clarifier_agent to generate 3 clarifying questions about the research query.
   - Present these questions to understand the user's specific needs
   - Wait for or infer answers to these questions

2. **Plan Searches**: Use the plan_searches tool with:
   - The original query
   - The clarifying information/answers
   This will generate a search plan tuned to the clarifications.

3. **Perform Searches**: For each search in the plan, use the perform_search tool with:
   - The search term
   - The reason for the search
   - The clarifying context
   Collect all search results.

4. **Write Report**: Use the write_report tool with:
   - The original query
   - The clarifications
   - All collected search results
   This generates the final research report.

5. **Send Email**: Hand off the report to the Email Manager agent, which will format and send it.

Important:
- Always use the clarifier first to refine the query
- Use clarifications to tune all subsequent steps
- Coordinate the workflow from clarification through email delivery
- Only hand off the final report to the Email Manager (one handoff only)
"""

research_manager_agent = Agent(
    name="Research Manager",
    instructions=MANAGER_INSTRUCTIONS,
    tools=[clarifier_tool, planner_tool, search_tool, writer_tool],
    handoffs=[email_agent],
    model="gpt-4o-mini",
)

# Keep the class for backward compatibility with existing code
class ResearchManager:

    async def generate_questions(self, query: str):
        """
        Phase 1: Generate clarifying questions one by one.
        Returns the questions for display to the user.
        """
        trace_id = gen_trace_id()
        output = []
        questions = []
        previous_questions = []
        
        with trace("Question Generation", trace_id=trace_id):
            output.append(f"View trace: https://platform.openai.com/traces/trace?trace_id={trace_id}\n")
            output.append("\n## Generating Clarifying Questions\n\n")
            output.append("I'll ask you 3 questions to better understand your research needs.\n\n")
            yield "\n".join(output)
            
            # Generate questions one by one
            for i in range(1, 4):
                output.append(f"**Generating question {i}...**\n\n")
                yield "\n".join(output)
                
                question = await generate_question_one_by_one(query, previous_questions)
                questions.append(question)
                previous_questions.append(question)
                
                output.append(f"### Question {i}:\n\n{question}\n\n")
                yield "\n".join(output)
            
            output.append("\n---\n\n**Please provide your answers above, then click 'Run Research with Answers'.**\n")
            yield "\n".join(output)

    async def run(self, query: str, clarifications: str = None, question_answers: dict = None):
        """
        Run the deep research process with clarifying questions.
        
        Args:
            query: The research query
            clarifications: Optional clarifying information/answers. If None, will generate questions.
            question_answers: Optional dict mapping question numbers to answers (for interactive mode)
        """
        trace_id = gen_trace_id()
        output = []  # Accumulate output for Gradio
        
        with trace("Research trace", trace_id=trace_id):
            trace_link = f"View trace: https://platform.openai.com/traces/trace?trace_id={trace_id}"
            print(trace_link)
            output.append(trace_link)
            yield "\n".join(output)
            
            # Process user answers to create clarifications
            collected_answers = []
            if question_answers:
                # Use provided answers - format them clearly
                for i in range(1, 4):
                    answer = question_answers.get(str(i), question_answers.get(i, ""))
                    if answer and answer.strip():
                        collected_answers.append(f"Answer {i}: {answer.strip()}")
            elif clarifications and clarifications.strip():
                # Use provided clarifications as answers
                collected_answers.append(clarifications)
            
            # Format clarifications for use in research
            if collected_answers:
                clarifications_text = "\n\n".join(collected_answers)
                output.append(f"\n**Using your answers to tune the research:**\n\n{clarifications_text}\n\n")
            else:
                # No answers provided - proceed without specific clarifications
                output.append("\n⚠️ *No answers provided. Proceeding with general research.*\n\n")
                clarifications_text = None
            
            output.append("---\n\n")
            yield "\n".join(output)
            
            # Step 2: Plan searches with clarifications
            print("Planning searches with clarifications...")
            output.append("\n## Planning searches based on your answers...\n")
            yield "\n".join(output)
            
            search_plan = await self.plan_searches(query, clarifications_text if clarifications_text else "")
            output.append(f"\n✓ Searches planned ({len(search_plan.searches)} searches), starting to search...\n")
            yield "\n".join(output)
            
            # Step 3: Perform searches with clarifications
            search_results = await self.perform_searches(search_plan, clarifications_text if clarifications_text else "")
            output.append(f"\n✓ Searches complete ({len(search_results)} results), writing report...\n")
            yield "\n".join(output)
            
            # Step 4: Write report with clarifications
            report = await self.write_report(query, clarifications_text if clarifications_text else "", search_results)
            output.append("\n✓ Report written, sending email...\n")
            yield "\n".join(output)
            
            # Step 5: Send email
            email_result = await self.send_email(report)
            if email_result.get("success", False):
                output.append("\n✓ Email sent successfully!\n")
            else:
                output.append(f"\n⚠️ Email sending issue: {email_result.get('error', 'Unknown error')}\n")
            output.append("\n---\n\n")
            yield "\n".join(output)
            
            # Add the final report
            output.append("## Research Report\n\n")
            output.append(report.markdown_report)
            yield "\n".join(output)

    async def plan_searches(self, query: str, clarifications: str = "") -> WebSearchPlan:
        """ Plan the searches to perform for the query, taking clarifications into account """
        print("Planning searches with clarifications...")
        if clarifications:
            input_text = f"""Original query: {query}

User's answers to clarifying questions:
{clarifications}

Plan web searches that are tuned to address both the original query and the user's specific answers."""
        else:
            input_text = f"""Original query: {query}

Plan web searches to answer this query."""
        
        result = await Runner.run(
            planner_agent,
            input_text,
        )
        print(f"Will perform {len(result.final_output.searches)} searches")
        return result.final_output_as(WebSearchPlan)

    async def perform_searches(self, search_plan: WebSearchPlan, clarifications: str = "") -> list[str]:
        """ Perform the searches, taking clarifications into account """
        print("Searching with clarifications...")
        num_completed = 0
        tasks = [asyncio.create_task(self.search(item, clarifications)) for item in search_plan.searches]
        results = []
        for task in asyncio.as_completed(tasks):
            result = await task
            if result is not None:
                results.append(result)
            num_completed += 1
            print(f"Searching... {num_completed}/{len(tasks)} completed")
        print("Finished searching")
        return results

    async def search(self, item: WebSearchItem, clarifications: str = "") -> str | None:
        """ Perform a search for the query, tuned with clarifications """
        if clarifications:
            input_text = f"""Search term: {item.query}
Reason for searching: {item.reason}

User's answers to clarifying questions (use these to focus the search):
{clarifications}

Perform the search and summarize results, prioritizing information relevant to the user's specific answers."""
        else:
            input_text = f"""Search term: {item.query}
Reason for searching: {item.reason}

Perform the search and summarize the results."""
        
        try:
            result = await Runner.run(
                search_agent,
                input_text,
            )
            return str(result.final_output)
        except Exception as e:
            print(f"Search error: {e}")
            return None

    async def write_report(self, query: str, clarifications: str = "", search_results: list[str] = None) -> ReportData:
        """ Write the report for the query, incorporating clarifications """
        if search_results is None:
            search_results = []
        print("Writing report with clarifications...")
        if clarifications:
            input_text = f"""Original query: {query}

User's answers to clarifying questions that refined the research:
{clarifications}

Summarized search results:
{search_results}

Write a comprehensive report that addresses the original query while incorporating insights from the user's specific answers."""
        else:
            input_text = f"""Original query: {query}

Summarized search results:
{search_results}

Write a comprehensive report that addresses the query."""
        
        result = await Runner.run(
            writer_agent,
            input_text,
        )

        print("Finished writing report")
        return result.final_output_as(ReportData)
    
    async def send_email(self, report: ReportData) -> dict:
        """Send email and return result with success/error status"""
        print("Sending email...")
        try:
            result = await Runner.run(
                email_agent,
                report.markdown_report,
            )
            print("Email sent successfully")
            return {"success": True, "result": result}
        except Exception as e:
            error_msg = str(e)
            print(f"Email sending failed: {error_msg}")
            
            # Provide helpful diagnostics for common errors
            if "403" in error_msg or "Forbidden" in error_msg:
                diagnostic = (
                    "\n**SendGrid 403 Forbidden Error**\n\n"
                    "This usually means:\n"
                    "1. Your API key doesn't have 'Mail Send' permissions\n"
                    "2. The sender email (vr.work.ams@gmail.com) is not verified in SendGrid\n"
                    "3. Your SendGrid account has restrictions\n\n"
                    "**To fix:**\n"
                    "- Go to SendGrid Dashboard → Settings → API Keys\n"
                    "- Ensure your API key has 'Mail Send' permission\n"
                    "- Verify your sender email in SendGrid Dashboard → Settings → Sender Authentication\n"
                )
                return {"success": False, "error": error_msg, "diagnostic": diagnostic}
            else:
                return {"success": False, "error": error_msg}