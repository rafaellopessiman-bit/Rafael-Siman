import src.main as main


def test_coerce_plan_result_preserves_string():
    assert main._coerce_plan_result("plano::texto") == "plano::texto"


def test_coerce_plan_result_coerces_complete_dict():
    result = main._coerce_plan_result(
        {
            "status": "ok",
            "objective": "fechar v1",
            "answer": "Plano estruturado",
        }
    )

    assert result.status == "ok"
    assert result.objective == "fechar v1"
    assert result.answer == "Plano estruturado"


def test_coerce_plan_result_returns_answer_from_partial_dict():
    result = main._coerce_plan_result({"answer": "Plano parcial"})
    assert result == "Plano parcial"


def test_handle_plan_returns_string_directly(monkeypatch):
    monkeypatch.setattr(main, "generate_plan", lambda objective: "plano::texto")
    assert main.handle_plan("fechar v1") == "plano::texto"


def test_handle_plan_renders_complete_dict(monkeypatch):
    monkeypatch.setattr(
        main,
        "generate_plan",
        lambda objective: {
            "status": "ok",
            "objective": objective,
            "answer": "Plano estruturado",
        },
    )
    monkeypatch.setattr(
        main,
        "render_plan_response",
        lambda response: f"{response.status}|{response.objective}|{response.answer}",
    )

    assert main.handle_plan("fechar v1") == "ok|fechar v1|Plano estruturado"


def test_handle_plan_returns_answer_from_partial_dict(monkeypatch):
    monkeypatch.setattr(main, "generate_plan", lambda objective: {"answer": "Plano parcial"})
    assert main.handle_plan("fechar v1") == "Plano parcial"
