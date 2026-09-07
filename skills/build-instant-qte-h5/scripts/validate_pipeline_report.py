#!/usr/bin/env python3
"""校验 build-instant-qte-h5 的报告结构、跨字段语义与可选产物完整性。"""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import zlib
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlsplit

from artifact_tools import sha256_directory, sha256_file, verify_archive_matches_build
from check_h5_delivery import check as check_h5_delivery
from schema_subset import SchemaError, validate_schema


FULL_STAGES = {"author", "implement", "static_check", "browser_test", "deliver"}
FULL_HARD_GATES = {
    "h_boot",
    "h_flow",
    "h_input",
    "h_action_meaning",
    "h_success",
    "h_miss",
    "h_resolve_once",
    "h_recovery",
    "h_retry",
    "h_console",
    "h_mobile",
    "h_reload",
    "h_archive",
}
FULL_SOFT_GATES = {
    "s_first_action_clarity",
    "s_telegraph",
    "s_action_feel",
    "s_phase_variety",
    "s_climax",
    "s_feedback",
    "s_failure_trace",
    "s_difficulty",
    "s_hud",
    "s_accessibility",
    "s_replay",
}
MODE_STAGES = {
    "full_run": FULL_STAGES,
    "author": {"author"},
    "implement": {"implement", "static_check"},
    "verify": {"static_check", "browser_test"},
}
MODE_RECEIPTS = {
    "full_run": {"author", "implement", "verify"},
    "author": {"author"},
    "implement": {"implement"},
    "verify": {"verify"},
}
MODE_ARTIFACTS = {
    "full_run": {"spec", "schema", "build_dir", "entrypoint", "archive", "report"},
    "author": {"spec", "schema", "report"},
    "implement": {"spec", "schema", "build_dir", "entrypoint", "report"},
    "verify": {"spec", "schema", "build_dir", "entrypoint", "report"},
}
BUILD_MODES = {"full_run", "implement", "verify"}
BROWSER_MODES = {"full_run", "verify"}
STATIC_MODES = {"full_run", "implement", "verify"}
MODE_HARD_GATES = {
    "full_run": FULL_HARD_GATES,
    "verify": FULL_HARD_GATES - {"h_archive"},
}
IMAGE_SUFFIXES = {".png"}


class Report:
    def __init__(self) -> None:
        self.errors: list[dict[str, str]] = []
        self.warnings: list[dict[str, str]] = []
        self._seen: set[tuple[str, str, str]] = set()

    def _append(self, target: list[dict[str, str]], code: str, path: str, message: str) -> None:
        key = (code, path, message)
        if key not in self._seen:
            self._seen.add(key)
            target.append({"code": code, "path": path, "message": message})

    def error(self, code: str, path: str, message: str) -> None:
        self._append(self.errors, code, path, message)

    def warning(self, code: str, path: str, message: str) -> None:
        self._append(self.warnings, code, path, message)


def read_json(path: Path | None) -> Any:
    if path is None:
        return json.load(sys.stdin)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def index_by_id(items: list[dict[str, Any]], path: str, report: Report) -> dict[str, tuple[int, dict[str, Any]]]:
    indexed: dict[str, tuple[int, dict[str, Any]]] = {}
    for index, item in enumerate(items):
        item_id = item["id"]
        if item_id in indexed:
            report.error("E_ID_DUPLICATE", f"{path}/{index}/id", "ID 必须唯一。")
        else:
            indexed[item_id] = (index, item)
    return indexed


def evidence_arrays(root: dict[str, Any]) -> Iterable[tuple[str, list[str]]]:
    yield "/static_check/evidence", root["static_check"]["evidence"]
    yield "/test_environment/evidence", root["test_environment"]["evidence"]
    for name, receipt in root["receipts"].items():
        yield f"/receipts/{name}/evidence", receipt["evidence"]
    for group in ("stages", "hard_gates", "soft_gates", "issues"):
        for index, item in enumerate(root[group]):
            yield f"/{group}/{index}/evidence", item["evidence"]
    design = root.get("design_validation")
    if isinstance(design, dict):
        yield "/design_validation/qa_replay_evidence", design["qa_replay_evidence"]
        for index, phase in enumerate(design["phase_diffs"]):
            yield f"/design_validation/phase_diffs/{index}/evidence", phase["evidence"]
        yield "/design_validation/reachability/evidence", design["reachability"]["evidence"]
        outcome_evidence = design["feedback"]["outcome_evidence"]
        yield "/design_validation/feedback/outcome_evidence", list(outcome_evidence.values())
        yield "/design_validation/feedback/cleanup_evidence", [design["feedback"]["cleanup_evidence"]]
        yield "/design_validation/feedback/reduced_motion_evidence", [design["feedback"]["reduced_motion_evidence"]]
    play = root.get("play_validation")
    if isinstance(play, dict):
        for index, pattern in enumerate(play["action_patterns"]):
            yield f"/play_validation/action_patterns/{index}/evidence", pattern["evidence"]
        anti = play["anti_autoplay"]
        yield "/play_validation/anti_autoplay/evidence", anti["evidence"]
        for index, trial in enumerate(anti["trials"]):
            yield f"/play_validation/anti_autoplay/trials/{index}/evidence", trial["evidence"]
        yield "/play_validation/anti_autoplay/position_trace/evidence", anti["position_trace"]["evidence"]
        for index, phase in enumerate(play["phase_fingerprints"]):
            yield f"/play_validation/phase_fingerprints/{index}/evidence", phase["evidence"]
        yield "/play_validation/climax/evidence", play["climax"]["evidence"]
        yield "/play_validation/replay/evidence", play["replay"]["evidence"]
        for index, observation in enumerate(play["playtest_observations"]):
            yield f"/play_validation/playtest_observations/{index}/evidence", observation["evidence"]


def require_registered_evidence(root: dict[str, Any], report: Report) -> None:
    registered = set(root["artifacts"]["evidence"])
    for path, values in evidence_arrays(root):
        for index, value in enumerate(values):
            if value not in registered:
                report.error("E_EVIDENCE_UNREGISTERED", f"{path}/{index}", "证据必须先登记在 artifacts.evidence。")


def require_nonempty_evidence(item: dict[str, Any], path: str, report: Report) -> None:
    if not item["evidence"]:
        report.error("E_EVIDENCE_EMPTY", f"{path}/evidence", "passed、failed 或 blocked 项必须附带证据。")


