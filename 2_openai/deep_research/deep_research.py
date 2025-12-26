import gradio as gr
from dotenv import load_dotenv
from research_manager import ResearchManager
from clarifier_agent import generate_question_one_by_one
import asyncio

load_dotenv(override=True)


def execute_research(query: str, state: dict):
    """Start the research flow - generate first question"""
    if not query or not query.strip():
        return (
            "Please enter a research query first.",
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(value=""),
            {"query": "", "current_question": 0, "questions": [], "answers": []}
        )
    
    # Initialize state
    state["query"] = query
    state["current_question"] = 1
    state["questions"] = []
    state["answers"] = []
    
    # Generate first question
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    question1 = loop.run_until_complete(generate_question_one_by_one(query, []))
    loop.close()
    
    state["questions"].append(question1)
    
    question_display = f"## Question 1:\n\n{question1}\n\n*Please provide your answer below.*"
    
    return (
        question_display,
        gr.update(visible=True),
        gr.update(visible=True),
        gr.update(value="", placeholder="Enter your answer here..."),
        state
    )


def submit_answer(answer: str, state: dict):
    """Handle answer submission and generate next question or start research"""
    if not answer or not answer.strip():
        return (
            state.get("current_question_display", ""),
            gr.update(visible=True),
            gr.update(visible=True),
            gr.update(value=""),
            state
        )
    
    # Store the answer
    current_q_num = state.get("current_question", 0)
    state["answers"].append(answer.strip())
    
    # If we have 3 answers, start research
    if len(state["answers"]) >= 3:
        # Hide question UI, show research report
        return (
            "## All questions answered! Starting research...\n\n*This may take a few moments.*",
            gr.update(visible=False),
            gr.update(visible=False),
            gr.update(value="", visible=False),
            state
        )
    
    # Generate next question
    next_q_num = current_q_num + 1
    state["current_question"] = next_q_num
    
    query = state["query"]
    previous_questions = state["questions"]
    
    # Generate next question
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    next_question = loop.run_until_complete(
        generate_question_one_by_one(query, previous_questions)
    )
    loop.close()
    
    state["questions"].append(next_question)
    state["current_question_display"] = f"## Question {next_q_num}:\n\n{next_question}\n\n*Please provide your answer below.*"
    
    return (
        state["current_question_display"],
        gr.update(visible=True),
        gr.update(visible=True),
        gr.update(value="", placeholder="Enter your answer here..."),
        state
    )


async def run_research_with_state(state: dict):
    """Run the actual research after all questions are answered"""
    query = state.get("query", "")
    answers = state.get("answers", [])
    
    if not query or len(answers) < 3:
        yield "Error: Missing query or answers. Please start over."
        return
    
    # Format clarifications from answers
    clarifications_parts = []
    for i, answer in enumerate(answers, 1):
        clarifications_parts.append(f"Answer to Question {i}: {answer}")
    
    clarifications = "\n\n".join(clarifications_parts)
    
    # Format question_answers dict
    question_answers = {str(i+1): answer for i, answer in enumerate(answers)}
    
    # Run the research
    manager = ResearchManager()
    async for chunk in manager.run(query, clarifications=clarifications, question_answers=question_answers):
        yield chunk


def start_research(state: dict):
    """Trigger research execution after all answers are collected"""
    if len(state.get("answers", [])) < 3:
        return state
    
    # This will be handled by the async generator
    return state


