import unittest
from unittest.mock import patch, MagicMock, AsyncMock # Add AsyncMock
import os

from agents.infrastructure_crew.translation_crew.translation_crew import SalesToInventoryTranslationCrew, SalesToPromotionalTranslationCrew, Process
from langchain_core.messages import AIMessage, AIMessageChunk # For mocking LLM response
from langchain_core.outputs import LLMResult, Generation # For mocking generate_prompt returns
# We will need to mock crewai classes Agent, Task, Crew for some unit tests
# from langchain_anthropic import ChatAnthropic # No longer needed for __class__

class TestSalesToInventoryTranslationCrew(unittest.TestCase):

    @patch.dict(os.environ, {}, clear=True)
    def test_init_default_llm_model(self):
        """Test __init__ uses default LLM model when env var is not set."""
        crew_instance = SalesToInventoryTranslationCrew()
        self.assertEqual(crew_instance.llm_model, 'claude-3-5-sonnet-20241022')

    @patch.dict(os.environ, {'LLM_MODEL': 'test-claude-model'})
    def test_init_uses_env_var_llm_model(self):
        """Test __init__ uses LLM_MODEL environment variable when set."""
        crew_instance = SalesToInventoryTranslationCrew()
        self.assertEqual(crew_instance.llm_model, 'test-claude-model')

    @patch('agents.infrastructure_crew.translation_crew.translation_crew.ChatAnthropic')
    @patch('agents.infrastructure_crew.translation_crew.translation_crew.Agent')
    def test_create_translation_agent(self, MockAgent, MockChatAnthropic):
        """Test create_translation_agent instantiates Agent correctly."""
        mock_llm_instance = MockChatAnthropic.return_value
        mock_agent_instance = MockAgent.return_value

        crew_instance = SalesToInventoryTranslationCrew()
        # Override llm_model for consistent testing if needed, or rely on default
        # crew_instance.llm_model = 'test-model-for-agent'

        agent = crew_instance.create_translation_agent()

        MockChatAnthropic.assert_called_once_with(
            model=crew_instance.llm_model,
            temperature=0.2
        )
        MockAgent.assert_called_once_with(
            role='Promotional Products Strategy Expert',
            goal="""Optimize promotional timing and inventory management to achieve 3% growth while maintaining optimal stock levels.
                   Focus on preventing stockouts and aligning marketing spend with inventory positions.""",
            backstory="""Seasoned professional with 6 years of experience bridging inventory and marketing domains. 
                        Demonstrated success in promotional timing and preventing stockouts, with a proven track record 
                        of maintaining optimal stock levels during promotions. Recently achieved significant improvements 
                        in inventory management with 0% stockouts in Q2 2024 and consistent optimization of ad spend.""",
            verbose=True,
            llm=mock_llm_instance
        )
        self.assertIs(agent, mock_agent_instance)

    @patch('agents.infrastructure_crew.translation_crew.translation_crew.Task')
    def test_create_translation_task(self, MockTask):
        """Test create_translation_task instantiates Task correctly."""
        mock_task_instance = MockTask.return_value
        mock_agent = MagicMock() # Mock the agent passed to the task
        original_message = "Test sales message about new promotion for SKU123"

        crew_instance = SalesToInventoryTranslationCrew()
        task = crew_instance.create_translation_task(agent=mock_agent, original_message=original_message)

        expected_description = f"""
            Source Domain: sales and promotional planning
            Target Domain: inventory management

            Original Message:
            {original_message}

            Requirements:
            1. Transform this message with focus on inventory implications of promotional activities
            2. Consider recent performance metrics:
               - Current inventory churn rate: 2.1
               - Stock level optimization: 0% out of stock
               - Ad spend efficiency: -3% vs target
            3. Ensure alignment between promotional calendar and inventory positions
            4. Include specific inventory requirements for projected 3% growth target
            5. Highlight any potential stockout risks based on promotional plans

            Transform this message into a JSON format with the following structure:
            {{
                "timestamp": <ISO format timestamp>,
                "sku_status": {{
                    "<sku_id>": {{
                        "current_stock": <int>,
                        "reorder_point": <int>,
                        "safety_stock": <int>,
                        "lead_time_days": <int>,
                        "daily_velocity": <float>,
                        "promo_multiplier": <float>,
                        "stock_coverage_days": <float>,
                        "alerts": [<alert_enum_value>, "..."]
                    }}
                }},
                "promotional_impact": {{
                    "impacted_skus": ["<sku_id>", "..."],
                    "risk_assessment": [<text_description>, "..."],
                    "required_actions": [<text_description>, "..."]
                }},
                "supply_chain_status": {{
                    "open_orders": [<order_details>, "..."],
                    "lead_time_updates": [<update_details>, "..."],
                    "fulfillment_risks": [<text_description>, "..."],
                    "coordination_actions": [<text_description>, "..."]
                }},
                "recommendations": [<text_recommendation>, "..."]
            }}

            Ensure all numerical values are appropriate for inventory context and alerts match the InventoryAlert enum options.
            """
        
        MockTask.assert_called_once_with(
            description=expected_description,
            agent=mock_agent,
            expected_output='JSON formatted inventory status and recommendations',
        )
        self.assertIs(task, mock_task_instance)

    @patch('agents.infrastructure_crew.translation_crew.translation_crew.Crew')
    @patch.object(SalesToInventoryTranslationCrew, 'create_translation_task')
    @patch.object(SalesToInventoryTranslationCrew, 'create_translation_agent')
    def test_crew_method_assembles_crew_correctly(self, mock_create_agent, mock_create_task, MockCrew):
        """Test the crew method correctly assembles and returns a Crew."""
        mock_agent_instance = MagicMock()
        mock_task_instance = MagicMock()
        mock_crew_instance = MockCrew.return_value

        mock_create_agent.return_value = mock_agent_instance
        mock_create_task.return_value = mock_task_instance

        crew_instance = SalesToInventoryTranslationCrew()
        original_message = "Sample message for crew assembly"
        
        created_crew = crew_instance.crew(original_message)

        mock_create_agent.assert_called_once_with() # self is implicit for instance method mocks
        mock_create_task.assert_called_once_with(mock_agent_instance, original_message) # self is implicit
        
        MockCrew.assert_called_once_with(
            agents=[mock_agent_instance],
            tasks=[mock_task_instance],
            process=Process.sequential,
            verbose=True,
            full_output=True,
            # output_log_file="./translation_crew_sales_to_inventory.out" # This is commented out in source
        )
        self.assertIs(created_crew, mock_crew_instance)

    @patch('agents.infrastructure_crew.translation_crew.translation_crew.ChatAnthropic', autospec=True)
    def test_crew_kickoff_produces_expected_output_with_mocked_llm(self, MockChatAnthropic):
        """Test crew.kickoff() integrates agent and task to produce LLM output."""
        # 1. Configure the mock LLM instance and its response
        # MockChatAnthropic is now an autospecced mock of the class.
        # MockChatAnthropic.return_value is an autospecced mock of an instance.
        mock_llm_instance = MockChatAnthropic.return_value 

        expected_json_output = "{ \"key\": \"value\" }" # Simpler JSON string for diagnostics

        # Configure the invoke method (the one most likely to be called)
        mock_llm_instance.invoke.return_value = AIMessage(content=expected_json_output)

        # Configure other abstract methods for Pydantic validation
        # autospec=True ensures these methods exist as mocks; we set their return_value.
        mock_llm_instance.predict.return_value = "dummy_prediction_string"
        mock_llm_instance.predict_messages.return_value = AIMessage(content="dummy_predict_messages")
        mock_llm_instance.generate_prompt.return_value = LLMResult(generations=[])

        # For async methods, autospec on an async method should yield an AsyncMock.
        # We then configure its return_value.
        mock_llm_instance.apredict.return_value = "dummy_async_prediction_string"
        mock_llm_instance.apredict_messages.return_value = AIMessage(content="dummy_async_predict_messages")
        mock_llm_instance.agenerate_prompt.return_value = LLMResult(generations=[])

        # Async helper functions for side_effect
        async def async_dummy_str_return(*args, **kwargs):
            return "dummy_async_prediction_string"
        async def async_dummy_msg_return(*args, **kwargs):
            return AIMessage(content="dummy_async_predict_messages")
        async def async_dummy_llmresult_return(*args, **kwargs):
          mock_llm_instance.invoke = MagicMock(return_value=AIMessage(content=expected_json_output))
        mock_llm_instance.predict = MagicMock(return_value=expected_json_output) # Returns raw string
        mock_llm_instance.predict_messages = MagicMock(return_value=AIMessage(content=expected_json_output))
        # For generate_prompt, which might be called by some agent types
        mock_llm_instance.generate_prompt = MagicMock(return_value=LLMResult(generations=[[Generation(text=expected_json_output)]]))

        # Async versions
        async def async_dummy_msg_return(*args, **kwargs):
            return AIMessage(content=expected_json_output)
        
        async def async_dummy_str_return(*args, **kwargs):
            return expected_json_output # Returns raw string

        async def async_dummy_llmresult_return(*args, **kwargs):
            return LLMResult(generations=[[Generation(text=expected_json_output)]])

        mock_llm_instance.ainvoke.side_effect = async_dummy_msg_return
        mock_llm_instance.apredict.side_effect = async_dummy_str_return # Returns raw string
        mock_llm_instance.apredict_messages.side_effect = async_dummy_msg_return
        mock_llm_instance.agenerate_prompt.side_effect = async_dummy_llmresult_return

        # Mock the stream method: an async generator yielding the raw string output
        async def async_generator_for_stream_raw_string():
            yield expected_json_output # Yield the raw string directly
        
        # mock_llm_instance.stream is an AsyncMock due to autospec=True.
        # Configure its return_value to be our specific async generator.
        mock_llm_instance.stream.return_value = async_generator_for_stream_raw_string()

        # 2. Setup and get the crew
        crew_creator = SalesToInventoryTranslationCrew()
        original_message = "Emergency promo for SKU_XYZ, stock levels critical!"
        # This will create a crew with an agent that uses the mocked ChatAnthropic
        actual_crew = crew_creator.crew(original_message)

        # 3. Kickoff the crew
        # With full_output=True (default for this crew), kickoff returns a dict.
        # The actual output of the task is stored in task.output.raw_output.
        kickoff_result = actual_crew.kickoff()

        # 4. Assertions
        # Check that the task's raw output matches the mocked LLM's content
        self.assertIsNotNone(actual_crew.tasks, "Crew should have tasks.")
        self.assertTrue(len(actual_crew.tasks) > 0, "Crew should have at least one task.")
        task_output = actual_crew.tasks[0].output
        self.assertIsNotNone(task_output, "Task output should not be None after kickoff.")
        self.assertEqual(task_output.raw_output, expected_json_output)
        
        # Verify the LLM's invoke method was called (once by the agent)
        mock_llm_instance.invoke.assert_called_once()

        # Optional: Verify the kickoff_result if its structure is known and relevant.
        # For a single task crew with full_output=True, the kickoff_result is often
        # the direct output of the task, or a dict containing it.
        # If the crew's `kickoff` directly returns the task's string output:
        if isinstance(kickoff_result, str):
             self.assertEqual(kickoff_result, expected_json_output)
        elif isinstance(kickoff_result, dict):
            # If it's a dict, you might need to inspect its structure to find the relevant output.
            # For example, it might be kickoff_result.get('final_answer') or similar.
            # This part depends on the specifics of crewai's full_output=True structure.
            # For now, we primarily rely on task.output.raw_output which is more direct.
            pass # Add more specific assertions if kickoff_result structure is critical

if __name__ == '__main__':
    unittest.main()
