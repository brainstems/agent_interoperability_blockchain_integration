from crewai import Agent, Task, Crew

# Assuming fc_event_subscriber_tool.py and fc_performance_analyzer_tool.py 
# are in the same directory as this file.
import functools
import uuid
import logging # Added for potential logging within this script

from crewai import Agent, Task, Crew # Assuming these are used to run the main QA logic

from ..tools.fc_event_subscriber_tool import FCEventSubscriberTool, crew_step_logger_callback, _observed_events_store
from ..tools.fc_performance_analyzer_tool import FCPerformanceAnalyzerTool
from ..tools.suggestion_generator_tool import SuggestionGeneratorTool
from ..translation_crew.translation_crew import SalesToInventoryTranslationCrew

logger = logging.getLogger(__name__)
# Basic logging config if not set elsewhere
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

class TranslationQAAgentBuilder:
    def __init__(self, event_subscriber_tool=None, performance_analyzer_tool=None):
        self.event_subscriber_tool = event_subscriber_tool
        self.performance_analyzer_tool = performance_analyzer_tool

    def build_agent(self):
        if not self.event_subscriber_tool or not self.performance_analyzer_tool:
            # If not provided, instantiate them here
            self.event_subscriber_tool = self.event_subscriber_tool or FCEventSubscriberTool()
            self.performance_analyzer_tool = self.performance_analyzer_tool or FCPerformanceAnalyzerTool()
            
        return Agent(
            role='Translation Crew QA Analyst',
            goal=("Analyze the TranslationCrew's execution patterns for specific tasks. "
                  "Identify inefficiencies in its planning, task decomposition, and internal information routing. "
                  "Provide a detailed analysis of observed behaviors based on event logs."),
            backstory=("You are an expert QA Analyst specializing in multi-agent AI systems. "
                       "Your primary function is to observe the TranslationCrew, meticulously record its operational events, "
                       "and use advanced analysis techniques to understand its performance. "
                       "Your insights are crucial for the future optimization of the TranslationCrew."),
            tools=[
                self.event_subscriber_tool,
                self.performance_analyzer_tool
            ],
            allow_delegation=False,
            verbose=True,
            memory=True
        )

