#!/usr/bin/env python3
"""校验 fallback QTE Authoring Spec 的结构、校准状态与引用完整性。"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

from schema_subset import validate_schema


def issue(code: str, path: str, message: str) -> dict[str, str]:
    return {"code": code, "path": path, "message": message}


def validate_authoring(root: dict[str, Any], schema: dict[str, Any], require_ready: bool = False) -> list[dict[str, str]]:
    errors = [issue("E_SCHEMA", item.path, item.message) for item in validate_schema(root, schema)]
    if errors:
        return errors

    parameters = root["calibration_contract"]["parameters"]
    parameter_ids: set[str] = set()
    open_parameter_ids: set[str] = set()
    parameter_values: dict[str, float] = {}
    for index, parameter in enumerate(parameters):
        parameter_id = parameter["id"]
        path = f"/calibration_contract/parameters/{index}"
        if parameter_id in parameter_ids:
            errors.append(issue("E_PARAMETER_DUPLICATE", f"{path}/id", "校准参数 ID 必须唯一。"))
        parameter_ids.add(parameter_id)
        status = parameter["status"]
        value = parameter["value"]
        if status == "open":
            open_parameter_ids.add(parameter_id)
            if value is not None:
                errors.append(issue("E_OPEN_VALUE", f"{path}/value", "open 参数的 value 必须为 null，不能把模板数值伪装成未决策。"))
        elif not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            errors.append(issue("E_CALIBRATED_VALUE", f"{path}/value", "measured/inherited 参数必须提供有限数值。"))
        else:
            parameter_values[parameter_id] = float(value)
            domain = parameter["domain"]
            domain_valid = {
                "positive": value > 0,
                "nonnegative": value >= 0,
                "signed": True,
                "ratio": 0 <= value <= 1,
                "positive_integer": isinstance(value, int) and not isinstance(value, bool) and value > 0,
                "nonnegative_integer": isinstance(value, int) and not isinstance(value, bool) and value >= 0,
            }[domain]
            if not domain_valid:
                errors.append(issue("E_PARAMETER_DOMAIN", f"{path}/value", f"参数值不符合声明的 {domain} 数值域。"))

    references: list[tuple[str, str]] = [
        ("/target/session_duration_param", root["target"]["session_duration_param"]),
        ("/mechanics/clock/calibration_offset_param", root["mechanics"]["clock"]["calibration_offset_param"]),
    ]
    cue_defaults = root["mechanics"]["cue_defaults"]
    for key in ("telegraph_param", "input_window_param", "recovery_param", "minimum_target_size_param", "concurrency_limit_param"):
        references.append((f"/mechanics/cue_defaults/{key}", cue_defaults[key]))

    pattern_ids = {pattern["id"] for pattern in root["fun_contract"]["action_patterns"]}
    if len(pattern_ids) != len(root["fun_contract"]["action_patterns"]):
        errors.append(issue("E_PATTERN_DUPLICATE", "/fun_contract/action_patterns", "action pattern ID 必须唯一。"))

    allowed_actions = set(root["mechanics"]["input_policy"]["allowed_actions"])
    subtype_action = {
        "tap_target": "tap_target",
        "timing_gate": "timing_press",
        "swipe_direction": "swipe_direction",
        "swipe_path": "swipe_path",
        "drag_intercept": "drag_intercept",
    }
    for cue_index, cue in enumerate(root["mechanics"]["cue_nodes"]):
        cue_path = f"/mechanics/cue_nodes/{cue_index}"
        if cue["pattern_id"] not in pattern_ids:
            errors.append(issue("E_PATTERN_REF", f"{cue_path}/pattern_id", "cue 引用了不存在的 action pattern。"))
        trigger_param = cue["trigger"]["at_param"]
        if trigger_param is not None:
            references.append((f"{cue_path}/trigger/at_param", trigger_param))
        trigger_type = cue["trigger"]["type"]
        trigger_event = cue["trigger"]["event"]
        trigger_valid = (
            (trigger_type == "timeline" and trigger_param is not None and trigger_event is None)
            or (trigger_type in {"event", "player_state"} and trigger_param is None and trigger_event is not None)
            or (trigger_type == "previous_resolved" and trigger_param is None and trigger_event is None)
        )
        if not trigger_valid:
            errors.append(issue("E_TRIGGER_SHAPE", f"{cue_path}/trigger", "trigger type 必须与 at_param/event 的非空字段严格匹配。"))

        action = cue["input"]["action"]
        if subtype_action[cue["subtype"]] != action:
            errors.append(issue("E_CUE_ACTION", f"{cue_path}/input/action", "cue subtype 与语义 input action 不一致。"))
        if action not in allowed_actions:
            errors.append(issue("E_ACTION_ALLOWED", f"{cue_path}/input/action", "cue 使用了 input_policy 未允许的动作。"))
        for key, value in cue["timing"].items():
            references.append((f"{cue_path}/timing/{key}", value))
        open_value = parameter_values.get(cue["timing"]["window_open_offset_param"])
        close_value = parameter_values.get(cue["timing"]["window_close_offset_param"])
        if open_value is not None and close_value is not None and open_value >= close_value:
            errors.append(issue("E_WINDOW_ORDER", f"{cue_path}/timing", "window_open_offset 必须早于 window_close_offset。"))

        grades = [judgement["grade"] for judgement in cue["judgements"]]
        if len(grades) != len(set(grades)) or set(grades) != {"perfect", "success", "miss"}:
            errors.append(issue("E_JUDGEMENT_SET", f"{cue_path}/judgements", "每个 cue 必须且只能声明 perfect、success、miss 三种评级。"))
        priorities = [judgement["priority"] for judgement in cue["judgements"]]
        if len(priorities) != len(set(priorities)):
            errors.append(issue("E_JUDGEMENT_PRIORITY", f"{cue_path}/judgements", "评级 priority 必须唯一。"))
        for judgement_index, judgement in enumerate(cue["judgements"]):
            judgement_path = f"{cue_path}/judgements/{judgement_index}"
            requirements = judgement.get("requirements", [])
            if judgement["grade"] in {"perfect", "success"} and not requirements:
                errors.append(issue("E_JUDGEMENT_REQUIREMENT", f"{judgement_path}/requirements", "perfect/success 必须依赖本次有效输入的可判定 requirement。"))
            if judgement["grade"] == "miss" and judgement.get("otherwise") is not True:
                errors.append(issue("E_MISS_FALLBACK", judgement_path, "miss 必须提供 otherwise fallback，确保边界无空洞。"))
            for requirement_index, requirement in enumerate(requirements):
                requirement_path = f"{judgement_path}/requirements/{requirement_index}"
                for reference_index, value in enumerate(requirement["parameter_refs"]):
                    references.append((f"{requirement_path}/parameter_refs/{reference_index}", value))
                requirement_type = requirement["type"]
                if requirement_type in {"signed_timing_error", "overlap_ratio"} and not requirement["parameter_refs"]:
                    errors.append(issue("E_REQUIREMENT_PARAM", f"{requirement_path}/parameter_refs", "该 requirement 必须引用校准参数。"))
                if requirement_type in {"target_match", "overlap_ratio"} and not requirement.get("target_id"):
                    errors.append(issue("E_REQUIREMENT_TARGET", f"{requirement_path}/target_id", "目标类 requirement 必须声明 target_id。"))
                if requirement_type == "direction_match" and not requirement.get("direction"):
                    errors.append(issue("E_REQUIREMENT_DIRECTION", f"{requirement_path}/direction", "方向 requirement 必须声明 direction。"))
                if requirement_type == "path_sequence" and not requirement.get("ordered_points"):
                    errors.append(issue("E_REQUIREMENT_PATH", f"{requirement_path}/ordered_points", "路径 requirement 必须声明 ordered_points。"))

        grade_by_name = {judgement["grade"]: judgement for judgement in cue["judgements"]}
        perfect_timing_refs = [
            ref
            for requirement in grade_by_name.get("perfect", {}).get("requirements", [])
            if requirement["type"] == "signed_timing_error"
            for ref in requirement["parameter_refs"]
        ]
        success_timing_refs = [
            ref
            for requirement in grade_by_name.get("success", {}).get("requirements", [])
            if requirement["type"] == "signed_timing_error"
            for ref in requirement["parameter_refs"]
        ]
        if perfect_timing_refs and success_timing_refs:
            perfect_value = parameter_values.get(perfect_timing_refs[0])
            success_value = parameter_values.get(success_timing_refs[0])
            if perfect_value is not None and success_value is not None and perfect_value > success_value:
                errors.append(issue("E_GRADE_NESTING", f"{cue_path}/judgements", "perfect 的时机容差不得宽于基础 success。"))

    for event_index, event in enumerate(root["feedback_contract"]["events"]):
        references.append((f"/feedback_contract/events/{event_index}/start_latency_param", event["start_latency_param"]))
    feedback_events = [event["on"] for event in root["feedback_contract"]["events"]]
    if len(feedback_events) != len(set(feedback_events)):
        errors.append(issue("E_FEEDBACK_EVENT_DUPLICATE", "/feedback_contract/events", "每个逻辑结果事件只能有一份反馈 recipe。"))
    feedback_event_set = set(feedback_events)
    for cue_index, cue in enumerate(root["mechanics"]["cue_nodes"]):
        for grade in ("perfect", "success", "miss"):
            emitted_events = {
                operation["event"]
                for operation in cue["effects"][grade]
                if operation["op"] == "emit"
            }
            if not emitted_events & feedback_event_set:
                errors.append(
                    issue(
                        "E_FEEDBACK_EVENT",
                        f"/mechanics/cue_nodes/{cue_index}/effects/{grade}",
                        "每种 verdict 至少要 emit 一个具有反馈 recipe 的逻辑事件；额外的流程事件可以不触发表现。",
                    )
                )

    for phase_index, phase in enumerate(root["difficulty"]["phases"]):
        for pattern_index, pattern_id in enumerate(phase["pattern_ids"]):
            if pattern_id not in pattern_ids:
                errors.append(issue("E_PATTERN_REF", f"/difficulty/phases/{phase_index}/pattern_ids/{pattern_index}", "阶段引用了不存在的 action pattern。"))
        for reference_index, value in enumerate(phase["parameter_refs"]):
            references.append((f"/difficulty/phases/{phase_index}/parameter_refs/{reference_index}", value))

    climax = root["fun_contract"]["climax"]
    for pattern_index, pattern_id in enumerate(climax["mastered_pattern_ids"]):
        if pattern_id not in pattern_ids:
            errors.append(issue("E_PATTERN_REF", f"/fun_contract/climax/mastered_pattern_ids/{pattern_index}", "高潮引用了不存在的 action pattern。"))

    for path, parameter_id in references:
        if parameter_id not in parameter_ids:
            errors.append(issue("E_PARAMETER_REF", path, "引用了不存在的校准参数。"))

    decision_status = root["decision_status"]
    open_decisions = decision_status["open"]
    decision_sets = {
        name: set(decision_status[name])
        for name in ("open", "defaulted", "locked")
    }
    for left, right in (("open", "defaulted"), ("open", "locked"), ("defaulted", "locked")):
        overlap = decision_sets[left] & decision_sets[right]
        if overlap:
            errors.append(issue("E_DECISION_STATUS", "/decision_status", f"{left} 与 {right} 不能重复登记同一决策：{sorted(overlap)}。"))
    if open_parameter_ids and not open_decisions:
        errors.append(issue("E_OPEN_DECISION", "/decision_status/open", "存在 open 校准参数时必须登记未决策项。"))
    if require_ready:
        if open_decisions:
            errors.append(issue("E_NOT_READY", "/decision_status/open", "交给 coder 前 decision_status.open 必须为空。"))
        if open_parameter_ids:
            errors.append(issue("E_NOT_READY", "/calibration_contract/parameters", "交给 coder 前所有校准参数必须 measured 或 inherited。"))
        placeholder_pattern = re.compile(r"\{[^{}]+\}")

        def walk_placeholders(value: Any, path: str = "") -> None:
            if isinstance(value, str) and placeholder_pattern.search(value):
                errors.append(issue("E_PLACEHOLDER", path or "/", "ready 规格不能保留未解析的模板占位符。"))
            elif isinstance(value, dict):
                for key, child in value.items():
                    walk_placeholders(child, f"{path}/{key}")
            elif isinstance(value, list):
                for index, child in enumerate(value):
                    walk_placeholders(child, f"{path}/{index}")

        walk_placeholders(root)
        if root["target"]["scope"] == "standalone" and (
            climax["applicable"] is not True
            or climax["numeric_only"] is not False
            or climax["uses_mastered_patterns"] is not True
            or not climax["mastered_pattern_ids"]
        ):
            errors.append(issue("E_CLIMAX", "/fun_contract/climax", "standalone 高潮必须组合已教学 action pattern，不能只有数值变化。"))

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", help="Authoring Spec JSON")
    parser.add_argument("--schema", help="Schema 路径；默认使用 Skill fallback Schema")
    parser.add_argument("--require-ready", action="store_true", help="同时要求已完成校准、可交给 coder")
    args = parser.parse_args()

    spec_path = Path(args.spec)
    schema_path = Path(args.schema) if args.schema else Path(__file__).resolve().parent.parent / "references" / "authoring.schema.json"
    try:
        root = json.loads(spec_path.read_text(encoding="utf-8"))
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "errors": [issue("E_READ", "/", str(exc))]}, ensure_ascii=False, indent=2))
        return 1

    structural_errors = validate_authoring(root, schema, require_ready=False)
    ready_errors = validate_authoring(root, schema, require_ready=True)
    errors = ready_errors if args.require_ready else structural_errors
    print(json.dumps({"valid": not errors, "ready": not ready_errors, "errors": errors}, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
