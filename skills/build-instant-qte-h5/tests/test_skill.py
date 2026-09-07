from __future__ import annotations

import copy
import hashlib
import json
import re
import struct
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zlib
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

from artifact_tools import sha256_directory, sha256_file  # noqa: E402
from check_h5_delivery import check  # noqa: E402
from schema_subset import validate_schema  # noqa: E402
from validate_authoring_spec import validate_authoring  # noqa: E402
from validate_pipeline_report import validate_artifacts, validate_semantics, visual_file_is_decodable  # noqa: E402


class SkillContractTests(unittest.TestCase):
    def test_generation_rules_match_original_template(self) -> None:
        data = (SKILL_ROOT / "references/generation_rules.md").read_bytes()
        self.assertEqual(
            hashlib.sha256(data).hexdigest(),
            "e1c1867ff79f2962ca74645d5b1707e40112d3ccb0a08d3348078c70142e4708",
        )

    def test_fallback_template_blocks_uncalibrated_values_and_validates(self) -> None:
        schema = json.loads((SKILL_ROOT / "references/authoring.schema.json").read_text(encoding="utf-8"))
        template = json.loads((SKILL_ROOT / "references/authoring.template.json").read_text(encoding="utf-8"))
        self.assertFalse(validate_schema(template, schema))
        self.assertTrue(template["decision_status"]["open"])
        self.assertEqual(template["calibration_contract"]["policy"], "game_specific_not_global_defaults")
        for parameter in template["calibration_contract"]["parameters"]:
            self.assertEqual(parameter["status"], "open")
            self.assertIsNone(parameter["value"])
            self.assertTrue(parameter["source"])
            self.assertTrue(parameter["constraints"])
            self.assertTrue(parameter["validation_signal"])
        anti = template["fun_contract"]["anti_autoplay"]
        self.assertFalse(any(anti[key] for key in (
            "passive_can_earn_highest_grade",
            "preposition_can_earn_highest_grade",
            "random_input_can_reliably_complete",
            "spatial_pressure_uses_instant_reposition",
        )))
        self.assertFalse(validate_authoring(template, schema))
        self.assertIn("E_NOT_READY", {item["code"] for item in validate_authoring(template, schema, require_ready=True)})

    def test_authoring_validator_rejects_hidden_default_and_missing_reference(self) -> None:
        schema = json.loads((SKILL_ROOT / "references/authoring.schema.json").read_text(encoding="utf-8"))
        template = json.loads((SKILL_ROOT / "references/authoring.template.json").read_text(encoding="utf-8"))
        template["calibration_contract"]["parameters"][0]["value"] = 90
        template["mechanics"]["cue_defaults"]["telegraph_param"] = "missing_parameter"
        codes = {item["code"] for item in validate_authoring(template, schema)}
        self.assertTrue({"E_OPEN_VALUE", "E_PARAMETER_REF"} <= codes)

    def test_authoring_ready_rejects_negative_placeholder_and_inconsistent_cue(self) -> None:
        schema = json.loads((SKILL_ROOT / "references/authoring.schema.json").read_text(encoding="utf-8"))
        data = json.loads((SKILL_ROOT / "references/authoring.template.json").read_text(encoding="utf-8"))
        data["decision_status"]["open"] = []
        for parameter in data["calibration_contract"]["parameters"]:
            parameter["status"] = "measured"
            parameter["value"] = -1
        cue = data["mechanics"]["cue_nodes"][0]
        cue["subtype"] = "tap_target"
        cue["trigger"] = {"type": "event", "at_param": None, "event": None}
        next(item for item in cue["judgements"] if item["grade"] == "perfect")["requirements"] = []
        codes = {item["code"] for item in validate_authoring(data, schema, require_ready=True)}
        self.assertTrue({
            "E_PARAMETER_DOMAIN",
            "E_PLACEHOLDER",
            "E_CUE_ACTION",
            "E_TRIGGER_SHAPE",
            "E_JUDGEMENT_REQUIREMENT",
        } <= codes)

    def test_authoring_decision_states_are_disjoint_and_verdicts_have_feedback(self) -> None:
        schema = json.loads((SKILL_ROOT / "references/authoring.schema.json").read_text(encoding="utf-8"))
        data = json.loads((SKILL_ROOT / "references/authoring.template.json").read_text(encoding="utf-8"))
        duplicated = data["decision_status"]["open"][0]
        data["decision_status"]["locked"].append(duplicated)
        data["feedback_contract"]["events"] = [
            event for event in data["feedback_contract"]["events"] if event["on"] != "qte_perfect"
        ]
        codes = {item["code"] for item in validate_authoring(data, schema)}
        self.assertTrue({"E_DECISION_STATUS", "E_FEEDBACK_EVENT"} <= codes)

    def test_generation_rules_are_preserved_and_fun_contract_is_mandatory(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("references/generation_rules.md", skill)
        self.assertIn("references/fun-action-patterns.md", skill)
        self.assertIn("一起构成创意冻结前的必读合同", skill)

    def test_design_pattern_references_are_routed(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        for name in (
            "level-design-patterns.md",
            "numeric-design-patterns.md",
            "game-feel-patterns.md",
            "fun-action-patterns.md",
        ):
            self.assertTrue((SKILL_ROOT / "references" / name).is_file())
            self.assertIn(f"references/{name}", skill)

    def test_high_star_source_set_is_commit_pinned(self) -> None:
        sources = "\n".join(
            (SKILL_ROOT / "references" / name).read_text(encoding="utf-8")
            for name in (
                "level-design-patterns.md",
                "numeric-design-patterns.md",
                "game-feel-patterns.md",
                "fun-action-patterns.md",
            )
        )
        expected_repositories = {
            "Anuken/Mindustry",
            "OndrejNepozitek/Edgar-DotNet",
            "deepnight/ldtk",
            "OpenRA/OpenRA",
            "optuna/optuna",
            "facebookresearch/nevergrad",
            "dubzzz/fast-check",
            "simple-statistics/simple-statistics",
            "ondras/rot.js",
            "open-telemetry/opentelemetry-js",
            "juliangarnier/anime",
            "catdad/canvas-confetti",
            "tweenjs/tween.js",
            "pixijs-userland/particle-emitter",
            "rexrainbow/phaser3-rex-notes",
            "libgdx/libgdx",
            "godotengine/godot",
            "HaxeFlixel/flixel",
            "NoelFB/Celeste",
            "ppy/osu",
            "stepmania/stepmania",
            "FunkinCrew/Funkin",
            "Quaver/Quaver",
            "vittorioromeo/SSVOpenHexagon",
            "taisei-project/taisei",
            "00-Evan/shattered-pixel-dungeon",
        }
        self.assertTrue(expected_repositories <= set(re.findall(r"github\.com/([^/]+/[^/)#]+)", sources)))
        self.assertGreaterEqual(len(re.findall(r"/blob/[0-9a-f]{40}/", sources)), 25)

    def test_fun_action_source_manifest_is_auditable(self) -> None:
        manifest = json.loads((SKILL_ROOT / "references/fun-action-sources.json").read_text(encoding="utf-8"))
        repositories = manifest["repositories"]
        self.assertGreaterEqual(len(repositories), 5)
        self.assertEqual(len({item["repo"] for item in repositories}), len(repositories))
        for item in repositories:
            self.assertGreater(item["stars_snapshot"], 100)
            self.assertRegex(item["commit"], r"^[0-9a-f]{40}$")
            self.assertTrue(item["license_spdx"])
            self.assertTrue(item["use"])

    def test_skill_revision_matches_report_example(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        schema = json.loads((SKILL_ROOT / "references/pipeline-report.schema.json").read_text(encoding="utf-8"))
        example = json.loads((SKILL_ROOT / "references/example-pipeline-report.json").read_text(encoding="utf-8"))
        self.assertIn("Skill revision：`1.2.0`", skill)
        self.assertEqual(schema["properties"]["control"]["properties"]["skill_revision"]["const"], "1.2.0")
        self.assertEqual(example["control"]["skill_revision"], "1.2.0")
        self.assertEqual(example["report_version"], "1.2.0")

    def test_numeric_contract_has_no_global_gameplay_defaults(self) -> None:
        numeric = (SKILL_ROOT / "references/numeric-design-patterns.md").read_text(encoding="utf-8")
        feel = (SKILL_ROOT / "references/game-feel-patterns.md").read_text(encoding="utf-8")
        self.assertIn("Skill 不给全局", numeric)
        self.assertNotRegex(numeric, r"telegraph_ms:\s*\d")
        self.assertNotRegex(numeric, r"hit_window_ms:\s*\d")
        self.assertNotRegex(feel, r"\d+\s*[～–-]\s*\d+\s*ms")
        self.assertNotIn("建议初始 recipe", feel)


class StaticDeliveryTests(unittest.TestCase):
    def make_build(self, index: str, extra: dict[str, str] | None = None) -> Path:
        temp = Path(tempfile.mkdtemp())
        (temp / "index.html").write_text(index, encoding="utf-8")
        for relative, source in (extra or {}).items():
            path = temp / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source, encoding="utf-8")
        self.addCleanup(lambda: __import__("shutil").rmtree(temp, ignore_errors=True))
        return temp

    def base_html(self, body: str = "") -> str:
        return f'<meta name="viewport" content="width=device-width"><style>canvas{{touch-action:none}}</style>{body}'

    def assert_code(self, root: Path, code: str) -> None:
        result, _ = check(str(root), "index.html")
        self.assertIn(code, {item["code"] for item in result.errors})

    def test_good_build(self) -> None:
        root = self.make_build(self.base_html('<script src="game.js"></script>'), {"game.js": "console.log('ok')"})
        result, _ = check(str(root), "index.html")
        self.assertFalse(result.errors)

    def test_base_href_is_rejected(self) -> None:
        root = self.make_build(self.base_html('<base href="../outside/"><script src="app.js"></script>'), {"app.js": ""})
        self.assert_code(root, "E_BASE_URL")

    def test_uppercase_file_scheme_is_rejected(self) -> None:
        root = self.make_build(self.base_html('<img src="FILE:///etc/passwd">'))
        self.assert_code(root, "E_FILE_URL")

    def test_css_dependency_is_recursive(self) -> None:
        root = self.make_build(self.base_html('<link rel="stylesheet" href="styles.css">'), {"styles.css": "body{background:url(missing.png)}"})
        self.assert_code(root, "E_RESOURCE_MISSING")

    def test_module_dependency_is_recursive(self) -> None:
        root = self.make_build(self.base_html('<script type="module" src="game.js"></script>'), {"game.js": "import './missing.js';"})
        self.assert_code(root, "E_RESOURCE_MISSING")

    def test_srcset_dependency_is_checked(self) -> None:
        root = self.make_build(self.base_html('<img srcset="missing-1x.png 1x, missing-2x.png 2x">'))
        self.assert_code(root, "E_RESOURCE_MISSING")

    def test_data_uri_is_not_external_network(self) -> None:
        root = self.make_build(self.base_html('<img src="data:image/gif;base64,R0lGODlhAQABAAAAACw=">'))
        result, summary = check(str(root), "index.html")
        self.assertFalse(result.errors)
        self.assertEqual(summary["external_references"], 0)
        self.assertEqual(summary["embedded_references"], 1)


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads((SKILL_ROOT / "references/pipeline-report.schema.json").read_text(encoding="utf-8"))
        cls.example = json.loads((SKILL_ROOT / "references/example-pipeline-report.json").read_text(encoding="utf-8"))

    def test_empty_object_fails_schema(self) -> None:
        self.assertTrue(validate_schema({}, self.schema))

    def test_example_passes_structure_and_semantics(self) -> None:
        self.assertFalse(validate_schema(self.example, self.schema))
        self.assertFalse(validate_semantics(self.example).errors)

    def test_empty_implement_cannot_pass(self) -> None:
        data = copy.deepcopy(self.example)
        data["run_mode"] = "implement"
        data["control"]["build_hash"] = None
        data["artifacts"]["build_dir"] = None
        data["artifacts"]["entrypoint"] = None
        data["artifacts"]["archive"] = None
        data["receipts"]["implement"] = {"status": "skipped", "schema_hash": None, "spec_hash": None, "build_hash": None, "evidence": []}
        data["stages"] = [
            {"id": "implement", "status": "passed", "attempts": 0, "evidence": [], "notes": []},
            {"id": "static_check", "status": "passed", "attempts": 0, "evidence": [], "notes": []},
        ]
        data["hard_gates"] = []
        data["soft_gates"] = []
        self.assertFalse(validate_schema(data, self.schema))
        codes = {item["code"] for item in validate_semantics(data).errors}
        self.assertTrue({"E_BUILD_HASH", "E_RECEIPT", "E_STAGE_ATTEMPT"} <= codes)

    def test_failed_report_can_be_structurally_valid(self) -> None:
        data = copy.deepcopy(self.example)
        data["final_status"] = "failed"
        data["contract"]["creative_schema_preserved"] = False
        data["issues"] = [{
            "id": "issue-contract",
            "gate_id": None,
            "severity": "error",
            "status": "open",
            "summary": "上游合同被破坏",
            "evidence": ["creative-spec.json"],
        }]
        self.assertFalse(validate_schema(data, self.schema))
        self.assertFalse(validate_semantics(data).errors)

    def test_browser_report_requires_structured_design_validation(self) -> None:
        data = copy.deepcopy(self.example)
        del data["design_validation"]
        self.assertFalse(validate_schema(data, self.schema))
        self.assertIn("E_DESIGN_VALIDATION", {item["code"] for item in validate_semantics(data).errors})

    def test_browser_report_requires_structured_play_validation(self) -> None:
        data = copy.deepcopy(self.example)
        del data["play_validation"]
        self.assertFalse(validate_schema(data, self.schema))
        self.assertIn("E_PLAY_VALIDATION", {item["code"] for item in validate_semantics(data).errors})

    def test_passive_or_preposition_autoplay_is_rejected(self) -> None:
        data = copy.deepcopy(self.example)
        data["play_validation"]["anti_autoplay"]["preposition_can_earn_highest_grade"] = True
        self.assertIn("E_ACTION_AUTOPLAY", {item["code"] for item in validate_semantics(data).errors})

    def test_counterfactual_trials_require_all_policies_and_consistent_counts(self) -> None:
        data = copy.deepcopy(self.example)
        trials = data["play_validation"]["anti_autoplay"]["trials"]
        trials.pop()
        trials[0]["highest_grade_count"] = trials[0]["attempts"] + 1
        codes = {item["code"] for item in validate_semantics(data).errors}
        self.assertTrue({"E_COUNTERFACTUAL_POLICY", "E_COUNTERFACTUAL_COUNTS", "E_ACTION_AUTOPLAY_TRIAL"} <= codes)

    def test_position_trace_rejects_direct_authority_write(self) -> None:
        data = copy.deepcopy(self.example)
        trace = data["play_validation"]["anti_autoplay"]["position_trace"]
        trace["direct_position_writes"] = 1
        trace["all_steps_explained_by_control_model"] = False
        self.assertIn("E_INSTANT_REPOSITION", {item["code"] for item in validate_semantics(data).errors})

    def test_instant_reposition_and_numeric_only_phase_are_rejected(self) -> None:
        data = copy.deepcopy(self.example)
        data["play_validation"]["anti_autoplay"]["spatial_pressure_uses_instant_reposition"] = True
        data["play_validation"]["phase_fingerprints"][0]["numeric_only_change"] = True
        codes = {item["code"] for item in validate_semantics(data).errors}
        self.assertTrue({"E_INSTANT_REPOSITION", "E_NUMERIC_ONLY_PHASE"} <= codes)

    def test_standalone_numeric_only_climax_is_rejected(self) -> None:
        data = copy.deepcopy(self.example)
        data["play_validation"]["climax"]["numeric_only"] = True
        self.assertIn("E_CLIMAX_COMPOSITION", {item["code"] for item in validate_semantics(data).errors})

    def test_climax_patterns_must_exist_and_be_taught_before_climax(self) -> None:
        missing = copy.deepcopy(self.example)
        missing["play_validation"]["climax"]["mastered_pattern_ids"] = ["missing_pattern"]
        self.assertIn("E_PATTERN_REFERENCE", {item["code"] for item in validate_semantics(missing).errors})

        untaught = copy.deepcopy(self.example)
        for phase in untaught["play_validation"]["phase_fingerprints"][:-1]:
            phase["pattern_ids"] = ["commit_intercept"]
        self.assertIn("E_CLIMAX_TEACHING", {item["code"] for item in validate_semantics(untaught).errors})

    def test_passed_action_feel_requires_human_observation(self) -> None:
        data = copy.deepcopy(self.example)
        for observation in data["play_validation"]["playtest_observations"]:
            observation["source"] = "agent_observation"
        self.assertIn("E_HUMAN_PLAYTEST", {item["code"] for item in validate_semantics(data).errors})

    def test_static_warning_requires_tracked_issue(self) -> None:
        data = copy.deepcopy(self.example)
        data["static_check"]["warnings"] = ["远程字体需浏览器复核"]
        self.assertIn("E_STATIC_WARNING_UNTRACKED", {item["code"] for item in validate_semantics(data).errors})

    def test_passed_mode_cannot_omit_schema_receipt(self) -> None:
        data = copy.deepcopy(self.example)
        data["control"]["schema_hash"] = None
        data["artifacts"]["schema"] = None
        for receipt in data["receipts"].values():
            receipt["schema_hash"] = None
        codes = {item["code"] for item in validate_semantics(data).errors}
        self.assertTrue({"E_SCHEMA_HASH", "E_ARTIFACT"} <= codes)

    def test_verify_does_not_require_archive_gate(self) -> None:
        data = copy.deepcopy(self.example)
        data["run_mode"] = "verify"
        data["artifacts"]["archive"] = None
        data["stages"] = [
            {"id": "static_check", "status": "passed", "attempts": 1, "evidence": ["evidence/static-check.json"], "notes": []},
            {"id": "browser_test", "status": "passed", "attempts": 1, "evidence": ["evidence/input-events.json"], "notes": []},
        ]
        data["hard_gates"] = [gate for gate in data["hard_gates"] if gate["id"] != "h_archive"]
        data["design_validation"]["scope"] = "embedded"
        data["design_validation"]["phase_diffs"] = []
        data["receipts"]["author"]["status"] = "skipped"
        data["receipts"]["author"]["evidence"] = []
        data["receipts"]["implement"]["status"] = "skipped"
        data["receipts"]["implement"]["evidence"] = []
        self.assertFalse(validate_schema(data, self.schema))
        self.assertFalse(validate_semantics(data).errors)

    def test_truncated_png_is_not_visual_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_name:
            path = Path(temp_name) / "fake.png"
            path.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01")
            self.assertFalse(visual_file_is_decodable(path))

    def test_png_with_valid_chunks_but_short_scanline_is_rejected(self) -> None:
        def chunk(kind: bytes, payload: bytes) -> bytes:
            return (
                struct.pack(">I", len(payload))
                + kind
                + payload
                + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
            )

        with tempfile.TemporaryDirectory() as temp_name:
            path = Path(temp_name) / "fake.png"
            # IHDR 声明 1×1 RGBA，正确解压后应有 1 字节 filter + 4 字节像素；这里只给 filter。
            ihdr = struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
            path.write_bytes(
                b"\x89PNG\r\n\x1a\n"
                + chunk(b"IHDR", ihdr)
                + chunk(b"IDAT", zlib.compress(b"\x00"))
                + chunk(b"IEND", b"")
            )
            self.assertFalse(visual_file_is_decodable(path))

    def test_require_passed_rejects_valid_failed_report(self) -> None:
        data = copy.deepcopy(self.example)
        data["final_status"] = "failed"
        data["issues"] = [{
            "id": "issue-runtime",
            "gate_id": "h_boot",
            "severity": "error",
            "status": "open",
            "summary": "启动失败",
            "evidence": ["evidence/browser-console.json"],
        }]
        with tempfile.TemporaryDirectory() as temp_name:
            report_path = Path(temp_name) / "failed.json"
            report_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SKILL_ROOT / "scripts/validate_pipeline_report.py"),
                    str(report_path),
                    "--require-passed",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            output = json.loads(completed.stdout)
            self.assertEqual(completed.returncode, 1)
            self.assertTrue(output["valid"])
            self.assertFalse(output["deliverable"])

    def test_artifact_path_escape_is_rejected(self) -> None:
        data = copy.deepcopy(self.example)
        data["artifacts"]["report"] = "../outside.json"
        with tempfile.TemporaryDirectory() as temp_name:
            result = validate_artifacts(data, Path(temp_name), None)
            self.assertIn("E_ARTIFACT_PATH", {item["code"] for item in result.errors})

    def test_real_artifacts_hash_and_archive_validate(self) -> None:
        # 这是 validator 的合同 fixture；真实浏览器来源由 full_run 的 browser runner 负责，
        # 不能把本测试生成的 PNG/JSON 当成任何游戏的试玩证据。
        with tempfile.TemporaryDirectory() as temp_name:
            root = Path(temp_name)
            game = root / "game"
            evidence_dir = root / "evidence"
            game.mkdir()
            evidence_dir.mkdir()
            (game / "index.html").write_text('<meta name="viewport" content="width=device-width"><style>*{touch-action:none}</style>', encoding="utf-8")
            (root / "creative-spec.json").write_text('{"game":"test"}\n', encoding="utf-8")
            (root / "frozen-working-spec.json").write_text('{"business_spec_hash":"test","plans":{}}\n', encoding="utf-8")
            (root / "authoring.schema.json").write_text('{"type":"object"}\n', encoding="utf-8")
            data = copy.deepcopy(self.example)
            data["control"]["spec_hash"] = sha256_file(root / "frozen-working-spec.json")
            data["control"]["schema_hash"] = sha256_file(root / "authoring.schema.json")
            data["control"]["build_hash"] = sha256_directory(game)
            for receipt in data["receipts"].values():
                receipt["schema_hash"] = data["control"]["schema_hash"]
                receipt["spec_hash"] = data["control"]["spec_hash"]
            data["receipts"]["implement"]["build_hash"] = data["control"]["build_hash"]
            data["receipts"]["verify"]["build_hash"] = data["control"]["build_hash"]
            static_result, static_summary = check(str(game), "index.html")
            self.assertFalse(static_result.errors)

            def make_valid_png(pattern: int) -> bytes:
                def chunk(kind: bytes, payload: bytes) -> bytes:
                    return (
                        struct.pack(">I", len(payload))
                        + kind
                        + payload
                        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
                    )

                width, height = 390, 844
                ihdr = struct.pack(">IIBBBBB", width, height, 1, 0, 0, 0, 0)
                # 1-bit grayscale: ceil(390/8) = 49 字节，每行前缀 filter=0。
                pixels = (b"\x00" + bytes([pattern & 0xFF]) * 49) * height
                return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b"")

            tiny_png = bytes.fromhex(
                "89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c02"
                "0000000b4944415478da6364f80f00010501012718e3660000000049454e44ae426082"
            )
            structured_evidence = {
                "evidence/static-check.json": {
                    "valid": True,
                    "errors": static_result.errors,
                    "warnings": static_result.warnings,
                    "summary": static_summary,
                },
                "evidence/design-validation.json": {
                    "run_id": data["run_id"],
                    "spec_hash": data["control"]["spec_hash"],
                    "build_hash": data["control"]["build_hash"],
                    "environment": {
                        key: data["test_environment"][key]
                        for key in (
                            "tested_at",
                            "base_url",
                            "browser",
                            "browser_version",
                            "viewport",
                            "has_touch",
                            "device_scale_factor",
                        )
                    },
                    "passed": True,
                    "qa_seed": data["design_validation"]["qa_seed"],
                    "input_trace_hash": "sha256:input-trace",
                    "sequence_hash_first": "sha256:sequence",
                    "sequence_hash_replay": "sha256:sequence",
                    "phase_diffs": [
                        {
                            "from": phase["from"],
                            "to": phase["to"],
                            "parameter_changes": phase["parameter_changes"],
                            "behavior_change": phase["behavior_change"],
                            "compensations": phase["compensations"],
                        }
                        for phase in data["design_validation"]["phase_diffs"]
                    ],
                    "reachability": {
                        "passed": True,
                        "checked_cases": data["design_validation"]["reachability"]["checked_cases"],
                        "unavoidable_overlap_count": 0,
                    },
                },
                "evidence/play-validation.json": {
                    "kind": "browser_play_trials",
                    "run_id": data["run_id"],
                    "spec_hash": data["control"]["spec_hash"],
                    "build_hash": data["control"]["build_hash"],
                    "environment": {
                        key: data["test_environment"][key]
                        for key in (
                            "tested_at",
                            "base_url",
                            "browser",
                            "browser_version",
                            "viewport",
                            "has_touch",
                            "device_scale_factor",
                        )
                    },
                    "action_patterns": [
                        {
                            key: pattern[key]
                            for key in ("id", "player_question", "skill_axes", "commitment", "mastery_signal")
                        }
                        for pattern in data["play_validation"]["action_patterns"]
                    ],
                    "anti_autoplay": {
                        **{
                            key: data["play_validation"]["anti_autoplay"][key]
                            for key in (
                                "passive_can_earn_highest_grade",
                                "preposition_can_earn_highest_grade",
                                "random_input_can_reliably_complete",
                                "spatial_pressure_uses_instant_reposition",
                            )
                        },
                        "trials": [
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
                            for trial in data["play_validation"]["anti_autoplay"]["trials"]
                        ],
                        "position_trace": {
                            key: data["play_validation"]["anti_autoplay"]["position_trace"][key]
                            for key in (
                                "applicable",
                                "input_path_hash",
                                "authority_trace_hash",
                                "direct_position_writes",
                                "all_steps_explained_by_control_model",
                            )
                        },
                    },
                    "phase_fingerprints": [
                        {
                            key: phase[key]
                            for key in ("phase_id", "role", "pattern_ids", "fingerprint", "numeric_only_change", "recovery_role")
                        }
                        for phase in data["play_validation"]["phase_fingerprints"]
                    ],
                    "climax": {
                        key: data["play_validation"]["climax"][key]
                        for key in ("applicable", "numeric_only", "uses_mastered_patterns", "mastered_pattern_ids", "player_behavior_change")
                    },
                    "replay": {
                        key: data["play_validation"]["replay"][key]
                        for key in ("qa_seed_policy", "runtime_variation_policy", "unintended_fixed_sequence")
                    },
                    "playtest_observations": [
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
                        for observation in data["play_validation"]["playtest_observations"]
                    ],
                },
                "evidence/effect-reset.json": {
                    "run_id": data["run_id"],
                    "spec_hash": data["control"]["spec_hash"],
                    "build_hash": data["control"]["build_hash"],
                    "environment": {
                        key: data["test_environment"][key]
                        for key in (
                            "tested_at",
                            "base_url",
                            "browser",
                            "browser_version",
                            "viewport",
                            "has_touch",
                            "device_scale_factor",
                        )
                    },
                    "verdict_before_feedback": True,
                    "active_effect_count_after_exit": 0,
                    "root_transform_identity": True,
                    "reentry_passed": True,
                },
                "evidence/browser-console.json": {
                    "run_id": data["run_id"],
                    "spec_hash": data["control"]["spec_hash"],
                    "build_hash": data["control"]["build_hash"],
                    "tested_at": data["test_environment"]["tested_at"],
                    "base_url": data["test_environment"]["base_url"],
                    "browser": data["test_environment"]["browser"],
                    "browser_version": data["test_environment"]["browser_version"],
                    "viewport": data["test_environment"]["viewport"],
                    "has_touch": data["test_environment"]["has_touch"],
                    "device_scale_factor": data["test_environment"]["device_scale_factor"],
                    "uncaught_errors": [],
                    "failed_requests": [],
                },
                "evidence/input-events.json": {
                    "kind": "browser_assertions",
                    "run_id": data["run_id"],
                    "spec_hash": data["control"]["spec_hash"],
                    "build_hash": data["control"]["build_hash"],
                    "environment": {
                        key: data["test_environment"][key]
                        for key in (
                            "tested_at",
                            "base_url",
                            "browser",
                            "browser_version",
                            "viewport",
                            "has_touch",
                            "device_scale_factor",
                        )
                    },
                    "assertions": {
                        "h_input": {"pointer_events": 2, "semantic_actions": 2, "page_scroll_delta": 0},
                        "h_resolve_once": {"competing_inputs": 3, "verdict_commits": 1, "result_events": 1},
                        "h_recovery": {"success_advanced": True, "miss_advanced": True},
                    },
                },
                "evidence/archive-retest.json": {
                    "run_id": data["run_id"],
                    "build_hash": data["control"]["build_hash"],
                    "archive_safe": True,
                    "content_match": True,
                    "http_retest_passed": True,
                },
            }
            png_index = 0
            for raw in data["artifacts"]["evidence"]:
                path = root / raw
                if not path.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    if path.suffix == ".png":
                        png_index += 1
                        path.write_bytes(make_valid_png(png_index))
                    else:
                        path.write_text(json.dumps(structured_evidence.get(raw, {})), encoding="utf-8")
            design_evidence = set(data["design_validation"]["qa_replay_evidence"])
            design_evidence.update(data["design_validation"]["reachability"]["evidence"])
            for phase in data["design_validation"]["phase_diffs"]:
                design_evidence.update(phase["evidence"])
            design_evidence.update(data["design_validation"]["feedback"]["outcome_evidence"].values())
            design_evidence.add(data["design_validation"]["feedback"]["cleanup_evidence"])
            design_evidence.add(data["design_validation"]["feedback"]["reduced_motion_evidence"])
            for pattern in data["play_validation"]["action_patterns"]:
                design_evidence.update(pattern["evidence"])
            anti = data["play_validation"]["anti_autoplay"]
            design_evidence.update(anti["evidence"])
            for trial in anti["trials"]:
                design_evidence.update(trial["evidence"])
            design_evidence.update(anti["position_trace"]["evidence"])
            for phase in data["play_validation"]["phase_fingerprints"]:
                design_evidence.update(phase["evidence"])
            design_evidence.update(data["play_validation"]["climax"]["evidence"])
            design_evidence.update(data["play_validation"]["replay"]["evidence"])
            for observation in data["play_validation"]["playtest_observations"]:
                design_evidence.update(observation["evidence"])
            manifest_evidence = sorted(
                {raw for gate in data["hard_gates"] for raw in gate["evidence"]}
                | {raw for gate in data["soft_gates"] for raw in gate["evidence"]}
                | design_evidence
            )
            browser_manifest = {
                "manifest_version": "1.0",
                "run_id": data["run_id"],
                "spec_hash": data["control"]["spec_hash"],
                "build_hash": data["control"]["build_hash"],
                "environment": {
                    key: data["test_environment"][key]
                    for key in (
                        "tested_at",
                        "base_url",
                        "browser",
                        "browser_version",
                        "viewport",
                        "has_touch",
                        "device_scale_factor",
                    )
                },
                "gate_results": {
                    gate["id"]: {"passed": gate["status"] == "passed", "evidence": gate["evidence"]}
                    for gate in data["hard_gates"]
                },
                "soft_gate_results": {
                    gate["id"]: {"status": gate["status"], "evidence": gate["evidence"]}
                    for gate in data["soft_gates"]
                },
                "design_evidence": sorted(design_evidence),
                "evidence_hashes": {
                    raw: sha256_file(root / raw)
                    for raw in manifest_evidence
                },
            }
            manifest_path = root / "evidence/browser-run-manifest.json"
            manifest_path.write_text(json.dumps(browser_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            with tarfile.open(root / "game.tar.gz", "w:gz") as archive:
                archive.add(game, arcname="game")
            report_path = root / "qte-pipeline-report.json"
            report_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            self.assertFalse(validate_schema(data, self.schema))
            self.assertFalse(validate_semantics(data).errors)
            self.assertFalse(validate_artifacts(data, root, report_path).errors)

            start_path = root / "evidence/start.png"
            start_content = start_path.read_bytes()
            start_path.write_bytes(tiny_png)
            browser_manifest["evidence_hashes"]["evidence/start.png"] = sha256_file(start_path)
            manifest_path.write_text(json.dumps(browser_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            tiny_codes = {item["code"] for item in validate_artifacts(data, root, report_path).errors}
            self.assertIn("E_VISUAL_DIMENSIONS", tiny_codes)
            start_path.write_bytes(start_content)
            browser_manifest["evidence_hashes"]["evidence/start.png"] = sha256_file(start_path)
            manifest_path.write_text(json.dumps(browser_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

            success_path = root / "evidence/success.png"
            perfect_path = root / "evidence/perfect.png"
            success_content = success_path.read_bytes()
            perfect_content = perfect_path.read_bytes()
            miss_content = (root / "evidence/miss.png").read_bytes()
            success_path.write_bytes(miss_content)
            perfect_path.write_bytes(miss_content)
            browser_manifest["evidence_hashes"]["evidence/success.png"] = sha256_file(success_path)
            browser_manifest["evidence_hashes"]["evidence/perfect.png"] = sha256_file(perfect_path)
            manifest_path.write_text(json.dumps(browser_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            duplicate_codes = {item["code"] for item in validate_artifacts(data, root, report_path).errors}
            self.assertTrue({"E_VISUAL_CATEGORIES", "E_OUTCOME_VISUALS"} <= duplicate_codes)
            success_path.write_bytes(success_content)
            perfect_path.write_bytes(perfect_content)
            browser_manifest["evidence_hashes"]["evidence/success.png"] = sha256_file(success_path)
            browser_manifest["evidence_hashes"]["evidence/perfect.png"] = sha256_file(perfect_path)
            manifest_path.write_text(json.dumps(browser_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

            design_path = root / "evidence/design-validation.json"
            design_content = design_path.read_text(encoding="utf-8")
            design_path.write_text("{}", encoding="utf-8")
            evidence_codes = {item["code"] for item in validate_artifacts(data, root, report_path).errors}
            self.assertTrue({"E_SEED_REPLAY_EVIDENCE", "E_DESIGN_EVIDENCE"} <= evidence_codes)
            design_path.write_text(design_content, encoding="utf-8")
            play_path = root / "evidence/play-validation.json"
            play_content = play_path.read_text(encoding="utf-8")
            play_path.write_text("{}", encoding="utf-8")
            browser_manifest["evidence_hashes"]["evidence/play-validation.json"] = sha256_file(play_path)
            manifest_path.write_text(json.dumps(browser_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            play_codes = {item["code"] for item in validate_artifacts(data, root, report_path).errors}
            self.assertIn("E_PLAY_EVIDENCE", play_codes)
            play_path.write_text(play_content, encoding="utf-8")
            browser_manifest["evidence_hashes"]["evidence/play-validation.json"] = sha256_file(play_path)
            manifest_path.write_text(json.dumps(browser_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SKILL_ROOT / "scripts/validate_pipeline_report.py"),
                    str(report_path),
                    "--artifact-root",
                    str(root),
                    "--require-passed",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            output = json.loads(completed.stdout)
            self.assertEqual(completed.returncode, 0)
            self.assertTrue(output["mode_passed"])
            self.assertTrue(output["deliverable"])

            browser_manifest["evidence_hashes"]["evidence/start.png"] = "sha256:" + "0" * 64
            manifest_path.write_text(json.dumps(browser_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            manifest_codes = {item["code"] for item in validate_artifacts(data, root, report_path).errors}
            self.assertIn("E_BROWSER_MANIFEST", manifest_codes)
            browser_manifest["evidence_hashes"]["evidence/start.png"] = sha256_file(root / "evidence/start.png")
            manifest_path.write_text(json.dumps(browser_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

            proxy_raw = "evidence/proxy-manifest.json"
            proxy_path = root / proxy_raw
            proxy_path.write_text('{"manifest_version":"proxy"}', encoding="utf-8")
            proxy_data = copy.deepcopy(data)
            proxy_data["artifacts"]["evidence"].append(proxy_raw)
            next(gate for gate in proxy_data["hard_gates"] if gate["id"] == "h_boot")["evidence"] = [proxy_raw]
            proxy_browser_manifest = copy.deepcopy(browser_manifest)
            proxy_browser_manifest["gate_results"]["h_boot"]["evidence"] = [proxy_raw]
            proxy_browser_manifest["evidence_hashes"][proxy_raw] = sha256_file(proxy_path)
            manifest_path.write_text(json.dumps(proxy_browser_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            proxy_codes = {item["code"] for item in validate_artifacts(proxy_data, root, report_path).errors}
            self.assertTrue({"E_BROWSER_MANIFEST", "E_GATE_VISUAL_EVIDENCE"} <= proxy_codes)
            manifest_path.write_text(json.dumps(browser_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

            input_events_path = root / "evidence/input-events.json"
            input_events_content = input_events_path.read_text(encoding="utf-8")
            input_events_path.write_text("{}", encoding="utf-8")
            browser_manifest["evidence_hashes"]["evidence/input-events.json"] = sha256_file(input_events_path)
            manifest_path.write_text(json.dumps(browser_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            assertion_codes = {item["code"] for item in validate_artifacts(data, root, report_path).errors}
            self.assertIn("E_BROWSER_ASSERTION", assertion_codes)
            input_events_path.write_text(input_events_content, encoding="utf-8")
            browser_manifest["evidence_hashes"]["evidence/input-events.json"] = sha256_file(input_events_path)
            manifest_path.write_text(json.dumps(browser_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

            design_value = json.loads(design_content)
            design_value["environment"]["viewport"]["width"] = 391
            design_path.write_text(json.dumps(design_value, ensure_ascii=False), encoding="utf-8")
            browser_manifest["evidence_hashes"]["evidence/design-validation.json"] = sha256_file(design_path)
            manifest_path.write_text(json.dumps(browser_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
            environment_codes = {item["code"] for item in validate_artifacts(data, root, report_path).errors}
            self.assertTrue({"E_SEED_REPLAY_EVIDENCE", "E_DESIGN_EVIDENCE"} <= environment_codes)
            design_path.write_text(design_content, encoding="utf-8")
            browser_manifest["evidence_hashes"]["evidence/design-validation.json"] = sha256_file(design_path)
            manifest_path.write_text(json.dumps(browser_manifest, ensure_ascii=False, indent=2), encoding="utf-8")

            missing_design = copy.deepcopy(data)
            del missing_design["design_validation"]
            missing_design["artifacts"]["report"] = "missing-design-report.json"
            missing_design_path = root / "missing-design-report.json"
            missing_design_path.write_text(json.dumps(missing_design, ensure_ascii=False, indent=2), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SKILL_ROOT / "scripts/validate_pipeline_report.py"),
                    str(missing_design_path),
                    "--artifact-root",
                    str(root),
                    "--require-passed",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            output = json.loads(completed.stdout)
            self.assertEqual(completed.returncode, 1)
            self.assertIn("E_DESIGN_VALIDATION", {item["code"] for item in output["errors"]})

            author_data = copy.deepcopy(data)
            author_data["run_mode"] = "author"
            author_data["artifacts"]["report"] = "author-report.json"
            author_path = root / "author-report.json"
            author_path.write_text(json.dumps(author_data, ensure_ascii=False, indent=2), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SKILL_ROOT / "scripts/validate_pipeline_report.py"),
                    str(author_path),
                    "--artifact-root",
                    str(root),
                    "--require-passed",
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            output = json.loads(completed.stdout)
            self.assertEqual(completed.returncode, 0)
            self.assertTrue(output["mode_passed"])
            self.assertFalse(output["deliverable"])


if __name__ == "__main__":
    unittest.main()
