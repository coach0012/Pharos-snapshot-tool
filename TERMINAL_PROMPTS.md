# Pharos Snapshot Tool - Terminal

Use these prompts in Codex, Claude Code, OpenClaw, or another Agent Center-compatible terminal agent.

The agent should select `pharos-snapshot-tool` when the user asks for a Pharos snapshot, holder list, wallet activity list, contract activity list, or campaign eligibility export.

## Prompt Templates

### # 1. ERC-20 Holder Snapshot

```text
Take an ERC-20 holder snapshot for token {token_addr} on the Pharos {network_display_en}. Scan from block {from_block} to block {to_block}. Export CSV, JSON, and XLSX.
```

Agent action:

```bash
python scripts/live_erc20_snapshot.py --contract {token_addr} --from-block {from_block} --to-block {to_block} --min-balance 0 --output out/erc20_holder_snapshot --formats csv,json,xlsx
```

### # 2. ERC-20 Holder Snapshot With Minimum Balance

```text
Take an ERC-20 holder snapshot for token {token_addr} on the Pharos {network_display_en}. Only include wallets with at least {min_balance} tokens. Scan from block {from_block} to block {to_block}. Export CSV, JSON, and XLSX.
```

Agent action:

```bash
python scripts/live_erc20_snapshot.py --contract {token_addr} --from-block {from_block} --to-block {to_block} --min-balance {min_balance} --output out/erc20_holder_snapshot --formats csv,json,xlsx
```

### # 3. USDC Real Demo Snapshot

```text
Take a real USDC holder snapshot on Pharos Atlantic Testnet from block 23020000 to block 23022313. Export CSV, JSON, and XLSX.
```

Agent action:

```bash
python scripts/live_erc20_snapshot.py --contract 0xE0BE08c77f415F577A1B3A9aD7a1Df1479564ec8 --from-block 23020000 --to-block 23022313 --min-balance 0 --output out/usdc_real_snapshot --formats csv,json,xlsx
```

Expected result:

```text
holder count
candidate wallet count
total token balance
CSV output file
JSON output file
XLSX output file
```

### # 4. Contract Activity Plan

```text
Prepare a contract activity snapshot plan for contract {contract_addr} on the Pharos {network_display_en}. Scan from block {from_block} to block {to_block}. Export CSV.
```

Agent action:

```bash
python scripts/snapshot_plan.py --type contract-activity --contract {contract_addr} --from-block {from_block} --to-block {to_block} --output csv
```

### # 5. Wallet Activity Plan

```text
Prepare a wallet activity snapshot plan for wallets {wallet_addrs} on the Pharos {network_display_en}. Scan from block {from_block} to block {to_block}. Export CSV and JSON.
```

Agent action:

```bash
python scripts/snapshot_plan.py --type wallet-activity --wallets {wallet_addrs} --from-block {from_block} --to-block {to_block} --output csv,json
```

### # 6. Campaign Eligibility Snapshot Plan

```text
Prepare a campaign eligibility snapshot for token {token_addr} on the Pharos {network_display_en}. Include wallets with at least {min_balance} tokens. Use target block {target_block}. Export CSV, JSON, and XLSX.
```

Agent action:

```bash
python scripts/snapshot_plan.py --type campaign-eligibility --contract {token_addr} --target-block {target_block} --min-balance {min_balance} --output csv,json,xlsx
```

### # 7. Probe Contract Before Snapshot

```text
Check if contract {contract_addr} exists on Pharos Atlantic Testnet before taking a snapshot.
```

Agent action:

```bash
python scripts/rpc_probe.py --contract {contract_addr}
```

### # 8. Export Existing Snapshot Rows

```text
Export the snapshot rows from {input_json} to CSV, JSON, and XLSX for contract {contract_addr}.
```

Agent action:

```bash
python scripts/export_snapshot.py --input {input_json} --output out/exported_snapshot --snapshot-type erc20-holders --contract {contract_addr} --block {target_block} --formats csv,json,xlsx
```

## Safety Behavior

The agent must say this before running live snapshot commands:

```text
This is a read-only Pharos snapshot. It does not use a private key, does not sign anything, and does not send transactions.
```

For large ranges, the agent should warn:

```text
This is a range-based holder snapshot. It finds wallets from Transfer events inside the selected block range. Use a smaller range for demos, or use the token creation block for a complete snapshot. Large block ranges can be slow or limited by the RPC provider.
```
