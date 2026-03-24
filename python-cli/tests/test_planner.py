from __future__ import annotations

from src.planner.planner import plan_goal


def test_plan_goal_uses_structured_output_when_available(monkeypatch) -> None:
    from src.planner.schemas import StructuredPlanModel

    def fake_structured_call(prompt, response_model, temperature=0.0):
        return StructuredPlanModel(
            goal="Montar validação do planner",
            steps=[
                {
                    "step": 1,
                    "action": "Ler o objetivo",
                    "reason": "Entender o escopo",
                    "expected_output": "Objetivo interpretado",
                },
                {
                    "step": 2,
                    "action": "Gerar plano estruturado",
                    "reason": "Padronizar a saída",
                    "expected_output": "Plano com passos válidos",
                },
            ],
            assumptions=["Ambiente local ativo"],
            risks=["Provider pode variar formato"],
        )

    monkeypatch.setattr("src.core.llm_client.structured_call", fake_structured_call)

    result = plan_goal("Criar um plano de validação do planner")

    assert result["status"] == "ok"
    assert result["route"] == "planner"
    assert result["goal"] == "Montar validação do planner"
    assert len(result["steps"]) == 2
    assert result["errors"] == []
    assert "Passos:" in result["answer"]


def test_plan_goal_returns_error_and_fallback_when_schema_fails(monkeypatch) -> None:
    def fake_structured_call(prompt, response_model, temperature=0.0):
        raise RuntimeError("Schema do provider inválido")

    monkeypatch.setattr("src.core.llm_client.structured_call", fake_structured_call)

    result = plan_goal("Criar um plano para integração do planner")

    assert result["status"] == "error"
    assert result["route"] == "planner"
    assert len(result["steps"]) >= 1
    assert "Schema do provider inválido" in result["errors"][0]
    assert "fallback_deterministico_apos_falha_schema" in result["warnings"]


def test_plan_goal_keeps_deterministic_branch_temporarily() -> None:
    result = plan_goal("Executar validação local do baseline com patch incremental")

    assert result["status"] == "ok"
    assert result["route"] == "planner"
    assert len(result["steps"]) >= 1
    assert "branch_deterministico_ativo" in result["warnings"]
