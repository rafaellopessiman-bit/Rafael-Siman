from __future__ import annotations

import json
from typing import Any
from urllib import error, request


def _schedule_status_facts(payload: dict[str, Any]) -> list[tuple[str, str]]:
    schedule = payload.get("schedule", {}) if isinstance(payload.get("schedule"), dict) else {}
    steps = payload.get("steps", {}) if isinstance(payload.get("steps"), dict) else {}
    facts = [
        ("status", str(payload.get("status", "ok"))),
        ("jobs", ", ".join(str(item) for item in schedule.get("jobs", []))),
        ("origem", str(schedule.get("documents_path", ""))),
        ("banco", str(schedule.get("database_path", ""))),
    ]
    for name, step in steps.items():
        if isinstance(step, dict):
            facts.append((f"step:{name}", str(step.get("status", "ok"))))
    return facts


def _collect_regression_lines(payload: dict[str, Any]) -> list[str]:
    steps = payload.get("steps", {}) if isinstance(payload.get("steps"), dict) else {}
    evaluate = steps.get("evaluate", {}) if isinstance(steps.get("evaluate"), dict) else {}
    regressions = evaluate.get("regressions", []) if isinstance(evaluate.get("regressions"), list) else []
    return [str(item) for item in regressions if str(item)]


def _collect_audit_highlights(payload: dict[str, Any]) -> list[tuple[str, str]]:
    steps = payload.get("steps", {}) if isinstance(payload.get("steps"), dict) else {}
    audit = steps.get("audit", {}) if isinstance(steps.get("audit"), dict) else {}
    highlights = []
    if audit.get("ocr_required_count"):
        highlights.append(("ocr_pendente", str(audit["ocr_required_count"])))
    if audit.get("isolated_count"):
        highlights.append(("isolados", str(audit["isolated_count"])))
    if audit.get("review_count"):
        highlights.append(("em_revisao", str(audit["review_count"])))
    return highlights


def build_teams_webhook_payload(payload: dict[str, Any]) -> dict[str, Any]:
    status = str(payload.get("status", "ok")).lower()
    color = {
        "ok": "2EB886",
        "partial": "D9A441",
        "error": "C43D3D",
    }.get(status, "808080")
    facts = [
        {"name": name, "value": value or "-"}
        for name, value in _schedule_status_facts(payload)
    ]
    return {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "summary": f"Atlas Local Schedule: {status}",
        "themeColor": color,
        "title": f"Atlas Local Schedule: {status.upper()}",
        "sections": _build_teams_sections(payload, facts),
    }


def _build_teams_sections(payload: dict[str, Any], facts: list[dict[str, str]]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = [
            {
                "facts": facts,
                "markdown": True,
            }
    ]

    regressions = _collect_regression_lines(payload)
    if regressions:
        sections.append(
            {
                "title": "Regressoes detectadas",
                "text": "\n".join(f"- {item}" for item in regressions[:8]),
                "markdown": True,
            }
        )

    audit_highlights = _collect_audit_highlights(payload)
    if audit_highlights:
        sections.append(
            {
                "title": "Sinais operacionais",
                "facts": [{"name": name, "value": value} for name, value in audit_highlights],
                "markdown": True,
            }
        )

    return sections


def build_slack_webhook_payload(payload: dict[str, Any]) -> dict[str, Any]:
    facts = _schedule_status_facts(payload)
    lines = [f"*{name}*: {value or '-'}" for name, value in facts]
    status = str(payload.get("status", "ok")).upper()
    blocks: list[dict[str, Any]] = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Atlas Local Schedule: {status}*\n" + "\n".join(lines),
            },
        }
    ]

    regressions = _collect_regression_lines(payload)
    if regressions:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Regressoes detectadas*\n" + "\n".join(f"- {item}" for item in regressions[:8]),
                },
            }
        )

    audit_highlights = _collect_audit_highlights(payload)
    if audit_highlights:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Sinais operacionais*\n" + "\n".join(f"- {name}: {value}" for name, value in audit_highlights),
                },
            }
        )

    return {
        "text": f"Atlas Local Schedule: {status}",
        "blocks": blocks,
    }


def build_webhook_payload(payload: dict[str, Any], format_name: str = "raw") -> dict[str, Any]:
    normalized = format_name.strip().lower()
    if normalized == "teams":
        return build_teams_webhook_payload(payload)
    if normalized == "slack":
        return build_slack_webhook_payload(payload)
    return payload


def send_json_webhook(url: str, payload: dict[str, Any], timeout_seconds: int = 10) -> dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url=url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            response_body = response.read().decode("utf-8", errors="replace")
            status_code = getattr(response, "status", None)
            if status_code is None:
                status_code = response.getcode()
            return {
                "status": "ok",
                "status_code": status_code,
                "body": response_body,
            }
    except error.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")
        return {
            "status": "error",
            "status_code": exc.code,
            "body": response_body,
            "message": str(exc),
        }
    except error.URLError as exc:
        return {
            "status": "error",
            "status_code": None,
            "body": "",
            "message": str(exc.reason),
        }
