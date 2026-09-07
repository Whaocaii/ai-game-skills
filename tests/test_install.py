import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('installer', ROOT / 'scripts/install.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class InstallationTests(unittest.TestCase):
    def test_domain_dependencies(self):
        self.assertEqual(installer.select(['number-tower-defense-like']), ['number-orchestrator', 'number-shared', 'number-tower-defense-like'])

    def test_router_is_complete(self):
        self.assertEqual(installer.select(['game-skill-router']), installer.select(['all']))

    def test_no_drama_entries(self):
        self.assertFalse(any(n.startswith('novel-') or n == 'ai-short-drama' for n in installer.select(['all'])))

    def test_unknown_and_escape_names_rejected(self):
        for name in ['unknown', '../../secrets', '/tmp/skill']:
            with self.assertRaises(ValueError):
                installer.select([name])

    def test_copy_preserves_full_skill(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            names = installer.select(['game-skill-router'])
            installer.copy_skills(names, destination)
            for name in names:
                source = ROOT / 'skills' / name
                for file in source.rglob('*'):
                    if file.is_file():
                        self.assertEqual(file.read_bytes(), (destination / name / file.relative_to(source)).read_bytes())

    def test_conflict_blocks_all_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            destination = Path(directory)
            (destination / 'number-shared').mkdir()
            (destination / 'number-shared/keep').write_text('unchanged')
            with self.assertRaises(ValueError):
                installer.copy_skills(installer.select(['number-tower-defense-like']), destination)
            self.assertEqual([p.name for p in destination.iterdir()], ['number-shared'])
            self.assertEqual((destination / 'number-shared/keep').read_text(), 'unchanged')

    def test_dependency_cycle_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            for name in ['a', 'b']:
                p = temporary / 'skills' / name
                p.mkdir(parents=True)
                (p / 'SKILL.md').write_text('placeholder')
            (temporary / 'catalog.json').write_text(json.dumps({'groups': {}, 'skills': {'a': {'dependencies': ['b']}, 'b': {'dependencies': ['a']}}}))
            with patch.object(installer, 'ROOT', temporary):
                with self.assertRaisesRegex(ValueError, 'cycle'):
                    installer.select(['a'])


if __name__ == '__main__':
    unittest.main()
