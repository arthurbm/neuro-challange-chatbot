"""
Integration tests for Agent Trajectories using AgentEvals

Tests agent end-to-end behavior with trajectory matching and LLM-as-judge.
Uses GenericFakeChatModel to simulate deterministic agent behavior.
"""
import pytest
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from agentevals.trajectory.match import create_trajectory_match_evaluator
from agentevals.trajectory.llm import create_trajectory_llm_as_judge, TRAJECTORY_ACCURACY_PROMPT


# ==============================================================================
# Test Agent Trajectory - Strict Match
# ==============================================================================

@pytest.mark.integration
@pytest.mark.langsmith
@pytest.mark.skip(reason="Requires full agent setup - implement when agent wrapper ready")
def test_simple_query_strict_trajectory():
    """
    Agent should query database, then respond.
    Uses strict trajectory matching - exact sequence of messages.
    """
    # Create evaluator for strict matching
    evaluator = create_trajectory_match_evaluator(
        trajectory_match_mode="strict"
    )

    # TODO: Setup agent with fake LLM
    # agent = create_agent(fake_llm, tools=[query_database, generate_chart])

    # TODO: Invoke agent
    # result = agent.invoke({
    #     "messages": [HumanMessage(content="Qual a taxa média de inadimplência?")]
    # })

    # Reference trajectory (expected sequence)
    reference_trajectory = [
        HumanMessage(content="Qual a taxa média de inadimplência?"),
        AIMessage(
            content="",
            tool_calls=[{
                "id": "call_1",
                "name": "query_database",
                "args": {"question_context": "Qual a taxa média de inadimplência?"}
            }]
        ),
        ToolMessage(
            content='{"sql": "SELECT AVG(\\"TARGET\\") as taxa FROM credit_train", "result": [{"taxa": 0.0923}]}',
            tool_call_id="call_1"
        ),
        AIMessage(content="A taxa média de inadimplência é 9,23%")
    ]

    # TODO: Evaluate trajectory
    # evaluation = evaluator(
    #     outputs=result["messages"],
    #     reference_outputs=reference_trajectory
    # )
    # assert evaluation["score"] is True


# ==============================================================================
# Test Agent Trajectory - Unordered Match
# ==============================================================================

@pytest.mark.integration
@pytest.mark.langsmith
@pytest.mark.skip(reason="Requires full agent setup")
def test_query_and_visualize_unordered():
    """
    Agent queries database then generates chart.
    Uses unordered matching - tools can be called in any order.
    """
    evaluator = create_trajectory_match_evaluator(
        trajectory_match_mode="unordered"
    )

    # Reference shows query then chart, but actual order may vary
    reference_trajectory = [
        HumanMessage(content="Mostre a taxa de inadimplência por UF em gráfico"),
        AIMessage(
            content="",
            tool_calls=[
                {"id": "call_1", "name": "query_database", "args": {"question_context": "taxa por UF"}},
            ]
        ),
        ToolMessage(content='{"sql": "SELECT ...", "result": [...]}', tool_call_id="call_1"),
        AIMessage(
            content="",
            tool_calls=[
                {"id": "call_2", "name": "generate_chart", "args": {"data": [...]}},
            ]
        ),
        ToolMessage(content='[{"type": "image", ...}]', tool_call_id="call_2"),
        AIMessage(content="Aqui está o gráfico solicitado"),
    ]

    # TODO: Test with actual agent
    # evaluation = evaluator(outputs=result["messages"], reference_outputs=reference_trajectory)
    # assert evaluation["score"] is True


# ==============================================================================
# Test Agent Trajectory - Superset Match (Retry Allowed)
# ==============================================================================

@pytest.mark.integration
@pytest.mark.langsmith
@pytest.mark.skip(reason="Requires full agent setup")
def test_retry_trajectory_superset():
    """
    Agent may retry SQL generation (extra tool calls allowed).
    Uses superset matching - actual can have more tool calls than reference.
    """
    evaluator = create_trajectory_match_evaluator(
        trajectory_match_mode="superset"
    )

    # Reference shows 1 query attempt, actual may have 2-3 retries
    reference_trajectory = [
        HumanMessage(content="Taxa de inadimplência por classe social"),
        AIMessage(
            content="",
            tool_calls=[{"id": "call_1", "name": "query_database", "args": {}}]
        ),
        ToolMessage(content='{"result": [...]}', tool_call_id="call_1"),
        AIMessage(content="Resultado..."),
    ]

    # TODO: Test with agent that might retry
    # evaluation = evaluator(outputs=result["messages"], reference_outputs=reference_trajectory)
    # assert evaluation["score"] is True  # Should pass even if agent made extra retry calls


