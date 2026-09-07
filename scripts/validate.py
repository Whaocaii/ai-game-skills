#!/usr/bin/env python3
"""Validate catalog structure, dependencies, names and Markdown file links."""
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def validate():
    errors = []
    data = json.loads((ROOT / 'catalog.json').read_text(encoding='utf-8'))
    known = set(data['skills'])
    actual = {p.name for p in (ROOT / 'skills').iterdir() if p.is_dir()}
    if known != actual:
        errors.append(f'Catalog/directory mismatch: {sorted(known ^ actual)}')
    for group, names in data['groups'].items():
        for name in names:
            if name not in known:
                errors.append(f'Unknown group member: {group}/{name}')
    for name, entry in data['skills'].items():
        p = ROOT / 'skills' / name / 'SKILL.md'
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name):
            errors.append(f'Invalid name: {name}')
        if not p.is_file():
            errors.append(f'Missing entry: {name}')
            continue
        text = p.read_text(encoding='utf-8')
        fm = re.match(r'^---\n(.*?)\n---\n', text, re.S)
        if not fm or not re.search(r'^name: '+re.escape(name)+r'$', fm.group(1), re.M):
            errors.append(f'Invalid frontmatter name: {name}')
        if not fm or not re.search(r'^description: .+', fm.group(1), re.M):
            errors.append(f'Missing description: {name}')
        for dep in entry['dependencies']:
            if dep not in known:
                errors.append(f'Missing dependency: {name} -> {dep}')
    done, pending = set(), set()

    def walk(name):
        if name in pending:
            errors.append(f'Dependency cycle: {name}')
            return
        if name in done or name not in known:
            return
        pending.add(name)
        for dep in data['skills'][name]['dependencies']:
            walk(dep)
        pending.remove(name)
        done.add(name)

    for name in known:
        walk(name)
    for p in ROOT.rglob('*.md'):
        if '.git' in p.parts:
            continue
        for target in re.findall(r'\]\(([^)]+)\)', p.read_text(encoding='utf-8')):
            target = target.split('#', 1)[0]
            if not target or re.match(r'[a-z]+://|mailto:', target):
                continue
            if not (p.parent / unquote(target)).exists():
                errors.append(f'Broken link in {p.relative_to(ROOT)}: {target}')
    return errors


if __name__ == '__main__':
    problems = validate()
    for problem in problems:
        print(problem, file=sys.stderr)
    print('PASS' if not problems else 'FAIL')
    sys.exit(bool(problems))
