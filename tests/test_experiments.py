from behavioral_lab.agents.factory import build_agents
from behavioral_lab.agents.llm import LLMAgent
from behavioral_lab.experiments import ExperimentRunner
from behavioral_lab.experiments.evaluators import CooperationEvaluator
from behavioral_lab.experiments.report import compare_reports
from behavioral_lab.providers.fake import FakeLLMProvider


def test_runner_repeats_seeds_and_reports_metrics(tmp_path):
    report = ExperimentRunner([101, 202], max_rounds=2, output_dir=tmp_path).run()

    assert [summary.seed for summary in report.summaries] == [101, 202]
    assert len(report.comparison) == 1
    assert report.comparison[0]["runs"] == 2
    assert set(report.summaries[0].metrics) == {
        "survival",
        "hunger",
        "consumption",
        "cooperation",
            "disclosure",
            "resource_distribution",
            "llm_reliability",
        }
    assert all(summary.event_path and summary.event_path.exists() for summary in report.summaries)


def test_runner_supports_controlled_positions_and_five_llm_agents():
    report = ExperimentRunner(
        [101],
        max_rounds=1,
        agent_mode="llm",
        all_llm=True,
        initial_positions={"Agent_A": "KITCHEN", "Agent_B": "KITCHEN"},
    ).run()

    summary = report.summaries[0]
    assert all(agent["actions"] == 1 for agent in summary.per_agent.values())
    assert summary.per_agent["Agent_A"]["location"] == "KITCHEN"
    assert summary.model == "fake-model"


def test_factory_can_select_the_five_llm_configuration():
    ids = ["Agent_A", "Agent_B", "Agent_C", "Agent_D", "Agent_E"]
    agents = build_agents(
        ids,
        mode="llm",
        provider=FakeLLMProvider(['{"action":"wait"}']),
        llm_agent_ids=ids,
    )
    assert all(isinstance(agent, LLMAgent) for agent in agents.values())


def test_second_scenario_uses_same_runner_contract():
    report = ExperimentRunner([7], max_rounds=1, scenario="common_pool").run()
    snapshot = report.runs[0].snapshot
    assert snapshot["scenario"] == "common_pool"
    assert snapshot["locations"]["STORAGE"]["food"] == 0


def test_custom_evaluator_and_cross_report_comparison():
    fake = ExperimentRunner(
        [1], max_rounds=1, evaluators=[CooperationEvaluator(minimum_units=1)]
    ).run()
    llm = ExperimentRunner([1], max_rounds=1, agent_mode="llm").run()

    assert set(fake.summaries[0].evaluations) == {"cooperation"}
    comparison = compare_reports(fake, llm)
    assert len(comparison) == 2