# Example usage (intended to be run from a separate script, e.g., a test or main orchestration script)
if __name__ == '__main__':
    import sys
    import os
    # This allows running the script directly for testing, assuming it's in the 'agents' directory
    # For imports to work correctly if this file is moved, ensure Python's path is set up.

    print("Running TranslationQAAgent example...")

    # 1. Instantiate the tools (or let the builder do it)
    event_tool = FCEventSubscriberTool()
    analyzer_tool = FCPerformanceAnalyzerTool()

    # 2. Instantiate and run the Functional Crew (SalesToInventoryTranslationCrew) with event logging
    sales_to_inventory_translator = SalesToInventoryTranslationCrew()
    functional_crew_task_desc = "Translate the following sentence: 'The quick brown fox jumps over the lazy dog.' from English to French, providing context that it is for a children's storybook."
    functional_crew_input = {
        "source_text": "The quick brown fox jumps over the lazy dog.",
        "source_language": "English",
        "target_language": "French",
        "context_notes": "For a children's storybook, keep the tone light and simple."
    }

    # The functional_crew_task_desc seems more like the 'original_message'
    # that SalesToInventoryTranslationCrew().crew() expects.
    original_message_for_fc = functional_crew_task_desc

    # Create the crew instance
    translation_crew: Crew = sales_to_inventory_translator.crew(original_message=original_message_for_fc) 

    crew_run_id = str(uuid.uuid4())
    logger.info(f"Generated crew_run_id for TranslationCrew: {crew_run_id}")

    if translation_crew and hasattr(translation_crew, 'agents') and isinstance(translation_crew.agents, list):
        for agent_in_fc in translation_crew.agents:
            if hasattr(agent_in_fc, 'role') and hasattr(agent_in_fc, 'step_callback'):
                # Bind crew_run_id, the FC's task description, and this agent's role to the callback
                agent_specific_event_collector = functools.partial(
                    crew_step_logger_callback, 
                    crew_run_id=crew_run_id, 
                    task_description=functional_crew_task_desc, # Task of the crew being observed
                    agent_role=agent_in_fc.role
                )
                agent_in_fc.step_callback = agent_specific_event_collector
                logger.info(f"Set step_callback for agent '{agent_in_fc.role}' in TranslationCrew (run ID: {crew_run_id})")
            else:
                logger.warning(f"Agent in TranslationCrew (role: {getattr(agent_in_fc, 'role', 'Unknown')}) does not support step_callback or role attribute missing.")
    else:
        logger.error("TranslationCrew or its agents list is not properly configured for setting step_callbacks.")
        # Handle error: perhaps exit or skip QA part if FC cannot be observed

    functional_crew_output = ""
    if hasattr(translation_crew, 'kickoff'):
        logger.info(f"Kicking off TranslationCrew (run ID: {crew_run_id}) with input: {functional_crew_input}")
        try:
            functional_crew_output = translation_crew.kickoff(inputs=functional_crew_input)
            logger.info(f"TranslationCrew (run ID: {crew_run_id}) execution finished. Output: {functional_crew_output}")
        except Exception as e:
            logger.error(f"Error during TranslationCrew kickoff for run {crew_run_id}: {e}", exc_info=True)
            functional_crew_output = f"Error during TranslationCrew kickoff: {e}"
    else:
        logger.error("TranslationCrew object has no kickoff method or was not initialized.")
        functional_crew_output = "Error: TranslationCrew could not be run."

    # 3. Build the QA Agent
    qa_agent_builder = TranslationQAAgentBuilder(
        event_subscriber_tool=event_tool, # event_tool was defined earlier
        performance_analyzer_tool=analyzer_tool # analyzer_tool was defined earlier
    )
    qa_agent = qa_agent_builder.build_agent()
    print(f"Translation QA Agent '{qa_agent.role}' created with tools.")

    # 4. Define a task for the QA Agent, using the actual crew_run_id and functional_crew_task_desc
    analysis_task_description = (
        f"Retrieve events for 'crew_run_id={crew_run_id}' using the FCEventSubscriberTool. "
        f"Then, analyze these events using the FCPerformanceAnalyzerTool. "
        f"The original task for the Functional Crew (TranslationCrew) being analyzed was: '{functional_crew_task_desc}'. "
        f"The output from the TranslationCrew was: '{functional_crew_output}'. "
        "Focus your analysis on the crew's planning, task decomposition, internal information routing, and overall effectiveness in achieving its goal. "
        "Provide a detailed report of your findings, highlighting any observed inefficiencies or areas for improvement."
    )
    
    qa_task = Task(
        description=analysis_task_description,
        expected_output=("A textual analysis report based on the TranslationCrew's execution events and output. The report should detail "
                         "observations on planning effectiveness, efficiency of task decomposition, clarity of information flow, "
                         "tool usage patterns, accuracy of the final output, and any identified bottlenecks or areas for future optimization."),
        agent=qa_agent
    )

    # 5. Create a Crew for the QA Agent and kick it off
    qa_crew = Crew(
        agents=[qa_agent],
        tasks=[qa_task],
        verbose=2 # Set to 1 or 0 for less output if preferred
    )

    print(f"\nKicking off QA Crew for TranslationCrew run_id: {crew_run_id}...")
    result = qa_crew.kickoff()

    print("\n###################### QA CREW RESULT ######################")
    print(result)
    print("############################################################")

    # Clean up events for the specific run_id if necessary (optional, as _observed_events_store is in-memory)
    # If you want to clear it for a specific run:
    if crew_run_id in _observed_events_store:
        del _observed_events_store[crew_run_id]
        logger.info(f"Cleared events from _observed_events_store for run_id: {crew_run_id}")
