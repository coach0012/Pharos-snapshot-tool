# Agent Center Install Guide

This file explains how to use **Pharos Snapshot Tool** as a skill in the Agent Center style.

## 1. Skill File Storage Path

### Codex

Copy this skill folder into:

```text
~/.codex/skills/pharos-snapshot-tool/
```

The important file is:

```text
~/.codex/skills/pharos-snapshot-tool/SKILL.md
```

Keep the `scripts` folder beside `SKILL.md`, because the skill instructions call those scripts.

### Claude Code

Copy this skill folder into:

```text
~/.claude/skills/pharos-snapshot-tool/
```

Claude Code can load the skill from the skills directory or from a project-level skill folder.

### OpenClaw

Copy this skill folder into:

```text
~/.openclaw/skills/pharos-snapshot-tool/
```

OpenClaw can also load project-specific skills from the project root.

## 2. Verify Skill Installation

### Codex

Start a new Codex session and type:

```text
/skills
```

Look for:

```text
pharos-snapshot-tool
```

### Claude Code

Start Claude Code and type:

```text
/skills
```

Look for:

```text
pharos-snapshot-tool
```

### OpenClaw

Run:

```bash
openclaw skills list
```

Look for:

```text
pharos-snapshot-tool
```

## 3. How the Agent Uses the Skill

For ready-made terminal prompt examples, see:

```text
TERMINAL_PROMPTS.md
```

### Step A: Write Your Prompt

Use normal words:

```text
Take an ERC-20 holder snapshot for USDC on Pharos Atlantic Testnet from block 23020000 to block 23022313 and export CSV, JSON, and XLSX.
```

### Step B: Agent Selects Skill

The agent should detect that this is a Pharos snapshot task.

It should say something like:

```text
Using pharos-snapshot-tool to prepare a read-only holder snapshot on Pharos Atlantic Testnet.
```

### Step C: Skill Executes

The agent follows `SKILL.md` and runs:

```bash
python scripts/live_erc20_snapshot.py --contract 0xE0BE08c77f415F577A1B3A9aD7a1Df1479564ec8 --from-block 23020000 --to-block 23022313 --min-balance 0 --output out/usdc_real_snapshot --formats csv,json,xlsx
```

The skill returns:

```text
holder count
total token balance
CSV output
JSON output
XLSX output
warnings, if any
```

## Safety

This skill is read-only.

It does not ask for a private key.

It does not ask for a seed phrase.

It does not sign anything.

It does not send transactions.

It only reads public onchain data from Pharos Atlantic Testnet.