with gr.Blocks(theme=gr.themes.Default(primary_hue="sky")) as ui:
    gr.Markdown("# Deep Research")
    gr.Markdown("Enter your research query and click 'Execute Research' to begin. You'll be asked 3 clarifying questions one by one.")
    
    # State to track progress
    state = gr.State(value={"query": "", "current_question": 0, "questions": [], "answers": []})
    
    with gr.Row():
        with gr.Column(scale=2):
            query_textbox = gr.Textbox(
                label="What topic would you like to research?",
                placeholder="e.g., 'What are the latest trends in AI safety?'",
                lines=2
            )
            execute_btn = gr.Button("Execute Research", variant="primary")
        
        with gr.Column(scale=3):
            question_display = gr.Markdown(
                label="Clarifying Questions",
                value="Enter your research query and click 'Execute Research' to begin."
            )
    
    # Answer input section (initially hidden)
    with gr.Row(visible=False) as answer_section:
        with gr.Column():
            answer_input = gr.Textbox(
                label="Your Answer",
                placeholder="Enter your answer here...",
                lines=3
            )
            submit_answer_btn = gr.Button("Submit Answer", variant="primary")
    
    # Research report section
    report = gr.Markdown(label="Research Report", visible=False)
    
    # Event handlers
    def handle_execute(query, current_state):
        """Handle execute research button"""
        result = execute_research(query, current_state)
        # Show answer section if we have a question
        if result[1].get("visible", False):
            return [
                result[0],  # question_display
                gr.update(visible=True),  # answer_section
                result[2],  # submit_answer_btn
                result[3],  # answer_input
                result[4],  # state
                gr.update(visible=False)  # report (hide initially)
            ]
        return [
            result[0],  # question_display
            gr.update(visible=False),  # answer_section
            gr.update(visible=False),  # submit_answer_btn
            result[3],  # answer_input
            result[4],  # state
            gr.update(visible=False)  # report
        ]
    
    def handle_submit(answer, current_state):
        """Handle answer submission"""
        if not answer or not answer.strip():
            return [
                current_state.get("current_question_display", ""),
                gr.update(visible=True),
                gr.update(visible=True),
                gr.update(value=""),
                current_state,
                gr.update(visible=True)  # Keep report visible if it was already showing
            ]
        
        result = submit_answer(answer, current_state)
        new_state = result[4]
        
        # If all 3 answers collected, hide answer section and show report area
        if len(new_state.get("answers", [])) >= 3:
            return [
                "## All 3 questions answered!\n\nStarting research... This may take a few moments.\n",  # question_display
                gr.update(visible=False),  # answer_section
                gr.update(visible=False),  # submit_answer_btn
                gr.update(value="", visible=False),  # answer_input
                new_state,  # state
                gr.update(visible=True)  # report (show)
            ]
        
        return [
            result[0],  # question_display
            result[1],  # answer_section
            result[2],  # submit_answer_btn
            result[3],  # answer_input
            new_state,  # state
            gr.update(visible=False)  # report (hide until all answers collected)
        ]
    
    # Wire up events
    async def trigger_research(current_state):
        """Trigger research after all answers are collected"""
        if len(current_state.get("answers", [])) >= 3:
            async for chunk in run_research_with_state(current_state):
                yield chunk
    
    execute_btn.click(
        fn=handle_execute,
        inputs=[query_textbox, state],
        outputs=[question_display, answer_section, submit_answer_btn, answer_input, state, report]
    )
    
    query_textbox.submit(
        fn=handle_execute,
        inputs=[query_textbox, state],
        outputs=[question_display, answer_section, submit_answer_btn, answer_input, state, report]
    )
    
    # Handle answer submission
    submit_click = submit_answer_btn.click(
        fn=handle_submit,
        inputs=[answer_input, state],
        outputs=[question_display, answer_section, submit_answer_btn, answer_input, state, report]
    )
    
    # After submit, check if research should start
    submit_click.then(
        fn=trigger_research,
        inputs=[state],
        outputs=[report]
    )
    
    answer_submit = answer_input.submit(
        fn=handle_submit,
        inputs=[answer_input, state],
        outputs=[question_display, answer_section, submit_answer_btn, answer_input, state, report]
    )
    
    answer_submit.then(
        fn=trigger_research,
        inputs=[state],
        outputs=[report]
    )

ui.launch(inbrowser=True)