def validate_semantics(root: dict[str, Any]) -> Report:
    report = Report()
    mode = root["run_mode"]
    final_status = root["final_status"]
    control = root["control"]
    contract = root["contract"]
    artifacts = root["artifacts"]
    receipts = root["receipts"]
    stages = index_by_id(root["stages"], "/stages", report)
    hard_gates = index_by_id(root["hard_gates"], "/hard_gates", report)
    soft_gates = index_by_id(root["soft_gates"], "/soft_gates", report)
    issues = root["issues"]
    spec_hash = control["spec_hash"]
    schema_hash = control["schema_hash"]
    build_hash = control["build_hash"]

    require_registered_evidence(root, report)

    for index, stage in enumerate(root["stages"]):
        if stage["status"] in {"passed", "failed", "blocked"}:
            if stage["attempts"] < 1:
                report.error("E_STAGE_ATTEMPT", f"/stages/{index}/attempts", "已执行阶段的 attempts 必须至少为 1。")
            require_nonempty_evidence(stage, f"/stages/{index}", report)

    for name, receipt in receipts.items():
        if receipt["status"] in {"passed", "failed", "blocked"}:
            require_nonempty_evidence(receipt, f"/receipts/{name}", report)
        if receipt["status"] == "passed":
            if receipt["schema_hash"] != schema_hash:
                report.error("E_RECEIPT_SCHEMA", f"/receipts/{name}/schema_hash", "阶段凭证与当前 Schema 摘要不一致。")
            if receipt["spec_hash"] != spec_hash:
                report.error("E_RECEIPT_SPEC", f"/receipts/{name}/spec_hash", "阶段凭证与当前规格摘要不一致。")
            if name in {"implement", "verify"} and receipt["build_hash"] != build_hash:
                report.error("E_RECEIPT_BUILD", f"/receipts/{name}/build_hash", "阶段凭证与当前构建摘要不一致。")

    for group_name in ("hard_gates", "soft_gates"):
        for index, gate in enumerate(root[group_name]):
            if gate["status"] in {"passed", "failed", "blocked"}:
                require_nonempty_evidence(gate, f"/{group_name}/{index}", report)

    for index, issue in enumerate(issues):
        if issue["severity"] in {"blocker", "error"} and issue["status"] == "accepted":
            report.error("E_ISSUE_ACCEPTED", f"/issues/{index}/status", "blocker 或 error 不能被直接接受。")
        if issue["status"] in {"open", "fixed", "accepted"}:
            require_nonempty_evidence(issue, f"/issues/{index}", report)

    if final_status in {"failed", "blocked"}:
        if final_status == "blocked" and root["blocked_reason"] is None:
            report.error("E_BLOCKED_REASON", "/blocked_reason", "blocked 报告必须说明阻断原因。")
        if not any(
            issue["severity"] in {"blocker", "error"} and issue["status"] == "open"
            for issue in issues
        ):
            report.error("E_FAILURE_ISSUE", "/issues", "failed 或 blocked 报告必须保留至少一个 open blocker/error。")

    if final_status == "passed":
        if root["blocked_reason"] is not None:
            report.error("E_BLOCKED_REASON", "/blocked_reason", "passed 报告的 blocked_reason 必须为 null。")
        if contract["creative_schema_preserved"] is not True:
            report.error("E_SCHEMA_CHANGED", "/contract/creative_schema_preserved", "通过状态下必须保持创意 Schema。")
        if contract["coder_interface_modified"] is not False:
            report.error("E_CODER_INTERFACE", "/contract/coder_interface_modified", "通过状态下不得修改 coder 接口。")
        if spec_hash is None:
            report.error("E_SPEC_HASH", "/control/spec_hash", "通过状态必须记录冻结规格摘要。")
        if schema_hash is None:
            report.error("E_SCHEMA_HASH", "/control/schema_hash", "通过状态必须记录调用方或 fallback Schema 摘要。")
        if mode in BUILD_MODES and build_hash is None:
            report.error("E_BUILD_HASH", "/control/build_hash", "该模式通过时必须记录构建摘要。")
        for key in sorted(MODE_ARTIFACTS[mode]):
            if artifacts[key] is None:
                report.error("E_ARTIFACT", f"/artifacts/{key}", "该模式通过时必须提供此产物。")

        for stage_id in sorted(MODE_STAGES[mode]):
            indexed = stages.get(stage_id)
            if indexed is None:
                report.error("E_STAGE_MISSING", "/stages", f"缺少必需阶段：{stage_id}。")
            elif indexed[1]["status"] != "passed":
                report.error("E_STAGE_NOT_PASSED", f"/stages/{indexed[0]}/status", "最终通过前，该阶段必须通过。")

        for receipt_name in sorted(MODE_RECEIPTS[mode]):
            if receipts[receipt_name]["status"] != "passed":
                report.error("E_RECEIPT", f"/receipts/{receipt_name}/status", "该模式通过需要匹配的阶段凭证。")

        if mode in STATIC_MODES:
            static_check = root["static_check"]
            if static_check["status"] != "passed" or static_check["errors"]:
                report.error("E_STATIC_CHECK", "/static_check/status", "该模式通过需要无 error 的静态检查。")
            require_nonempty_evidence(static_check, "/static_check", report)

        if mode in BROWSER_MODES:
            environment = root["test_environment"]
            if environment["status"] != "passed":
                report.error("E_BROWSER_RUN", "/test_environment/status", "该模式通过需要真实浏览器运行记录。")
            for key in ("tested_at", "base_url", "browser", "browser_version", "viewport", "has_touch", "device_scale_factor"):
                if environment[key] is None:
                    report.error("E_BROWSER_ENV", f"/test_environment/{key}", "浏览器通过时必须记录该环境字段。")
            if environment["has_touch"] is not True:
                report.error("E_TOUCH_ENV", "/test_environment/has_touch", "移动端验收必须启用触摸语义，不能只缩放视口。")
            viewport = environment["viewport"]
            if viewport is not None and (viewport["width"] != 390 or viewport["height"] != 844):
                report.error("E_VIEWPORT_ENV", "/test_environment/viewport", "至少要记录一次 390×844 的移动视口验收。")
            require_nonempty_evidence(environment, "/test_environment", report)

            for gate_id in sorted(MODE_HARD_GATES[mode]):
                indexed = hard_gates.get(gate_id)
                if indexed is None:
                    report.error("E_GATE_MISSING", "/hard_gates", f"缺少必测硬门槛：{gate_id}。")
                elif indexed[1]["status"] != "passed":
                    report.error("E_GATE_NOT_PASSED", f"/hard_gates/{indexed[0]}/status", "最终通过前，硬门槛必须通过。")
            for gate_id in sorted(FULL_SOFT_GATES):
                if gate_id not in soft_gates:
                    report.error("E_SOFT_GATE_MISSING", "/soft_gates", f"缺少必评软门槛：{gate_id}。")

            design = root.get("design_validation")
            if not isinstance(design, dict):
                report.error("E_DESIGN_VALIDATION", "/design_validation", "浏览器模式通过必须提供结构化关卡、数值与手感验证。")
            else:
                seed = design["qa_seed"]
                seed_status = design["qa_replay_status"]
                if design["scope"] == "standalone" and not design["phase_diffs"]:
                    report.error("E_PHASE_DIFF", "/design_validation/phase_diffs", "standalone 浏览器验收必须记录至少一个相邻阶段参数 diff。")
                if seed_status == "passed" and seed is None:
                    report.error("E_SEED_EVIDENCE", "/design_validation/qa_seed", "QA seed 重放通过时必须记录 QA seed。")
                if seed_status == "not_applicable" and seed is not None:
                    report.error("E_SEED_EVIDENCE", "/design_validation/qa_seed", "无随机性时 qa_seed 应为 null。")
                feedback_gate = soft_gates.get("s_feedback")
                if feedback_gate is not None:
                    values = feedback_gate[1]["evidence"]
                    required_feedback = set(design["feedback"]["outcome_evidence"].values())
                    required_feedback.add(design["feedback"]["cleanup_evidence"])
                    if not required_feedback <= set(values):
                        report.error(
                            "E_FEEDBACK_EVIDENCE",
                            f"/soft_gates/{feedback_gate[0]}/evidence",
                            "S_FEEDBACK 通过至少需要 perfect/success/miss 三份视觉证据和一份效果清理记录。",
                        )

                difficulty_gate = soft_gates.get("s_difficulty")
                if difficulty_gate is not None:
                    difficulty_evidence = set(difficulty_gate[1]["evidence"])
                    required_design_evidence = set(design["reachability"]["evidence"])
                    required_design_evidence.update(design["qa_replay_evidence"])
                    for phase in design["phase_diffs"]:
                        required_design_evidence.update(phase["evidence"])
                    if not required_design_evidence <= difficulty_evidence:
                        report.error(
                            "E_DIFFICULTY_EVIDENCE",
                            f"/soft_gates/{difficulty_gate[0]}/evidence",
                            "S_DIFFICULTY 必须引用逐阶段参数 diff 与可达性证据。",
                        )

                accessibility_gate = soft_gates.get("s_accessibility")
                if accessibility_gate is not None:
                    reduced_evidence = design["feedback"]["reduced_motion_evidence"]
                    if reduced_evidence not in accessibility_gate[1]["evidence"]:
                        report.error(
                            "E_ACCESSIBILITY_EVIDENCE",
                            f"/soft_gates/{accessibility_gate[0]}/evidence",
                            "S_ACCESSIBILITY 必须引用 reduced-motion 实跑证据。",
                        )

            play = root.get("play_validation")
            if not isinstance(play, dict):
                report.error("E_PLAY_VALIDATION", "/play_validation", "浏览器模式通过必须提供结构化操作感与可玩性验证。")
            else:
                pattern_index = index_by_id(play["action_patterns"], "/play_validation/action_patterns", report)
                pattern_ids = set(pattern_index)
                anti = play["anti_autoplay"]
                if anti["passive_can_earn_highest_grade"] or anti["preposition_can_earn_highest_grade"] or anti["random_input_can_reliably_complete"]:
                    report.error("E_ACTION_AUTOPLAY", "/play_validation/anti_autoplay", "无输入、提前占位或随机输入不能取得最高评级或稳定完成。")
                if anti["spatial_pressure_uses_instant_reposition"]:
                    report.error("E_INSTANT_REPOSITION", "/play_validation/anti_autoplay/spatial_pressure_uses_instant_reposition", "空间压力不能用瞬时改写权威位置伪造。")

                required_policies = {"passive", "preposition", "random"}
                seen_policies: set[str] = set()
                for trial_index, trial in enumerate(anti["trials"]):
                    policy = trial["policy"]
                    if policy in seen_policies:
                        report.error(
                            "E_COUNTERFACTUAL_POLICY",
                            f"/play_validation/anti_autoplay/trials/{trial_index}/policy",
                            "每种反例策略只能记录一组聚合试跑。",
                        )
                    seen_policies.add(policy)
                    if trial["completions"] > trial["attempts"] or trial["highest_grade_count"] > trial["attempts"]:
                        report.error(
                            "E_COUNTERFACTUAL_COUNTS",
                            f"/play_validation/anti_autoplay/trials/{trial_index}",
                            "完成数与最高评级数不能大于实际试跑数。",
                        )
                    if trial["reliable_completion"] or trial["highest_grade_count"] != 0:
                        report.error(
                            "E_ACTION_AUTOPLAY_TRIAL",
                            f"/play_validation/anti_autoplay/trials/{trial_index}",
                            "反例策略实跑不能稳定完成，也不能取得最高评级。",
                        )
                if seen_policies != required_policies:
                    report.error(
                        "E_COUNTERFACTUAL_POLICY",
                        "/play_validation/anti_autoplay/trials",
                        "必须分别记录 passive、preposition 与 random 三种反例策略。",
                    )

                position_trace = anti["position_trace"]
                if position_trace["applicable"]:
                    if not isinstance(position_trace["input_path_hash"], str) or not isinstance(position_trace["authority_trace_hash"], str):
                        report.error(
                            "E_POSITION_TRACE",
                            "/play_validation/anti_autoplay/position_trace",
                            "空间控制适用时必须同时记录输入路径与权威位置轨迹摘要。",
                        )
                    if position_trace["direct_position_writes"] != 0 or position_trace["all_steps_explained_by_control_model"] is not True:
                        report.error(
                            "E_INSTANT_REPOSITION",
                            "/play_validation/anti_autoplay/position_trace",
                            "权威位置必须由声明的控制模型逐步解释，不能直接瞬移改写。",
                        )
                elif position_trace["input_path_hash"] is not None or position_trace["authority_trace_hash"] is not None:
                    report.error(
                        "E_POSITION_TRACE",
                        "/play_validation/anti_autoplay/position_trace",
                        "空间轨迹不适用时路径摘要应为 null，避免伪造无意义证据。",
                    )

                for phase_index, phase in enumerate(play["phase_fingerprints"]):
                    unknown_patterns = set(phase["pattern_ids"]) - pattern_ids
                    if unknown_patterns:
                        report.error(
                            "E_PATTERN_REFERENCE",
                            f"/play_validation/phase_fingerprints/{phase_index}/pattern_ids",
                            f"阶段引用了不存在的 action pattern：{sorted(unknown_patterns)}。",
                        )
                    if phase["numeric_only_change"]:
                        report.error(
                            "E_NUMERIC_ONLY_PHASE",
                            f"/play_validation/phase_fingerprints/{phase_index}/numeric_only_change",
                            "阶段必须改变玩家问题、动作组合、选择/风险或恢复职责，不能只有数值变化。",
                        )

                scope = design.get("scope") if isinstance(design, dict) else None
                climax = play["climax"]
                unknown_climax_patterns = set(climax["mastered_pattern_ids"]) - pattern_ids
                if unknown_climax_patterns:
                    report.error(
                        "E_PATTERN_REFERENCE",
                        "/play_validation/climax/mastered_pattern_ids",
                        f"高潮引用了不存在的 action pattern：{sorted(unknown_climax_patterns)}。",
                    )
                if scope == "standalone" and (
                    climax["applicable"] is not True
                    or climax["numeric_only"] is not False
                    or climax["uses_mastered_patterns"] is not True
                    or not climax["mastered_pattern_ids"]
                ):
                    report.error("E_CLIMAX_COMPOSITION", "/play_validation/climax", "standalone 高潮必须组合已教学 pattern 并改变玩家行为，不能只有数值加速。")
                if climax["applicable"]:
                    climax_indices = [
                        phase_index
                        for phase_index, phase in enumerate(play["phase_fingerprints"])
                        if phase["role"] == "climax"
                    ]
                    if not climax_indices:
                        report.error("E_CLIMAX_COMPOSITION", "/play_validation/phase_fingerprints", "声明高潮适用时必须有 climax 阶段 fingerprint。")
                    else:
                        first_climax = min(climax_indices)
                        taught_before_climax = {
                            pattern_id
                            for phase in play["phase_fingerprints"][:first_climax]
                            for pattern_id in phase["pattern_ids"]
                        }
                        not_taught = set(climax["mastered_pattern_ids"]) - taught_before_climax
                        if not_taught:
                            report.error(
                                "E_CLIMAX_TEACHING",
                                "/play_validation/climax/mastered_pattern_ids",
                                f"高潮 pattern 必须先在高潮前阶段出现并完成教学：{sorted(not_taught)}。",
                            )

                human_observations = [
                    observation
                    for observation in play["playtest_observations"]
                    if observation["source"] == "human"
                ]
                action_feel_gate = soft_gates.get("s_action_feel")
                if action_feel_gate is not None and action_feel_gate[1]["status"] == "passed" and not human_observations:
                    report.error(
                        "E_HUMAN_PLAYTEST",
                        "/play_validation/playtest_observations",
                        "S_ACTION_FEEL 只有真人连续试玩观察时才能 passed；只有 Agent 观察时应标为 review 并关联 issue。",
                    )

                evidence_requirements = {
                    "h_action_meaning": set(anti["evidence"])
                    | {raw for trial in anti["trials"] for raw in trial["evidence"]}
                    | set(position_trace["evidence"]),
                    "s_action_feel": {
                        raw
                        for pattern in play["action_patterns"]
                        for raw in pattern["evidence"]
                    }
                    | {
                        raw
                        for observation in play["playtest_observations"]
                        for raw in observation["evidence"]
                    },
                    "s_phase_variety": {
                        raw
                        for phase in play["phase_fingerprints"]
                        for raw in phase["evidence"]
                    },
                    "s_climax": set(climax["evidence"]),
                    "s_replay": set(play["replay"]["evidence"]),
                }
                for gate_id, required_evidence in evidence_requirements.items():
                    indexed = hard_gates.get(gate_id) if gate_id.startswith("h_") else soft_gates.get(gate_id)
                    if indexed is not None and not required_evidence <= set(indexed[1]["evidence"]):
                        group = "hard_gates" if gate_id.startswith("h_") else "soft_gates"
                        report.error(
                            "E_PLAY_GATE_EVIDENCE",
                            f"/{group}/{indexed[0]}/evidence",
                            f"{gate_id} 必须引用 play_validation 对应的结构化证据。",
                        )

        if any(
            issue["severity"] in {"blocker", "error"} and issue["status"] == "open"
            for issue in issues
        ):
            report.error("E_OPEN_ISSUE", "/issues", "通过状态下不能存在未解决的 blocker 或 error。")

        for gate_id, (index, gate) in hard_gates.items():
            if gate["status"] != "passed":
                report.error("E_GATE_NOT_PASSED", f"/hard_gates/{index}/status", f"已声明硬门槛 {gate_id} 未通过。")

    issues_by_gate = {issue["gate_id"] for issue in issues if issue["gate_id"] is not None}
    for gate_id, (index, gate) in soft_gates.items():
        if gate["status"] != "passed":
            report.warning("W_SOFT_PENDING", f"/soft_gates/{index}/status", f"软门槛 {gate_id} 未通过或仍需复核。")
            if gate_id not in issues_by_gate:
                report.error("E_SOFT_ISSUE", f"/soft_gates/{index}", "未通过的软门槛必须关联一个 issue。")

    static_check = root["static_check"]
    warning_reviews = static_check["warning_reviews"]
    issues_by_id = {issue["id"]: issue for issue in issues}
    mapped_indices: set[int] = set()
    for review_index, review in enumerate(warning_reviews):
        warning_index = review["warning_index"]
        issue = issues_by_id.get(review["issue_id"])
        if warning_index >= len(static_check["warnings"]):
            report.error("E_STATIC_WARNING_INDEX", f"/static_check/warning_reviews/{review_index}/warning_index", "warning_index 越出 warnings 数组。")
            continue
        if review["warning_text"] != static_check["warnings"][warning_index]:
            report.error("E_STATIC_WARNING_TEXT", f"/static_check/warning_reviews/{review_index}/warning_text", "warning_text 必须逐字匹配被复核的静态 warning。")
        if warning_index in mapped_indices:
            report.error("E_STATIC_WARNING_DUPLICATE", f"/static_check/warning_reviews/{review_index}/warning_index", "每条静态 warning 只能映射一次。")
        mapped_indices.add(warning_index)
        if issue is None or issue["severity"] not in {"warning", "review"} or not issue["evidence"]:
            report.error("E_STATIC_WARNING_ISSUE", f"/static_check/warning_reviews/{review_index}/issue_id", "映射目标必须是存在且带证据的 warning/review issue。")
    if static_check["warnings"]:
        if mapped_indices != set(range(len(static_check["warnings"]))):
            report.error("E_STATIC_WARNING_UNTRACKED", "/static_check/warning_reviews", "每条静态 warning 都必须逐条映射到带证据的 warning/review issue。")
        report.warning("W_STATIC_WARNING", "/static_check/warnings", "静态警告已进入 issue 复核，不应被静默忽略。")
    elif warning_reviews:
        report.error("E_STATIC_WARNING_INDEX", "/static_check/warning_reviews", "没有静态 warning 时 warning_reviews 必须为空。")

    return report


