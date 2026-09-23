"""
Tau2 integration utilities for CaveAgent.

This module provides utilities to integrate CaveAgent with tau2-bench
without modifying tau2's core files.
"""

from loguru import logger
from tau2.registry import registry
from adapters.tau2_cave_agent_registry import Tau2CaveAgentRegistry


def register_cave_agent():
    """Register CaveAgent with tau2's global registry."""
    try:
        registry.register_agent(Tau2CaveAgentRegistry, "cave_agent")
        logger.info("✓ CaveAgent registered with tau2")
        return True
    except ValueError as e:
        if "already registered" in str(e):
            logger.debug("CaveAgent already registered")
            return True
        raise


def patch_tau2_for_cave_agent():
    """Patch tau2's run_task to support CaveAgent."""
    import tau2.run
    from tau2.evaluator.evaluator import EvaluationType, evaluate_simulation
    from tau2.orchestrator.orchestrator import Orchestrator

    def patched_run_task(domain, task, agent, user, llm_agent=None, llm_args_agent=None,
                        llm_user=None, llm_args_user=None, max_steps=100, max_errors=10,
                        evaluation_type=None, seed=None, enforce_communication_protocol=False):
        """Run task with CaveAgent support."""
        evaluation_type = evaluation_type or EvaluationType.ALL

        environment_constructor = registry.get_env_constructor(domain)
        environment = environment_constructor()
        AgentConstructor = registry.get_agent_constructor(agent)

        # Instantiate agent
        agent_instance = AgentConstructor(
            tools=environment.get_tools(),
            domain_policy=environment.get_policy(),
            llm=llm_agent,
            llm_args=llm_args_agent,
            task=task,
        )

        # Setup user
        try:
            user_tools = environment.get_user_tools()
        except Exception:
            user_tools = None

        UserConstructor = registry.get_user_constructor(user)
        user_instance = UserConstructor(
            tools=user_tools,
            instructions=str(task.user_scenario),
            llm=llm_user,
            llm_args=llm_args_user,
        )

        # Run orchestrator
        orchestrator = Orchestrator(
            domain=domain,
            agent=agent_instance,
            user=user_instance,
            environment=environment,
            task=task,
            max_steps=max_steps,
            max_errors=max_errors,
            seed=seed,
            solo_mode=False,
            validate_communication=enforce_communication_protocol,
        )
        simulation = orchestrator.run()

        # Evaluate
        reward_info = evaluate_simulation(
            domain=domain,
            task=task,
            simulation=simulation,
            evaluation_type=evaluation_type,
            solo_mode=False,
        )
        simulation.reward_info = reward_info

        logger.info(
            f"FINISHED SIMULATION: Domain: {domain}, Task: {task.id}, "
            f"Agent: {agent_instance.__class__.__name__}, Reward: {reward_info.reward}"
        )
        return simulation

    tau2.run.run_task = patched_run_task
    logger.info("✓ Tau2 patched for CaveAgent")


def setup_cave_agent_for_tau2():
    """Setup CaveAgent integration with tau2 (register + patch)."""
    register_cave_agent()
    patch_tau2_for_cave_agent()

    # Verify
    info = registry.get_info()
    assert "cave_agent" in info.agents, "cave_agent not registered!"
    logger.info(f"✓ CaveAgent ready. Available agents: {info.agents}")
