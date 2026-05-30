# Pharos Snapshot Tool

Read-only Agent Center skill for taking holder, owner, activity, and campaign eligibility snapshots on Pharos Atlantic Testnet.

## What It Does

This tool helps AI agents safely prepare and export public onchain snapshots without requesting private keys or sending transactions. It validates snapshot inputs, creates a transparent query plan, optionally probes contract bytecode through Pharos RPC, and exports fetched rows to CSV, JSON, and XLSX.

## Network

- Pharos Atlantic Testnet
- Chain ID: `688689`
- RPC: `https://atlantic.dplabs-internal.com`
- Explorer: `https://atlantic.pharosscan.xyz/`

## Install

No package install is required for planning or CSV/JSON/XLSX export. The XLSX writer uses only Python standard libraries.

For Agent Center style installation, see:

```text
AGENT_CENTER_GUIDE.md
```

For Agent Center terminal prompt examples, see:

```text
TERMINAL_PROMPTS.md
```

For a test-first video demo script, see:

```text
DEMO_TEST_FIRST.md
```

```bash
python scripts/snapshot_plan.py --help
python scripts/export_snapshot.py --help
python scripts/rpc_probe.py --help
python scripts/live_erc20_snapshot.py --help
```

## Usage

Create a holder snapshot plan:

```bash
python scripts/snapshot_plan.py --type erc20-holders --contract 0x0000000000000000000000000000000000000001 --target-block latest --min-balance 1 --output csv,json,xlsx
```

Export fetched rows:

```bash
python scripts/export_snapshot.py --input examples/sample_erc20_rows.json --output out/erc20_snapshot --snapshot-type erc20-holders --contract 0x0000000000000000000000000000000000000001 --block latest --formats csv,json,xlsx
```

Confirm whether a contract has bytecode:

```bash
python scripts/rpc_probe.py --contract 0x0000000000000000000000000000000000000001
```

Take a real ERC-20 holder snapshot from Pharos RPC:

```bash
python scripts/live_erc20_snapshot.py --contract 0xE0BE08c77f415F577A1B3A9aD7a1Df1479564ec8 --from-block 23020000 --to-block 23022313 --min-balance 0 --output out/usdc_real_snapshot --formats csv,json,xlsx
```

This live command:

- checks the RPC chain ID is Pharos Atlantic Testnet
- checks the contract has bytecode
- scans ERC-20 `Transfer` logs
- finds sender and receiver wallets
- calls `balanceOf` for each wallet
- exports real holder rows

For a complete snapshot, use the token creation block or earliest known activity block as `--from-block`. For a quick demo, use a smaller fixed range like the command above.

## Supported Snapshot Types

- `erc20-holders`
- `erc721-owners`
- `erc1155-balances`
- `contract-activity`
- `wallet-activity`
- `campaign-eligibility`

## Submission Notes

- Skill name: Pharos Snapshot Tool
- Supported framework: Codex / Pharos Agent Center style skills
- Dependencies: Python 3.10 or newer
- Safety posture: read-only, no private keys, no signing, no transaction sending
- Agent install guide: `AGENT_CENTER_GUIDE.md`
- Terminal prompt guide: `TERMINAL_PROMPTS.md`
- Test-first demo script: `DEMO_TEST_FIRST.md`
