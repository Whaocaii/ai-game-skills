#!/usr/bin/env python3
"""Install local game skills and dependencies; existing destinations are protected."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]


def select(names):
    data = json.loads((ROOT / 'catalog.json').read_text(encoding='utf-8'))
    selected = set()
    visiting = set()

    def visit(name):
        if name in visiting:
            raise ValueError(f'Dependency cycle at {name}')
        if name in selected:
            return
        if name not in data['skills']:
            raise ValueError(f'Unknown skill: {name}')
        if Path(name).name != name or not (ROOT / 'skills' / name / 'SKILL.md').is_file():
            raise ValueError(f'Invalid skill directory: {name}')
        visiting.add(name)
        for dep in data['skills'][name]['dependencies']:
            visit(dep)
        visiting.remove(name)
        selected.add(name)

    for name in names:
        if name == 'all':
            members = data['skills']
        elif name in data['groups']:
            members = data['groups'][name]
        else:
            members = [name]
        for item in members:
            visit(item)
    return sorted(selected)


def copy_skills(names, destination):
    conflicts = [n for n in names if os.path.lexists(destination / n)]
    if conflicts:
        raise ValueError('Existing directories must be backed up and moved first: ' + ', '.join(conflicts))
    for name in names:
        source = ROOT / 'skills' / name
        if source.is_symlink() or any(p.is_symlink() for p in source.rglob('*')):
            raise ValueError(f'Refusing symlink in source: {name}')
    destination.mkdir(parents=True, exist_ok=True)
    for name in names:
        shutil.copytree(ROOT / 'skills' / name, destination / name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('names', nargs='*', help='Skill names, games, or all')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--dest', type=Path, default=Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'skills')
    args = parser.parse_args()
    if args.list:
        print('\n'.join(select(['all'])))
        return 0
    if not args.names:
        parser.error('Specify a skill, games, or all; use --list to inspect the catalog.')
    try:
        names = select(args.names)
        destination = args.dest.expanduser().resolve()
        print('Destination:', destination)
        print('Selected:', ', '.join(names))
        if not args.dry_run:
            copy_skills(names, destination)
            print(f'Installed {len(names)} skills. Start a new agent session.')
        return 0
    except (OSError, ValueError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