# ==============================================================================
# Test LLM-as-Judge for Trajectory Quality
# ==============================================================================

@pytest.mark.integration
@pytest.mark.langsmith
@pytest.mark.skip(reason="Requires full agent setup and OpenAI API for judge")
def test_agent_trajectory_quality_llm_judge():
    """
    Use LLM-as-judge to evaluate overall agent trajectory quality.
    More flexible than strict matching - assesses reasonableness.
    """
    # Create LLM judge evaluator
    judge = create_trajectory_llm_as_judge(
        model="openai:gpt-4o-mini",  # Judge model
        prompt=TRAJECTORY_ACCURACY_PROMPT,
    )

    # TODO: Get agent trajectory
    # result = agent.invoke({
    #     "messages": [HumanMessage("Análise completa de inadimplência por UF e sexo")]
    # })

    # Evaluate trajectory quality
    # evaluation = judge(outputs=result["messages"])
    #
    # assert evaluation["score"] is True, f"Judge failed: {evaluation['comment']}"
    # assert "reasonable" in evaluation["comment"].lower() or "correto" in evaluation["comment"].lower()


# ==============================================================================
# Test LLM-as-Judge with Reference Trajectory
# ==============================================================================

@pytest.mark.integration
@pytest.mark.langsmith
@pytest.mark.skip(reason="Requires full agent setup")
def test_agent_trajectory_with_reference_judge():
    """
    Use LLM judge with reference trajectory for comparison.
    """
    from agentevals.trajectory.llm import TRAJECTORY_ACCURACY_PROMPT_WITH_REFERENCE

    judge = create_trajectory_llm_as_judge(
        model="openai:gpt-4o-mini",
        prompt=TRAJECTORY_ACCURACY_PROMPT_WITH_REFERENCE,
    )

    reference_trajectory = [
        HumanMessage(content="Compare inadimplência entre homens e mulheres"),
        AIMessage(
            content="",
            tool_calls=[{"id": "call_1", "name": "query_database", "args": {}}]
        ),
        ToolMessage(content='{"result": [...]}', tool_call_id="call_1"),
        AIMessage(content="Os homens têm taxa de 8% e mulheres 10%"),
    ]

    # TODO: Test with agent
    # evaluation = judge(
    #     outputs=result["messages"],
    #     reference_outputs=reference_trajectory
    # )
    # assert evaluation["score"] is True


# ==============================================================================
# Placeholder Tests (Passing) for Initial Suite
# ==============================================================================

@pytest.mark.integration
def test_agentevals_library_imported():
    """Verify agentevals library is available."""
    from agentevals.trajectory.match import create_trajectory_match_evaluator
    from agentevals.trajectory.llm import create_trajectory_llm_as_judge

    # Should be able to create evaluators
    evaluator = create_trajectory_match_evaluator(trajectory_match_mode="strict")
    assert evaluator is not None


@pytest.mark.integration
def test_trajectory_match_evaluator_modes():
    """Test all trajectory match modes are available."""
    modes = ["strict", "unordered", "subset", "superset"]

    for mode in modes:
        evaluator = create_trajectory_match_evaluator(trajectory_match_mode=mode)
        assert evaluator is not None, f"Failed to create evaluator for mode: {mode}"


# ==============================================================================
# Notes for Future Implementation
# ==============================================================================

"""
To complete these tests, you need to:

1. Create agent factory function:
   ```python
   def create_test_agent(llm, tools):
       from src.agent import create_agent
       return create_agent(llm, tools)
   ```

2. Setup fake LLM in conftest.py for agent responses:
   ```python
   @pytest.fixture
   def fake_agent_llm():
       return GenericFakeChatModel(messages=iter([
           AIMessage(tool_calls=[...]),  # First: call tool
           AIMessage(content="..."),     # Then: respond to user
       ]))
   ```

3. Enable LangSmith logging in tests:
   ```python
   from langsmith import testing as t

   t.log_inputs({"question": "..."})
   t.log_outputs({"messages": result["messages"]})
   t.log_reference_outputs({"messages": reference_trajectory})
   ```

4. Run tests with LangSmith:
   ```bash
   pytest tests/integration/test_agent_trajectories.py --langsmith-output
   ```
"""
