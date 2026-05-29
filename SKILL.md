---
name: pharos-snapshot-tool
description: Read-only Pharos Agent Center skill for preparing and exporting ERC-20 holder, NFT owner, ERC-1155 balance, contract activity, wallet activity, and campaign eligibility snapshots on Pharos Atlantic Testnet.
---

# Pharos Snapshot Tool

Use this Skill when a user wants a read-only snapshot of public onchain data on Pharos Atlantic Testnet. It prepares safe query plans, validates addresses and block ranges, probes contracts with read-only RPC calls, and exports snapshot rows to CSV, JSON, or XLSX.

## Network

- Network: Pharos Atlantic Testnet
- Chain ID: `688689`
- RPC: `https://atlantic.dplabs-internal.com`
- Explorer: `https://atlantic.pharosscan.xyz/`
- Native token: PHRS

## Supported Snapshot Types

- `erc20-holders`: ERC-20 holder balances at a target block.
- `erc721-owners`: NFT owner/token ID rows at a target block.
- `erc1155-balances`: ERC-1155 owner balances for selected token IDs.
- `contract-activity`: event activity for a contract across a block range.
- `wallet-activity`: event activity for one or more wallets across a block range.
- `campaign-eligibility`: eligibility rows based on balance or activity rules.

## Safety Rules

- Never ask for private keys, seed phrases, signatures, or wallet approvals.
- Never send transactions or prepare signed payloads.
- Never modify balances, approvals, or contract state.
- Show all filters before exporting results.
- Validate every address, block value, output format, and activity range.
- Warn users that RPC-only scans can miss historical data when the provider limits old logs.

## Workflow

1. Ask for the snapshot type and required inputs.
2. Run `scripts/snapshot_plan.py` to validate inputs and produce the read-only plan.
3. For contract snapshots, run `scripts/rpc_probe.py --contract <address>` to confirm deployed bytecode when network access is available.
4. Show the plan preview, including filters, warnings, and estimated query size.
5. Fetch rows with read-only RPC or explorer queries.
6. Export rows with `scripts/export_snapshot.py`.

## Examples

Prepare an ERC-20 holder snapshot plan:

```bash
python scripts/snapshot_plan.py --type erc20-holders --contract 0x0000000000000000000000000000000000000001 --target-block latest --min-balance 1 --output csv,json,xlsx
```

Prepare a contract activity plan:

```bash
python scripts/snapshot_plan.py --type contract-activity --contract 0x0000000000000000000000000000000000000001 --from-block 1000 --to-block 2500 --output csv
```

Probe a contract with read-only RPC:

```bash
python scripts/rpc_probe.py --contract 0x0000000000000000000000000000000000000001
```

Export rows:

```bash
python scripts/export_snapshot.py --input examples/sample_erc20_rows.json --output out/erc20_snapshot --snapshot-type erc20-holders --contract 0x0000000000000000000000000000000000000001 --block latest --formats csv,json,xlsx
```

## Output Schema

- `status`: `safe`, `review`, or `unsafe`
- `snapshot_type`
- `network`
- `contracts`
- `target_block` or `block_range`
- `filters`
- `estimated_query_size`
- `warnings`
- `output_formats`
- `summary`

