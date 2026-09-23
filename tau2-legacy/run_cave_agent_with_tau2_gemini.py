"""
Run CaveAgent evaluation using tau2's infrastructure.

Usage:
    python run_cave_agent_with_tau2.py
"""

import os
import datetime
from loguru import logger
from adapters.tau2_integration import setup_cave_agent_for_tau2
from tau2.data_model.simulation import RunConfig
from tau2.run import run_domain

setup_cave_agent_for_tau2()

num_trials = 1
domain = "airline"
model = "gemini-3-pro"
timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H:%M:%S")

# Configure your run
config = RunConfig(
    domain=domain,
    task_set_name=None,  # Uses default airline tasks
    task_split_name="base",

    # Agent configuration
    agent="cave_agent",
    llm_agent="gemini-3-pro-preview",  # Your model

    llm_args_agent={
        "api_key": os.environ["GEMINI_API_KEY"],
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "temperature": 1,
        "max_steps": 100,  # CaveAgent max steps
        "log_level": "INFO",  # CaveAgent log level (ERROR/INFO/DEBUG)
        "run_id": f"{timestamp}_{model}",  # Unique ID for this run
        "run_domain": domain,  # Domain for folder organization
    },

    # User simulator configuration
    user="user_simulator",

    llm_user="openai/deepseek-chat",
    llm_args_user={
        "api_key": os.environ["DEEPSEEK_API_KEY"],
        "base_url": "https://api.deepseek.com/v1",
        "temperature": 0.2,
    },

    # Execution settings
    num_trials=num_trials,  # Number of times to run each task
    max_steps=100,  # tau2 orchestrator max steps
    max_errors=10,
    save_to=f"{timestamp}_cave_agent_{domain}_{model}_{num_trials}_trials_task",  # Results file name
    max_concurrency=5,  # Parallel execution (increase for faster runs)
    log_level="INFO",
    enforce_communication_protocol=False,
)

# Run the evaluation
logger.info("="*80)
logger.info("Starting CaveAgent evaluation via tau2")
logger.info("="*80)

results = run_domain(config)

logger.info("="*80)
logger.info("Evaluation completed!")
logger.info(f"Results saved to: data/simulations/{config.save_to}.json")
logger.info("="*80)
