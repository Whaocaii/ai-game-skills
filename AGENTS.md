# Repository guidance

This is Whaocaii's AI game skill project. Work on the user's requested scope; do not expand a narrow edit into rebuilding all skills.

- Keep skill names, `catalog.json`, dependency links and README entries consistent.
- Do not introduce AI short-drama modules unless the user explicitly requests them.
- Preserve user-authored changes. The installer must never silently overwrite an existing skill.
- Write practical decision guidance, concrete examples and observable completion criteria.
- Explain whether a feature is workflow guidance, a tested script or a tested engine integration.
- Update CHANGELOG for behavior changes; preserve third-party attribution when introducing external material.
- Run `python3 scripts/validate.py` and relevant tests. Actual gameplay or model quality needs separate evidence.
- Do not publish or push unrelated changes without task authorization.
