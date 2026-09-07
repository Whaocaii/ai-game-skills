#!/usr/bin/env python3
"""本 Skill 报告 Schema 所需的依赖无关 JSON Schema 子集校验器。

支持 Draft 2020-12 中本包实际使用的关键字：$ref、type、const、enum、
required、properties、additionalProperties、items、anyOf、allOf、pattern、
minLength、minItems、maxItems、uniqueItems、minimum 与 maximum。未知关键字不会被当作已验证约束；
因此修改报告 Schema 时，必须同时运行本包的回归测试。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SchemaError:
    path: str
    message: str


def _pointer(path: str, part: str | int) -> str:
    escaped = str(part).replace("~", "~0").replace("/", "~1")
    return f"/{escaped}" if path == "/" else f"{path}/{escaped}"


def _resolve_ref(root_schema: dict[str, Any], reference: str) -> Any:
    if not reference.startswith("#/"):
        raise ValueError(f"只支持本地 JSON Pointer $ref：{reference}")
    current: Any = root_schema
    for raw in reference[2:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        current = current[token]
    return current


def _is_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    raise ValueError(f"不支持的 schema type：{expected}")


def validate_schema(instance: Any, schema: dict[str, Any]) -> list[SchemaError]:
    errors: list[SchemaError] = []

    def visit(value: Any, rule: Any, path: str) -> None:
        if isinstance(rule, bool):
            if not rule:
                errors.append(SchemaError(path, "Schema 不允许该值。"))
            return
        if not isinstance(rule, dict):
            raise ValueError("Schema 节点必须是对象或布尔值。")

        if "$ref" in rule:
            visit(value, _resolve_ref(schema, rule["$ref"]), path)

        if "allOf" in rule:
            for child in rule["allOf"]:
                visit(value, child, path)

        if "anyOf" in rule:
            branches = rule["anyOf"]
            matched = False
            for child in branches:
                branch_errors: list[SchemaError] = []
                original = len(errors)
                visit(value, child, path)
                branch_errors.extend(errors[original:])
                del errors[original:]
                if not branch_errors:
                    matched = True
                    break
            if not matched:
                errors.append(SchemaError(path, "值不符合 anyOf 中的任一分支。"))

        if "const" in rule and value != rule["const"]:
            errors.append(SchemaError(path, f"值必须等于 {json.dumps(rule['const'], ensure_ascii=False)}。"))
        if "enum" in rule and value not in rule["enum"]:
            errors.append(SchemaError(path, "值不在允许的枚举中。"))

        expected_type = rule.get("type")
        if expected_type is not None:
            allowed = [expected_type] if isinstance(expected_type, str) else expected_type
            if not any(_is_type(value, item) for item in allowed):
                errors.append(SchemaError(path, f"类型必须为 {' 或 '.join(allowed)}。"))
                return

        if isinstance(value, dict):
            properties = rule.get("properties", {})
            for required in rule.get("required", []):
                if required not in value:
                    errors.append(SchemaError(_pointer(path, required), "缺少必填字段。"))
            for key, child_value in value.items():
                if key in properties:
                    visit(child_value, properties[key], _pointer(path, key))
                elif rule.get("additionalProperties") is False:
                    errors.append(SchemaError(_pointer(path, key), "不允许额外字段。"))
                elif isinstance(rule.get("additionalProperties"), dict):
                    visit(child_value, rule["additionalProperties"], _pointer(path, key))

        if isinstance(value, list):
            if "minItems" in rule and len(value) < rule["minItems"]:
                errors.append(SchemaError(path, f"数组至少需要 {rule['minItems']} 项。"))
            if "maxItems" in rule and len(value) > rule["maxItems"]:
                errors.append(SchemaError(path, f"数组最多允许 {rule['maxItems']} 项。"))
            if rule.get("uniqueItems"):
                serialized = [json.dumps(item, ensure_ascii=False, sort_keys=True) for item in value]
                if len(serialized) != len(set(serialized)):
                    errors.append(SchemaError(path, "数组项必须唯一。"))
            if "items" in rule:
                for index, item in enumerate(value):
                    visit(item, rule["items"], _pointer(path, index))

        if isinstance(value, str):
            if "minLength" in rule and len(value) < rule["minLength"]:
                errors.append(SchemaError(path, f"字符串长度至少为 {rule['minLength']}。"))
            if "pattern" in rule and re.search(rule["pattern"], value) is None:
                errors.append(SchemaError(path, "字符串不符合 pattern。"))

        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in rule and value < rule["minimum"]:
                errors.append(SchemaError(path, f"数值不能小于 {rule['minimum']}。"))
            if "maximum" in rule and value > rule["maximum"]:
                errors.append(SchemaError(path, f"数值不能大于 {rule['maximum']}。"))

    visit(instance, schema, "/")
    return errors