def is_descendant(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def resolve_artifact(root: Path, raw: str, field_path: str, report: Report) -> Path | None:
    split = urlsplit(raw)
    candidate_raw = Path(raw)
    if split.scheme or split.netloc or candidate_raw.is_absolute() or ".." in candidate_raw.parts:
        report.error("E_ARTIFACT_PATH", field_path, "产物路径必须是 artifact root 内不含 .. 的相对路径。")
        return None
    candidate = (root / candidate_raw).resolve()
    if not is_descendant(candidate, root):
        report.error("E_ARTIFACT_ESCAPE", field_path, "产物路径越出 artifact root。")
        return None
    return candidate


def visual_file_is_decodable(path: Path) -> bool:
    """做无依赖图片结构检查，拒绝只伪造扩展名、文件头或尺寸的证据。"""
    try:
        data = path.read_bytes()
    except OSError:
        return False
    if len(data) > 50 * 1024 * 1024:
        return False
    suffix = path.suffix.lower()
    if suffix == ".png":
        if len(data) < 45 or data[:8] != b"\x89PNG\r\n\x1a\n":
            return False
        offset = 8
        seen_header = False
        seen_data = False
        seen_end = False
        compressed = bytearray()
        image_meta: tuple[int, int, int, int] | None = None
        while offset + 12 <= len(data):
            length = struct.unpack(">I", data[offset : offset + 4])[0]
            chunk_end = offset + 12 + length
            if chunk_end > len(data):
                return False
            chunk_type = data[offset + 4 : offset + 8]
            chunk_data = data[offset + 8 : offset + 8 + length]
            expected_crc = struct.unpack(">I", data[offset + 8 + length : chunk_end])[0]
            if zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF != expected_crc:
                return False
            if chunk_type == b"IHDR":
                if seen_header or offset != 8 or length != 13:
                    return False
                width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(">IIBBBBB", chunk_data)
                if width <= 0 or height <= 0 or width > 8192 or height > 8192 or compression != 0 or filter_method != 0 or interlace != 0:
                    return False
                if color_type not in {0, 2, 4, 6}:
                    return False
                valid_depths = {0: {1, 2, 4, 8, 16}, 2: {8, 16}, 4: {8, 16}, 6: {8, 16}}
                if bit_depth not in valid_depths[color_type]:
                    return False
                image_meta = (width, height, bit_depth, color_type)
                seen_header = True
            elif chunk_type == b"IDAT":
                if not seen_header:
                    return False
                seen_data = True
                compressed.extend(chunk_data)
            elif chunk_type == b"IEND":
                if length != 0:
                    return False
                seen_end = True
                offset = chunk_end
                break
            offset = chunk_end
        if not (seen_header and seen_data and seen_end) or offset != len(data):
            return False
        if image_meta is None:
            return False
        width, height, bit_depth, color_type = image_meta
        samples_per_pixel = {0: 1, 2: 3, 4: 2, 6: 4}[color_type]
        row_bytes = (width * samples_per_pixel * bit_depth + 7) // 8
        stride = row_bytes + 1
        expected_size = height * stride
        if expected_size > 128 * 1024 * 1024:
            return False
        try:
            inflater = zlib.decompressobj()
            pixels = inflater.decompress(bytes(compressed), expected_size + 1)
            if len(pixels) > expected_size or inflater.unconsumed_tail:
                return False
            pixels += inflater.flush()
        except zlib.error:
            return False
        if not inflater.eof or inflater.unused_data or inflater.unconsumed_tail:
            return False
        if len(pixels) != expected_size:
            return False
        return all(pixels[row * stride] <= 4 for row in range(height))
    return False


def png_dimensions(path: Path) -> tuple[int, int] | None:
    """读取已解码 PNG 的 IHDR 尺寸；调用方仍应先执行完整结构检查。"""
    try:
        with path.open("rb") as handle:
            header = handle.read(24)
    except OSError:
        return None
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", header[16:24])
    return (width, height) if width > 0 and height > 0 else None


def read_json_evidence(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def validate_artifacts(
    root: dict[str, Any],
    artifact_root: Path,
    report_path: Path | None,
) -> Report:
    report = Report()
    artifact_root = artifact_root.resolve()
    if not artifact_root.is_dir():
        report.error("E_ARTIFACT_ROOT", str(artifact_root), "artifact root 不存在或不是目录。")
        return report

    values = root["artifacts"]
    resolved: dict[str, Path | None] = {}
    for key in ("spec", "schema", "build_dir", "entrypoint", "archive", "report"):
        raw = values[key]
        resolved[key] = None if raw is None else resolve_artifact(artifact_root, raw, f"/artifacts/{key}", report)

    evidence_paths: list[Path] = []
    evidence_by_name: dict[str, Path] = {}
    for index, raw in enumerate(values["evidence"]):
        path = resolve_artifact(artifact_root, raw, f"/artifacts/evidence/{index}", report)
        if path is not None:
            evidence_paths.append(path)
            evidence_by_name[raw] = path
            if not path.is_file():
                report.error("E_EVIDENCE_FILE", f"/artifacts/evidence/{index}", "证据文件不存在。")

    for key in ("spec", "schema", "entrypoint", "archive", "report"):
        path = resolved[key]
        if path is not None and not path.is_file():
            report.error("E_ARTIFACT_FILE", f"/artifacts/{key}", "声明的产物文件不存在。")
    build_dir = resolved["build_dir"]
    if build_dir is not None and not build_dir.is_dir():
        report.error("E_BUILD_DIR", "/artifacts/build_dir", "声明的构建目录不存在。")

    if report_path is not None and resolved["report"] is not None and resolved["report"] != report_path.resolve():
        report.error("E_REPORT_PATH", "/artifacts/report", "报告声明路径与当前被校验文件不一致。")

    entrypoint = resolved["entrypoint"]
    if build_dir is not None and entrypoint is not None and not is_descendant(entrypoint, build_dir):
        report.error("E_ENTRY_OUTSIDE_BUILD", "/artifacts/entrypoint", "入口必须位于 build_dir 内。")

    if build_dir is not None:
        for key in ("spec", "schema", "archive", "report"):
            path = resolved[key]
            if path is not None and is_descendant(path, build_dir):
                report.error("E_HASH_CYCLE", f"/artifacts/{key}", "规范、报告或归档必须位于 build_dir 外，避免构建摘要自引用。")
        for index, path in enumerate(evidence_paths):
            if is_descendant(path, build_dir):
                report.error("E_HASH_CYCLE", f"/artifacts/evidence/{index}", "验收证据必须位于 build_dir 外。")

    spec = resolved["spec"]
    if spec is not None and spec.is_file():
        actual = sha256_file(spec)
        if root["control"]["spec_hash"] != actual:
            report.error("E_SPEC_HASH_MISMATCH", "/control/spec_hash", f"实际规格摘要为 {actual}。")
    schema = resolved["schema"]
    if schema is not None and schema.is_file():
        actual = sha256_file(schema)
        if root["control"]["schema_hash"] != actual:
            report.error("E_SCHEMA_HASH_MISMATCH", "/control/schema_hash", f"实际 Schema 摘要为 {actual}。")
    elif root["control"]["schema_hash"] is not None:
        report.error("E_SCHEMA_ARTIFACT", "/artifacts/schema", "存在 schema_hash 时必须提供可校验的 Schema 文件。")

    if build_dir is not None and build_dir.is_dir():
        try:
            actual = sha256_directory(build_dir)
            if root["control"]["build_hash"] != actual:
                report.error("E_BUILD_HASH_MISMATCH", "/control/build_hash", f"实际构建摘要为 {actual}。")
        except (OSError, ValueError) as exc:
            report.error("E_BUILD_HASH_READ", "/artifacts/build_dir", str(exc))

    archive = resolved["archive"]
    if archive is not None and archive.is_file() and build_dir is not None and build_dir.is_dir():
        for problem in verify_archive_matches_build(archive, build_dir):
            report.error("E_ARCHIVE_CONTENT", "/artifacts/archive", problem)

    json_cache: dict[str, dict[str, Any] | None] = {}

    def evidence_json(raw: str, field_path: str) -> dict[str, Any] | None:
        if raw in json_cache:
            return json_cache[raw]
        path = evidence_by_name.get(raw)
        value = None if path is None or path.suffix.lower() != ".json" else read_json_evidence(path)
        json_cache[raw] = value
        if value is None:
            report.error("E_EVIDENCE_JSON", field_path, f"证据必须是可解析的 JSON 对象：{raw}")
        return value

    expected_spec_hash = root["control"]["spec_hash"]
    expected_build_hash = root["control"]["build_hash"]

    def bound_to_current_run(
        value: dict[str, Any],
        *,
        require_spec: bool = True,
        require_build: bool = True,
    ) -> bool:
        """结构化证据必须绑定当前冻结规格和已校验构建。"""
        return (
            (not require_spec or value.get("spec_hash") == expected_spec_hash)
            and (not require_build or value.get("build_hash") == expected_build_hash)
        )

    static_check = root["static_check"]
    if static_check["status"] == "passed":
        current_static_result = None
        current_static_summary = None
        if (
            build_dir is not None
            and build_dir.is_dir()
            and entrypoint is not None
            and entrypoint.is_file()
            and is_descendant(entrypoint, build_dir)
        ):
            try:
                relative_entry = entrypoint.relative_to(build_dir).as_posix()
                current_static_result, current_static_summary = check_h5_delivery(str(build_dir), relative_entry)
            except (OSError, ValueError) as exc:
                report.error("E_STATIC_RECHECK", "/artifacts/build_dir", f"无法重跑当前构建的静态检查：{exc}")
        if current_static_result is None or current_static_summary is None:
            report.error("E_STATIC_RECHECK", "/static_check", "静态通过时必须能对当前 build_dir 和 entrypoint 重跑检查。")
        elif current_static_result.errors:
            report.error("E_STATIC_RECHECK", "/static_check", "当前构建重跑静态检查仍存在 error，不得复用旧通过证据。")

        static_validated = False
        for index, raw in enumerate(static_check["evidence"]):
            value = evidence_json(raw, f"/static_check/evidence/{index}")
            if value is None or current_static_result is None or current_static_summary is None:
                continue
            source_warnings = value.get("warnings")
            warning_codes_match = isinstance(source_warnings, list) and all(
                isinstance(item, dict)
                and isinstance(item.get("code"), str)
                and any(item["code"] in summary for summary in static_check["warnings"])
                for item in source_warnings
            )
            if (
                value.get("valid") is True
                and value.get("errors") == current_static_result.errors == []
                and source_warnings == current_static_result.warnings
                and warning_codes_match
                and len(source_warnings) == len(static_check["warnings"])
                and value.get("summary") == current_static_summary
            ):
                static_validated = True
        if not static_validated:
            report.error("E_STATIC_EVIDENCE", "/static_check/evidence", "passed 静态检查必须附带与当前 build_dir、entrypoint 及重跑结果完全一致的 check_h5_delivery.py 输出。")

    if root["final_status"] == "passed" and root["run_mode"] in BROWSER_MODES:
        gates = {gate["id"]: gate for gate in root["hard_gates"]}
        environment = root["test_environment"]
        expected_environment = {
            key: environment[key]
            for key in (
                "tested_at",
                "base_url",
                "browser",
                "browser_version",
                "viewport",
                "has_touch",
                "device_scale_factor",
            )
        }
        required_gate_ids = MODE_HARD_GATES[root["run_mode"]]
        soft_gates = {gate["id"]: gate for gate in root["soft_gates"]}
        design_for_manifest = root.get("design_validation")
        design_evidence_names: set[str] = set()
        if isinstance(design_for_manifest, dict):
            design_evidence_names.update(design_for_manifest["qa_replay_evidence"])
            design_evidence_names.update(design_for_manifest["reachability"]["evidence"])
            for phase in design_for_manifest["phase_diffs"]:
                design_evidence_names.update(phase["evidence"])
            feedback_for_manifest = design_for_manifest["feedback"]
            design_evidence_names.update(feedback_for_manifest["outcome_evidence"].values())
            design_evidence_names.add(feedback_for_manifest["cleanup_evidence"])
            design_evidence_names.add(feedback_for_manifest["reduced_motion_evidence"])
        play_for_manifest = root.get("play_validation")
        if isinstance(play_for_manifest, dict):
            for pattern in play_for_manifest["action_patterns"]:
                design_evidence_names.update(pattern["evidence"])
            anti_for_manifest = play_for_manifest["anti_autoplay"]
            design_evidence_names.update(anti_for_manifest["evidence"])
            for trial in anti_for_manifest["trials"]:
                design_evidence_names.update(trial["evidence"])
            design_evidence_names.update(anti_for_manifest["position_trace"]["evidence"])
            for phase in play_for_manifest["phase_fingerprints"]:
                design_evidence_names.update(phase["evidence"])
            design_evidence_names.update(play_for_manifest["climax"]["evidence"])
            design_evidence_names.update(play_for_manifest["replay"]["evidence"])
            for observation in play_for_manifest["playtest_observations"]:
                design_evidence_names.update(observation["evidence"])
        hard_evidence_names = {
            raw
            for gate_id in required_gate_ids
            for raw in gates.get(gate_id, {}).get("evidence", [])
        }
        soft_evidence_names = {
            raw
            for gate in soft_gates.values()
            for raw in gate["evidence"]
        }
        covered_browser_evidence = hard_evidence_names | soft_evidence_names | design_evidence_names
        manifest_names: set[str] = set()
        for raw, path in evidence_by_name.items():
            if path.suffix.lower() != ".json" or not path.is_file():
                continue
            candidate = read_json_evidence(path)
            if candidate is not None and "manifest_version" in candidate:
                manifest_names.add(raw)

        browser_manifest_validated = False
        for index, raw in enumerate(environment["evidence"]):
            value = evidence_json(raw, f"/test_environment/evidence/{index}")
            if value is None or value.get("manifest_version") != "1.0":
                continue
            if (
                value.get("run_id") != root["run_id"]
                or not bound_to_current_run(value)
                or value.get("environment") != expected_environment
            ):
                continue
            gate_results = value.get("gate_results")
            soft_gate_results = value.get("soft_gate_results")
            manifest_design_evidence = value.get("design_evidence")
            evidence_hashes = value.get("evidence_hashes")
            if (
                not isinstance(gate_results, dict)
                or not isinstance(soft_gate_results, dict)
                or not isinstance(manifest_design_evidence, list)
                or not all(isinstance(item, str) for item in manifest_design_evidence)
                or not isinstance(evidence_hashes, dict)
                or set(manifest_design_evidence) != design_evidence_names
                or set(evidence_hashes) != covered_browser_evidence
                or bool(manifest_names & covered_browser_evidence)
            ):
                continue
            candidate_valid = True
            for gate_id in required_gate_ids:
                report_gate = gates.get(gate_id)
                manifest_gate = gate_results.get(gate_id)
                if (
                    not isinstance(report_gate, dict)
                    or report_gate.get("status") != "passed"
                    or not isinstance(manifest_gate, dict)
                    or manifest_gate.get("passed") is not True
                    or manifest_gate.get("evidence") != report_gate.get("evidence")
                    or not report_gate.get("evidence")
                ):
                    candidate_valid = False
                    break
            if not candidate_valid:
                continue
            for gate_id, report_gate in soft_gates.items():
                manifest_gate = soft_gate_results.get(gate_id)
                if (
                    not isinstance(manifest_gate, dict)
                    or manifest_gate.get("status") != report_gate["status"]
                    or manifest_gate.get("evidence") != report_gate["evidence"]
                ):
                    candidate_valid = False
                    break
            if not candidate_valid:
                continue
            for evidence_raw in covered_browser_evidence:
                evidence_path = evidence_by_name.get(evidence_raw)
                expected_hash = evidence_hashes.get(evidence_raw)
                if evidence_path is None or not evidence_path.is_file() or not isinstance(expected_hash, str):
                    candidate_valid = False
                    break
                try:
                    if sha256_file(evidence_path) != expected_hash:
                        candidate_valid = False
                        break
                except OSError:
                    candidate_valid = False
                    break
            if candidate_valid:
                browser_manifest_validated = True
                break
        if not browser_manifest_validated:
            report.error(
                "E_BROWSER_MANIFEST",
                "/test_environment/evidence",
                "浏览器通过必须提供本 run 的 browser-run manifest：绑定当前 spec/build 与完整环境，覆盖硬门禁、软门禁和 design_validation 的证据列表及文件 SHA-256，且任何 manifest 都不得自证或代理门禁。",
            )

        visual_gate_ids = {"h_boot", "h_flow", "h_success", "h_miss", "h_retry", "h_mobile", "h_reload"}
        for gate_id in visual_gate_ids & required_gate_ids:
            gate = gates.get(gate_id)
            if not isinstance(gate, dict) or not any(
                evidence_by_name.get(raw) is not None
                and evidence_by_name[raw].suffix.lower() == ".png"
                and evidence_by_name[raw].is_file()
                and visual_file_is_decodable(evidence_by_name[raw])
                for raw in gate.get("evidence", [])
            ):
                report.error("E_GATE_VISUAL_EVIDENCE", f"/hard_gates/{gate_id}", f"{gate_id} 通过必须引用至少一张可解码 PNG，不能用无关 JSON 代替。")

        assertion_requirements = {
            "h_input": lambda item: (
                type(item.get("pointer_events")) is int
                and item["pointer_events"] >= 1
                and type(item.get("semantic_actions")) is int
                and item["semantic_actions"] >= 1
                and item["semantic_actions"] <= item["pointer_events"]
                and type(item.get("page_scroll_delta")) in {int, float}
                and item.get("page_scroll_delta") == 0
            ),
            "h_resolve_once": lambda item: (
                type(item.get("competing_inputs")) is int
                and item["competing_inputs"] >= 2
                and type(item.get("verdict_commits")) is int
                and item.get("verdict_commits") == 1
                and type(item.get("result_events")) is int
                and item.get("result_events") == 1
            ),
            "h_recovery": lambda item: item.get("success_advanced") is True and item.get("miss_advanced") is True,
        }
        for gate_id, requirement in assertion_requirements.items():
            if gate_id not in required_gate_ids:
                continue
            assertion_validated = False
            gate = gates.get(gate_id)
            if isinstance(gate, dict):
                for index, evidence_raw in enumerate(gate["evidence"]):
                    value = evidence_json(evidence_raw, f"/hard_gates/{gate_id}/evidence/{index}")
                    assertions = None if value is None else value.get("assertions")
                    assertion = assertions.get(gate_id) if isinstance(assertions, dict) else None
                    if (
                        value is not None
                        and value.get("kind") == "browser_assertions"
                        and value.get("run_id") == root["run_id"]
                        and bound_to_current_run(value)
                        and value.get("environment") == expected_environment
                        and isinstance(assertion, dict)
                        and requirement(assertion)
                    ):
                        assertion_validated = True
                        break
            if not assertion_validated:
                report.error("E_BROWSER_ASSERTION", f"/hard_gates/{gate_id}", f"{gate_id} 必须引用绑定本 run/spec/build/环境且包含 gate-specific 计数或布尔结论的 browser_assertions JSON。")

        console_gate = gates.get("h_console")
        if console_gate is not None:
            console_validated = False
            for index, raw in enumerate(console_gate["evidence"]):
                value = evidence_json(raw, f"/hard_gates/h_console/evidence/{index}")
                environment_matches = value is not None and all(
                    value.get(key) == environment[key]
                    for key in (
                        "tested_at",
                        "base_url",
                        "browser",
                        "browser_version",
                        "viewport",
                        "has_touch",
                        "device_scale_factor",
                    )
                )
                if (
                    value is not None
                    and value.get("run_id") == root["run_id"]
                    and bound_to_current_run(value)
                    and environment_matches
                    and value.get("uncaught_errors") == []
                    and value.get("failed_requests") == []
                ):
                    console_validated = True
            if not console_validated:
                report.error("E_CONSOLE_EVIDENCE", "/hard_gates", "H_CONSOLE 证据必须绑定当前 spec/build 与测试环境，且 uncaught_errors、failed_requests 均为空。")

        design = root.get("design_validation")
        if not isinstance(design, dict):
            report.error("E_DESIGN_VALIDATION", "/design_validation", "浏览器模式产物校验缺少结构化 design_validation，已拒绝通过。")
        else:
            replay_validated = False
            for index, raw in enumerate(design["qa_replay_evidence"]):
                value = evidence_json(raw, f"/design_validation/qa_replay_evidence/{index}")
                if (
                    value is None
                    or value.get("run_id") != root["run_id"]
                    or value.get("environment") != expected_environment
                    or not bound_to_current_run(value)
                ):
                    continue
                if design["qa_replay_status"] == "passed":
                    first_hash = value.get("sequence_hash_first")
                    replay_hash = value.get("sequence_hash_replay")
                    replay_validated = (
                        value.get("passed") is True
                        and value.get("qa_seed") == design["qa_seed"]
                        and isinstance(value.get("input_trace_hash"), str)
                        and bool(value["input_trace_hash"])
                        and isinstance(first_hash, str)
                        and bool(first_hash)
                        and first_hash == replay_hash
                    )
                else:
                    replay_validated = value.get("randomness") is False and isinstance(value.get("reason"), str) and bool(value["reason"])
                if replay_validated:
                    break
            if not replay_validated:
                report.error("E_SEED_REPLAY_EVIDENCE", "/design_validation/qa_replay_evidence", "QA seed 重放证据必须绑定当前 spec/build，并提供相同输入轨迹下匹配的序列摘要；无随机性时必须给出结构化原因。")

            design_evidence_names = set(design["reachability"]["evidence"])
            for phase in design["phase_diffs"]:
                design_evidence_names.update(phase["evidence"])
            design_validated = False
            expected_phases = [
                {
                    "from": phase["from"],
                    "to": phase["to"],
                    "parameter_changes": phase["parameter_changes"],
                    "behavior_change": phase["behavior_change"],
                    "compensations": phase["compensations"],
                }
                for phase in design["phase_diffs"]
            ]
            for raw in sorted(design_evidence_names):
                value = evidence_json(raw, "/design_validation")
                if (
                    value is None
                    or value.get("run_id") != root["run_id"]
                    or value.get("environment") != expected_environment
                    or not bound_to_current_run(value)
                ):
                    continue
                reachability = value.get("reachability")
                evidence_phases = value.get("phase_diffs")
                phases_match = (
                    isinstance(evidence_phases, list)
                    and len(evidence_phases) == len(expected_phases)
                    and all(
                        isinstance(actual, dict) and all(actual.get(key) == expected[key] for key in expected)
                        for actual, expected in zip(evidence_phases, expected_phases)
                    )
                )
                if (
                    phases_match
                    and isinstance(reachability, dict)
                    and reachability.get("passed") is True
                    and reachability.get("checked_cases") == design["reachability"]["checked_cases"]
                    and reachability.get("unavoidable_overlap_count") == 0
                ):
                    design_validated = True
                    break
            if not design_validated:
                report.error("E_DESIGN_EVIDENCE", "/design_validation", "逐阶段参数 diff 与可达性必须由绑定当前 spec/build 且内容匹配的结构化 JSON 证明。")

            feedback = design["feedback"]
            cleanup = evidence_json(feedback["cleanup_evidence"], "/design_validation/feedback/cleanup_evidence")
            if not (
                cleanup is not None
                and cleanup.get("run_id") == root["run_id"]
                and cleanup.get("environment") == expected_environment
                and bound_to_current_run(cleanup)
                and cleanup.get("verdict_before_feedback") is True
                and cleanup.get("active_effect_count_after_exit") == 0
                and cleanup.get("root_transform_identity") is True
                and cleanup.get("reentry_passed") is True
            ):
                report.error("E_EFFECT_RESET_EVIDENCE", "/design_validation/feedback/cleanup_evidence", "效果清理证据必须绑定当前 spec/build，并证明 verdict 先提交、退出后效果为零、根变换归位且可再次进入。")

        play = root.get("play_validation")
        if not isinstance(play, dict):
            report.error("E_PLAY_VALIDATION", "/play_validation", "浏览器模式产物校验缺少结构化 play_validation，已拒绝通过。")
        else:
            anti = play["anti_autoplay"]
            play_evidence_names: set[str] = set(anti["evidence"])
            for trial in anti["trials"]:
                play_evidence_names.update(trial["evidence"])
            play_evidence_names.update(anti["position_trace"]["evidence"])
            for pattern in play["action_patterns"]:
                play_evidence_names.update(pattern["evidence"])
            for phase in play["phase_fingerprints"]:
                play_evidence_names.update(phase["evidence"])
            play_evidence_names.update(play["climax"]["evidence"])
            play_evidence_names.update(play["replay"]["evidence"])
            for observation in play["playtest_observations"]:
                play_evidence_names.update(observation["evidence"])

            expected_patterns = [
                {key: pattern[key] for key in ("id", "player_question", "skill_axes", "commitment", "mastery_signal")}
                for pattern in play["action_patterns"]
            ]
            expected_anti = {
                key: anti[key]
                for key in (
                    "passive_can_earn_highest_grade",
                    "preposition_can_earn_highest_grade",
                    "random_input_can_reliably_complete",
                    "spatial_pressure_uses_instant_reposition",
                )
            }
            expected_anti["trials"] = [
                {
                    key: trial[key]
                    for key in (
                        "policy",
                        "run_seed",
                        "attempts",
                        "completions",
                        "highest_grade_count",
                        "reliable_completion",
                        "input_trace_hash",
                        "outcome_sequence_hash",
                    )
                }
                for trial in anti["trials"]
            ]
            expected_anti["position_trace"] = {
                key: anti["position_trace"][key]
                for key in (
                    "applicable",
                    "input_path_hash",
                    "authority_trace_hash",
                    "direct_position_writes",
                    "all_steps_explained_by_control_model",
                )
            }
            expected_fingerprints = [
                {key: phase[key] for key in ("phase_id", "role", "pattern_ids", "fingerprint", "numeric_only_change", "recovery_role")}
                for phase in play["phase_fingerprints"]
            ]
            expected_climax = {
                key: play["climax"][key]
                for key in ("applicable", "numeric_only", "uses_mastered_patterns", "mastered_pattern_ids", "player_behavior_change")
            }
            expected_replay = {
                key: play["replay"][key]
                for key in ("qa_seed_policy", "runtime_variation_policy", "unintended_fixed_sequence")
            }
            expected_observations = [
                {
                    key: observation[key]
                    for key in (
                        "source",
                        "session_id",
                        "first_run_observation",
                        "second_run_change",
                        "clutch_or_failure_moment",
                        "replay_choice",
                    )
                }
                for observation in play["playtest_observations"]
            ]
            play_validated = False
            for raw in sorted(play_evidence_names):
                value = evidence_json(raw, "/play_validation")
                if (
                    value is not None
                    and value.get("kind") == "browser_play_trials"
                    and value.get("run_id") == root["run_id"]
                    and value.get("environment") == expected_environment
                    and bound_to_current_run(value)
                    and value.get("action_patterns") == expected_patterns
                    and value.get("anti_autoplay") == expected_anti
                    and value.get("phase_fingerprints") == expected_fingerprints
                    and value.get("climax") == expected_climax
                    and value.get("replay") == expected_replay
                    and value.get("playtest_observations") == expected_observations
                ):
                    play_validated = True
                    break
            if not play_validated:
                report.error("E_PLAY_EVIDENCE", "/play_validation", "操作感证据必须来自 browser_play_trials，绑定当前 spec/build 与环境，并与反例试跑、位置轨迹、pattern、阶段、高潮、重玩和试玩观察逐字段一致。")

        if root["run_mode"] == "full_run":
            archive_gate = gates.get("h_archive")
            archive_validated = False
            if archive_gate is not None:
                for index, raw in enumerate(archive_gate["evidence"]):
                    value = evidence_json(raw, f"/hard_gates/h_archive/evidence/{index}")
                    if (
                        value is not None
                        and value.get("run_id") == root["run_id"]
                        and bound_to_current_run(value, require_spec=False)
                        and all(value.get(key) is True for key in ("archive_safe", "content_match", "http_retest_passed"))
                    ):
                        archive_validated = True
            if not archive_validated:
                report.error("E_ARCHIVE_EVIDENCE", "/hard_gates", "H_ARCHIVE 证据必须绑定当前 build，并证明安全成员、内容一致和 HTTP 复测均通过。")

    if root["final_status"] == "passed" and root["run_mode"] in BROWSER_MODES:
        images = {path for path in evidence_paths if path.suffix.lower() in IMAGE_SUFFIXES and path.is_file()}
        valid_images = {path for path in images if visual_file_is_decodable(path)}
        for path in sorted(images - valid_images):
            report.error("E_VISUAL_INVALID", "/artifacts/evidence", f"视觉证据不是可识别的图片结构：{path.name}")
        environment = root["test_environment"]
        viewport = environment["viewport"]
        dpr = environment["device_scale_factor"]
        allowed_dimensions: set[tuple[int, int]] = set()
        if (
            isinstance(viewport, dict)
            and type(viewport.get("width")) is int
            and type(viewport.get("height")) is int
            and viewport["width"] > 0
            and viewport["height"] > 0
        ):
            allowed_dimensions.add((viewport["width"], viewport["height"]))
            if isinstance(dpr, (int, float)) and not isinstance(dpr, bool) and dpr > 0:
                allowed_dimensions.add((round(viewport["width"] * dpr), round(viewport["height"] * dpr)))
        else:
            report.error("E_VISUAL_DIMENSIONS", "/test_environment/viewport", "视觉证据校验需要有效的正整数 viewport。")
        screenshot_images = {path for path in valid_images if png_dimensions(path) in allowed_dimensions}
        for path in sorted(valid_images - screenshot_images):
            report.error(
                "E_VISUAL_DIMENSIONS",
                "/artifacts/evidence",
                f"浏览器截图尺寸必须匹配记录的 viewport 或 viewport×DPR：{path.name} 为 {png_dimensions(path)}。",
            )
        image_hashes = {path: sha256_file(path) for path in screenshot_images}
        if len(set(image_hashes.values())) < 5:
            report.error("E_VISUAL_EVIDENCE", "/artifacts/evidence", "浏览器通过至少需要五份尺寸合法且内容 SHA-256 不同的截图，复制同图改名不计数。")

        gates = {gate["id"]: gate for gate in root["hard_gates"]}
        category_gate_ids = ("h_boot", "h_mobile", "h_success", "h_miss", "h_flow")
        category_hashes: list[set[str]] = []
        for gate_id in category_gate_ids:
            gate = gates.get(gate_id)
            candidates: set[str] = set()
            if isinstance(gate, dict):
                for raw in gate["evidence"]:
                    path = evidence_by_name.get(raw)
                    if path in screenshot_images:
                        candidates.add(image_hashes[path])
            category_hashes.append(candidates)

        def distinct_category_assignment(index: int, used: set[str]) -> bool:
            if index == len(category_hashes):
                return True
            return any(
                digest not in used and distinct_category_assignment(index + 1, used | {digest})
                for digest in category_hashes[index]
            )

        if not distinct_category_assignment(0, set()):
            report.error("E_VISUAL_CATEGORIES", "/hard_gates", "开始/教学、活跃 cue、success、miss、结算五类硬门禁必须各引用内容不同的合法截图。")

        design = root.get("design_validation")
        if isinstance(design, dict):
            outcome_paths = [
                evidence_by_name.get(design["feedback"]["outcome_evidence"][outcome])
                for outcome in ("perfect", "success", "miss")
            ]
            outcome_hashes = [image_hashes.get(path) for path in outcome_paths]
            if any(value is None for value in outcome_hashes) or len(set(outcome_hashes)) != 3:
                report.error("E_OUTCOME_VISUALS", "/design_validation/feedback/outcome_evidence", "perfect、success、miss 必须各引用尺寸合法且内容 SHA-256 不同的 PNG。")

    return report


def merge(target: Report, source: Report) -> None:
    for item in source.errors:
        target.error(item["code"], item["path"], item["message"])
    for item in source.warnings:
        target.warning(item["code"], item["path"], item["message"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_path", help="管线报告 JSON 路径；使用 - 表示标准输入")
    parser.add_argument("--schema", help="报告 Schema；默认使用 Skill 内置 Schema")
    parser.add_argument("--artifact-root", help="验证产物存在性、哈希、路径和归档内容")
    parser.add_argument("--require-passed", action="store_true", help="仅 final_status=passed 且所有校验通过时退出 0")
    args = parser.parse_args()

    report_path = None if args.json_path == "-" else Path(args.json_path).resolve()
    schema_path = Path(args.schema).resolve() if args.schema else Path(__file__).resolve().parent.parent / "references" / "pipeline-report.schema.json"
    try:
        data = read_json(report_path)
        schema = read_json(schema_path)
    except (OSError, json.JSONDecodeError) as exc:
        output = {
            "valid": False,
            "schema_valid": False,
            "semantic_valid": False,
            "artifacts_verified": False,
            "final_status": None,
            "mode_passed": False,
            "deliverable": False,
            "errors": [{"code": "E_JSON", "path": "/", "message": str(exc)}],
            "warnings": [],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 1

    schema_errors: list[SchemaError]
    try:
        schema_errors = validate_schema(data, schema)
    except (KeyError, TypeError, ValueError, re.error) as exc:  # type: ignore[name-defined]
        schema_errors = [SchemaError("/", f"内置 Schema 校验器失败：{exc}")]

    result = Report()
    for error in schema_errors:
        result.error("E_SCHEMA", error.path, error.message)
    semantic_valid = False
    artifacts_verified = False
    if not schema_errors:
        semantic = validate_semantics(data)
        merge(result, semantic)
        semantic_valid = not semantic.errors
        if args.artifact_root:
            artifact_result = validate_artifacts(data, Path(args.artifact_root), report_path)
            merge(result, artifact_result)
            artifacts_verified = not artifact_result.errors
        elif args.require_passed and data["final_status"] == "passed" and data["run_mode"] in MODE_ARTIFACTS:
            result.error("E_ARTIFACT_ROOT", "/", "交付门禁必须提供 --artifact-root 以核验真实产物。")

    final_status = data.get("final_status") if isinstance(data, dict) else None
    valid = not result.errors
    run_mode = data.get("run_mode") if isinstance(data, dict) else None
    needs_artifact_proof = run_mode in MODE_ARTIFACTS
    mode_passed = valid and final_status == "passed" and (artifacts_verified or not needs_artifact_proof)
    deliverable = mode_passed and run_mode == "full_run"
    output = {
        "valid": valid,
        "schema_valid": not schema_errors,
        "semantic_valid": semantic_valid,
        "artifacts_verified": artifacts_verified,
        "final_status": final_status,
        "mode_passed": mode_passed,
        "deliverable": deliverable,
        "errors": result.errors,
        "warnings": result.warnings,
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    if args.require_passed:
        return 0 if mode_passed else 1
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
