from __future__ import annotations

from time import perf_counter
import importlib

from src.planner.schemas import StructuredPlanModel


_llm_client = importlib.import_module("src.core.llm_client")


def _build_planner_prompt(goal: str) -> str:
    return f"""
Você é um planejador técnico local.
Retorne SOMENTE JSON válido no schema abaixo.

Schema:
{{
  "goal": "string",
  "steps": [
    {{
      "step": 1,
      "action": "string",
      "reason": "string",
      "expected_output": "string"
    }}
  ],
  "assumptions": ["string"],
  "risks": ["string"]
}}

Regras:
- Não use markdown.
- Não use comentários.
- Não invente arquivos inexistentes.
- Seja operacional e objetivo.
- Gere entre 3 e 6 passos.

Objetivo:
{goal}
""".strip()


def _deterministic_plan(goal: str) -> StructuredPlanModel:
    normalized = goal.strip()

    return StructuredPlanModel(
        goal=normalized,
        steps=[
            {
                "step": 1,
                "action": "Inspecionar o estado atual do projeto e confirmar o ponto de entrada do fluxo.",
                "reason": "Evita alterar módulos errados e reduz regressão estrutural.",
                "expected_output": "Mapa claro dos arquivos e da rota afetada.",
            },
            {
                "step": 2,
                "action": "Aplicar a menor mudança possível no módulo alvo, preservando a interface pública.",
                "reason": "Reduz acoplamento e mantém compatibilidade com o baseline.",
                "expected_output": "Patch local, pequeno e reversível.",
            },
            {
                "step": 3,
                "action": "Executar testes direcionados da rota afetada e validar imports.",
                "reason": "Confirma que a mudança resolveu o problema certo sem quebrar adjacências.",
                "expected_output": "Resultado objetivo de testes e smoke test.",
            },
        ],
        assumptions=[
            "O ambiente local está configurado com a venv ativa.",
            "O projeto deve evoluir por patch incremental.",
        ],
        risks=[
            "Interfaces legadas podem depender de nomes antigos.",
            "Mudanças não verificadas por teste podem gerar regressão lateral.",
        ],
    )


def _should_use_deterministic_branch(goal: str) -> bool:
    normalized = goal.casefold()

    triggers = [
        "baseline",
        "validação local",
        "validacao local",
        "smoke test",
        "teste local",
        "patch incremental",
    ]
    return any(trigger in normalized for trigger in triggers)


def _render_answer(plan: StructuredPlanModel) -> str:
    lines: list[str] = [f"Objetivo: {plan.goal}", "", "Passos:"]
    for step in plan.steps:
        lines.append(f"{step.step}. {step.action}")
        lines.append(f"   Motivo: {step.reason}")
        lines.append(f"   Saída esperada: {step.expected_output}")

    if plan.assumptions:
        lines.append("")
        lines.append("Premissas:")
        for item in plan.assumptions:
            lines.append(f"- {item}")

    if plan.risks:
        lines.append("")
        lines.append("Riscos:")
        for item in plan.risks:
            lines.append(f"- {item}")

    return "\n".join(lines).strip()


def plan_goal(goal: str) -> dict:
    started = perf_counter()
    warnings: list[str] = []
    errors: list[str] = []
    model_name = None

    try:
        model_name = getattr(_llm_client, "MODEL", None) or getattr(_llm_client, "DEFAULT_MODEL", None)
    except Exception:
        model_name = None

    if _should_use_deterministic_branch(goal):
        plan = _deterministic_plan(goal)
        elapsed_ms = int((perf_counter() - started) * 1000)
        return {
            "route": "planner",
            "status": "ok",
            "answer": _render_answer(plan),
            "goal": plan.goal,
            "steps": [step.model_dump() for step in plan.steps],
            "assumptions": list(plan.assumptions),
            "risks": list(plan.risks),
            "warnings": ["branch_deterministico_ativo"],
            "errors": [],
            "meta": {
                "model": model_name,
                "elapsed_ms": elapsed_ms,
            },
        }

    prompt = _build_planner_prompt(goal)

    try:
        structured = _llm_client.structured_call(prompt, StructuredPlanModel, temperature=0.0)
        elapsed_ms = int((perf_counter() - started) * 1000)
        return {
            "route": "planner",
            "status": "ok",
            "answer": _render_answer(structured),
            "goal": structured.goal,
            "steps": [step.model_dump() for step in structured.steps],
            "assumptions": list(structured.assumptions),
            "risks": list(structured.risks),
            "warnings": warnings,
            "errors": [],
            "meta": {
                "model": model_name,
                "elapsed_ms": elapsed_ms,
            },
        }
    except Exception as exc:
        errors.append(str(exc))
        warnings.append("fallback_deterministico_apos_falha_schema")

        fallback = _deterministic_plan(goal)
        elapsed_ms = int((perf_counter() - started) * 1000)

        return {
            "route": "planner",
            "status": "error",
            "answer": _render_answer(fallback),
            "goal": fallback.goal,
            "steps": [step.model_dump() for step in fallback.steps],
            "assumptions": list(fallback.assumptions),
            "risks": list(fallback.risks),
            "warnings": warnings,
            "errors": errors,
            "meta": {
                "model": model_name,
                "elapsed_ms": elapsed_ms,
            },
        }


generate_plan = plan_goal
create_plan = plan_goal
handle_plan = plan_goal
run_planner = plan_goal
