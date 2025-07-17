import asyncio
import logging
import uuid
from datetime import datetime, timezone

from agents.infrastructure_crew.infrastructure_agents.registry_manager_agent import RegistryManagerAgent
from agents.infrastructure_crew.schemas.learning_schemas import SharableLearning

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration for RegistryManagerAgent (adjust if your Redis is elsewhere)
REDIS_URL = "redis://localhost:6379/0"
REGISTRY_AGENT_ID = "test_registry_manager_for_learnings"

async def main():
    logger.info("Starting Sharable Learnings Test Script...")

    config = {
        "agent_id": REGISTRY_AGENT_ID,
        "redis_url": REDIS_URL
    }
    registry_manager = RegistryManagerAgent(config=config)
    # Ensure Redis client is available (it's initialized in RegistryManagerAgent's __init__)
    if not hasattr(registry_manager, 'redis') or registry_manager.redis is None:
        logger.error("Redis client not initialized in RegistryManagerAgent. Exiting.")
        return

    logger.info(f"RegistryManagerAgent initialized. Using Redis at {REDIS_URL}")

    # 1. Simulate FL Server publishing a Federated Model Update
    logger.info("\n--- Test 1: Publishing Federated Model Update ---")
    fl_model_learning = SharableLearning(
        source_entity_id="fl_server_qa_model_v1",
        learning_type="federated_model_update",
        content={
            "model_name": "QAModel_Federated",
            "model_version": "1.5.0",
            "parameters_reference": "file:///models/federated/qa_model_v1.5.0.npz",
            "aggregation_details": {"clients_participated": 10, "rounds": 5},
            "server_evaluation_metrics": {"accuracy": 0.85, "loss": 0.23}
        },
        task_description="Aggregated global model for Question Answering tasks after 5 rounds of federation.",
        keywords=["federated_learning", "qa_model", "global_model", "nlp"],
        performance_metric="accuracy:0.85"
    )
    publish_success = await registry_manager.publish_learning(fl_model_learning)
    logger.info(f"FL Model Learning published: {publish_success}, ID: {fl_model_learning.learning_id}")
    assert publish_success

    # 2. Simulate Agent querying for this Federated Model Update
    logger.info("\n--- Test 2: Querying for Federated Model Update ---")
    queried_models = await registry_manager.query_learnings(
        learning_type="federated_model_update",
        keywords=["qa_model"]
    )
    logger.info(f"Found {len(queried_models)} federated model learning(s):")
    for q_model in queried_models:
        logger.info(f"  - ID: {q_model.learning_id}, Source: {q_model.source_entity_id}, Model: {q_model.content.get('model_name')}")
    assert len(queried_models) > 0

    # 3. Simulate publishing a different type of learning (Prompt Template)
    logger.info("\n--- Test 3: Publishing a Prompt Template Learning ---")
    prompt_learning_id = f"learn_prompt_{uuid.uuid4()}"
    prompt_learning = SharableLearning(
        learning_id=prompt_learning_id, # Explicitly set for later retrieval
        source_entity_id="agent_creative_writer_v3",
        learning_type="prompt_template",
        content={
            "template": "Generate a short story about a {character} who discovers a {magical_object}.",
            "input_variables": ["character", "magical_object"],
            "notes": "Effective for generating fantasy micro-fiction."
        },
        task_description="Prompt template for creative story generation.",
        keywords=["prompt", "creative_writing", "story_generation", "fantasy"],
        performance_metric="user_engagement_increase:0.12"
    )
    publish_success_prompt = await registry_manager.publish_learning(prompt_learning)
    logger.info(f"Prompt Template Learning published: {publish_success_prompt}, ID: {prompt_learning.learning_id}")
    assert publish_success_prompt

    # 4. Query by various criteria
    logger.info("\n--- Test 4: Advanced Queries ---")
    # Query by learning type "prompt_template"
    prompt_templates = await registry_manager.query_learnings(learning_type="prompt_template")
    logger.info(f"Found {len(prompt_templates)} prompt templates:")
    for pt in prompt_templates:
        logger.info(f"  - ID: {pt.learning_id}, Source: {pt.source_entity_id}")
    assert any(pt.learning_id == prompt_learning_id for pt in prompt_templates)

    # Query by keyword "fantasy"
    fantasy_learnings = await registry_manager.query_learnings(keywords=["fantasy"])
    logger.info(f"Found {len(fantasy_learnings)} 'fantasy' learnings:")
    assert any(fl.learning_id == prompt_learning_id for fl in fantasy_learnings)

    # Query by source_entity_id
    creative_writer_learnings = await registry_manager.query_learnings(source_entity_id="agent_creative_writer_v3")
    logger.info(f"Found {len(creative_writer_learnings)} learnings from 'agent_creative_writer_v3':")
    assert any(cwl.learning_id == prompt_learning_id for cwl in creative_writer_learnings)

    # 5. Get a specific learning by its ID
    logger.info("\n--- Test 5: Get Learning by ID ---")
    retrieved_prompt = await registry_manager.get_learning_by_id(prompt_learning_id)
    if retrieved_prompt:
        logger.info(f"Retrieved prompt by ID '{prompt_learning_id}': Type - {retrieved_prompt.learning_type}")
        assert retrieved_prompt.task_description == prompt_learning.task_description
    else:
        logger.error(f"Failed to retrieve prompt by ID '{prompt_learning_id}'")
        assert False, "Failed to retrieve learning by ID"

    # 6. Delete a learning
    logger.info("\n--- Test 6: Delete Learning ---")
    delete_success = await registry_manager.delete_learning(prompt_learning_id)
    logger.info(f"Deletion of learning '{prompt_learning_id}' successful: {delete_success}")
    assert delete_success

    # Verify deletion
    deleted_prompt_check = await registry_manager.get_learning_by_id(prompt_learning_id)
    if deleted_prompt_check is None:
        logger.info(f"Learning '{prompt_learning_id}' successfully verified as deleted.")
    else:
        logger.error(f"Learning '{prompt_learning_id}' still found after deletion attempt.")
        assert False, "Learning not deleted successfully"
        
    # Clean up the first learning item too
    await registry_manager.delete_learning(fl_model_learning.learning_id)
    logger.info(f"Cleaned up FL model learning: {fl_model_learning.learning_id}")

    logger.info("\nSharable Learnings Test Script completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
