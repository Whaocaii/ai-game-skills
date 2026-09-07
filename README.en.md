# AI Game Skills

[中文](README.md) · English · [Machine-readable catalog](catalog.json)

**Maintainer: Whaocaii · MIT License · Version: 0.2.1**

24 agent skills for AI-assisted game design and development: game balancing, game economy, HTML5/H5 quick-time events (QTE), natural-language player actions, combat feel, inventory, stamina and survival crafting UI.

Instructions are primarily Chinese, with bilingual skill descriptions. The repository contains workflow guidance, Python QTE validators and JavaScript free-input examples. Complete game generation, engine integrations and live-model quality require project-specific verification; this is not a bundled game engine or hosted LLM service.

## Install and use

Requires Git and Python 3.9+. JavaScript examples and tests require Node.js 18+.

```bash
git clone https://github.com/Whaocaii/ai-game-skills.git
cd ai-game-skills
python3 scripts/install.py --list
python3 scripts/install.py build-instant-qte-h5 free-input-output
# Preview or install all 24 skills
python3 scripts/install.py all --dry-run
python3 scripts/install.py all
```

The installer targets `${CODEX_HOME}/skills`, or `~/.codex/skills` when unset, and refuses to overwrite existing skills. Start a new Codex session after installation. Other agents can read the Markdown entrypoints directly; automatic discovery and tool compatibility depend on the client and have not been verified across clients.

Example requests:

```text
Use $build-instant-qte-h5 to build a mobile HTML5 quick-time event game.
Require real player input, failure and retry flows, and browser playtest evidence.

Use $free-input-output to add natural-language player actions to this game.
Keep the existing result schema; handle timeouts, duplicate submissions and stale responses.

Use $number-tower-defense-like to diagnose an unfair difficulty spike in wave 5.
```

## Skill directory

| Skill | Capability and matching use case |
| --- | --- |
| [build-instant-qte-h5](skills/build-instant-qte-h5/SKILL.md) | Build and validate mobile HTML5 quick-time event (QTE) games with real player input and browser playtest evidence. |
| [build-pseudo-live2d-character](skills/build-pseudo-live2d-character/SKILL.md) | Plan browser character animation from a single illustration: breathing, blinking and layered motion; not a Cubism model generator. |
| [day-night-cycle](skills/day-night-cycle/SKILL.md) | Design day-night lighting, weather transitions and readable environmental colors. |
| [day-time-system](skills/day-time-system/SKILL.md) | Design game time, time scale, pause, day rollover and offline progression; use for simulation logic. |
| [fps-feel](skills/fps-feel/SKILL.md) | Improve FPS shooting feel: recoil, spread, hit feedback and reload timing. |
| [free-input-output](skills/free-input-output/SKILL.md) | Integrate natural-language player actions with LLM result validation, timeouts, duplicate-submit protection and atomic settlement; not just chat UI. |
| [game-skill-router](skills/game-skill-router/SKILL.md) | Select the smallest relevant game design, balancing, systems or game-feel skill set for a concrete task. |
| [improve-arpg-hit-feel](skills/improve-arpg-hit-feel/SKILL.md) | Diagnose melee combat responsiveness, hit impact, hit reactions and recovery timing. |
| [inventory-system](skills/inventory-system/SKILL.md) | Design inventory capacity, item identity, atomic transactions, equipment exchange and persistence. |
| [number-adventure-like](skills/number-adventure-like/SKILL.md) | Balance adventure, platformer and puzzle levels through checkpoints, resource pressure and progression. |
| [number-card-roguelike](skills/number-card-roguelike/SKILL.md) | Balance deckbuilding roguelikes: card draw, energy costs, deck choices and combat rewards. |
| [number-diablo-arpg-like](skills/number-diablo-arpg-like/SKILL.md) | Balance loot-driven action RPG damage, survivability, equipment upgrades and drop rewards. |
| [number-legend-like](skills/number-legend-like/SKILL.md) | Balance long-term RPG progression, upgrades, loot, trading and competitive power tiers. |
| [number-orchestrator](skills/number-orchestrator/SKILL.md) | Turn game experience goals into numerical models, tunable parameters and balance experiments. |
| [number-shared](skills/number-shared/SKILL.md) | Review units, probability, distributions, bounds and sensitivity in game balance formulas. |
| [number-shmup-like](skills/number-shmup-like/SKILL.md) | Balance shoot-em-up bullet patterns, dodgeability, firepower, survivability and scoring. |
| [number-sim-management-like](skills/number-sim-management-like/SKILL.md) | Balance management simulations, factories and idle games through production bottlenecks, inventory and expansion returns. |
| [number-survivor-like](skills/number-survivor-like/SKILL.md) | Balance survivor-like horde pressure, upgrade pacing and in-run builds. |
| [number-tower-defense-like](skills/number-tower-defense-like/SKILL.md) | Balance tower defense waves, path exposure, targeting, coverage and resource budgets. |
| [number-turn-card-like](skills/number-turn-card-like/SKILL.md) | Balance turn-based card RPG action economy, speed order, character growth and team composition. |
| [scene-transition](skills/scene-transition/SKILL.md) | Implement or diagnose scene loading, input handoff, transition effects and failure recovery. |
| [screen-shake-effects](skills/screen-shake-effects/SKILL.md) | Design camera shake, hit-stop and impact feedback with stacking limits and reduced-motion settings. |
| [stamina-system](skills/stamina-system/SKILL.md) | Design stamina costs, regeneration, caps, offline recovery and duplicate-request handling. |
| [survival-ui-guidelines](skills/survival-ui-guidelines/SKILL.md) | Design and review survival game HUD, inventory, crafting and building interfaces. |

## Structured discovery

[catalog.json](catalog.json) lists each skill's Chinese title, English title and description, search keywords, relative entrypoint path and installation dependencies. These are repository-specific metadata fields for tools that choose to read them, not a claim of universal automatic indexing. Read the selected `SKILL.md` before applying its workflow.

## Validation and credentials

```bash
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s skills/build-instant-qte-h5/tests -v
node --test skills/free-input-output/tests/test-free-input.cjs
```

Local tests and examples require no API key. Real model credentials belong on the application server, never in browser code or the repository. See [SECURITY.md](SECURITY.md) and [validation scope](VALIDATION.md).

## License and attribution

[MIT License](LICENSE). Preserve the required copyright and permission notice. Cite Whaocaii, the repository URL, the skill name and a full commit SHA when referencing a specific version. See [development notes](DEVELOPMENT.md), [contribution guidance](CONTRIBUTING.md) and [changelog](CHANGELOG.md).
