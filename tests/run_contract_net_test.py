import asyncio
import logging
import uuid
from typing import List

from agents.infrastructure_crew.infrastructure_agents.task_orchestration_agent import TaskOrchestrationAgent
from agents.infrastructure_crew.infrastructure_agents.basic_worker_agent import BasicWorkerAgent # Ensure this path is correct
from agents.infrastructure_crew.schemas.task_schemas import TaskSubmissionRequest, TaskStatus

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    # Initialize Agents
    orchestrator = TaskOrchestrationAgent(agent_id="orchestrator-main")
    
    num_workers = 3
    workers: List[BasicWorkerAgent] = []
    for i in range(num_workers):
        worker = BasicWorkerAgent(agent_id=f"worker-test-{i}")
        workers.append(worker)

    # Start Agents
    await orchestrator.start()
    for worker in workers:
        await worker.start()

    # Give agents a moment to initialize fully, especially Redis pub/sub
    await asyncio.sleep(2)

    # Submit a task that requires bidding
    task_submission = TaskSubmissionRequest(
        task_name="Complex Data Analysis Task",
        task_description="Perform complex analysis on a large dataset and generate a report. Requires significant computational resources.",
        priority=1,
        requires_bidding=True,
        data={"dataset_url": "s3://my-data-bucket/large_dataset.csv", "parameters": {"alpha": 0.05}},
        # deadline_seconds can be set if needed, orchestrator has a default
        # For testing, let's give it a reasonable deadline for the whole process
        deadline_seconds=120 # 2 minutes for CFP, bidding, execution, result
    )

    submitted_task_def = None
    try:
        logger.info("Submitting task to orchestrator...")
        submitted_task_def = await orchestrator.submit_task(task_submission)
        if submitted_task_def:
            logger.info(f"Task {submitted_task_def.task_id} submitted. Initial status: {submitted_task_def.status}")
            task_id_to_monitor = submitted_task_def.task_id

            # Wait for the task to complete or fail
            # Monitor task status for a while
            max_wait_time_seconds = submitted_task_def.deadline_seconds + 30 # Add some buffer
            poll_interval_seconds = 5
            elapsed_time = 0

            final_status = None
            while elapsed_time < max_wait_time_seconds:
                await asyncio.sleep(poll_interval_seconds)
                elapsed_time += poll_interval_seconds
                current_task_status_info = await orchestrator.get_task_status(task_id_to_monitor)
                
                if current_task_status_info:
                    logger.info(f"Task {task_id_to_monitor} current status: {current_task_status_info.status} (after {elapsed_time}s)")
                    if current_task_status_info.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.BIDDING_FAILED, TaskStatus.CANCELLED]:
                        final_status = current_task_status_info.status
                        logger.info(f"Task {task_id_to_monitor} reached final state: {final_status}")
                        if current_task_status_info.result_data:
                            logger.info(f"Task result: {current_task_status_info.result_data}")
                        if current_task_status_info.error_message:
                            logger.warning(f"Task error: {current_task_status_info.error_message}")
                        break 
                else:
                    logger.warning(f"Could not retrieve status for task {task_id_to_monitor} after {elapsed_time}s.")
                    # It might have been processed very quickly and removed if not configured to keep all tasks
                    # Or an issue occurred. For this test, we'll assume it might be an issue.
                    break
            
            if not final_status:
                logger.warning(f"Task {task_id_to_monitor} did not reach a final state within {max_wait_time_seconds}s.")
                current_task_status_info = await orchestrator.get_task_status(task_id_to_monitor)
                if current_task_status_info:
                     logger.info(f"Last known status: {current_task_status_info.status}")
                else:
                    logger.info("Last known status: Unknown / Not Found")

        else:
            logger.error("Failed to submit task to orchestrator.")

    except Exception as e:
        logger.error(f"An error occurred during the test: {e}", exc_info=True)
    finally:
        logger.info("Shutting down agents...")
        await orchestrator.stop()
        for worker in workers:
            await worker.stop()
        logger.info("All agents stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Test script interrupted by user. Shutting down...")
    except Exception as e:
        logger.error(f"Unhandled exception in main: {e}", exc_info=True)
