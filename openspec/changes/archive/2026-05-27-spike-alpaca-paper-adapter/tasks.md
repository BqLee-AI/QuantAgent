## Status

- [x] OpenSpec-only review is required before implementation.
- [x] Implementation is blocked until #157 `add-broker-simulator-test-harness-v1` is complete and its harness assets are available.
- [x] No API, runtime adapter, plugin, registry, wallet persistence, dependency or external network work may start before this change's OpenSpec PR is approved or explicitly marked “没问题”.

## Graph Overview

Critical path: `R0 -> B0 -> B1 -> B2 -> P1/P2 -> M0 -> V0 -> PR0`; if optional paper order submit is implemented, insert `B3` after `P2` and before `M0`.

After `B2`, mock / recorded contract tests (`P1`) and default-skip external smoke wiring (`P2`) may proceed in parallel because their write boundaries are separate. Paper order submit smoke (`B3`) remains serial after read-only smoke config is stable because it adds bounded write-side external behavior.

## Review Checkpoints

- [x] R0: OpenSpec-only review gate. Inputs: issue #158, this change's proposal/design/spec/tasks. Outputs: approved or explicitly accepted OpenSpec-only PR. Write boundary: `openspec/changes/spike-alpaca-paper-adapter/**`. Dependencies: none. Validation: `openspec validate spike-alpaca-paper-adapter --type change --strict --json`.
- [x] R1: Contract drift checkpoint. Inputs: #157 harness assets and Alpaca field mapping findings. Outputs: decision that all Alpaca fields can map to #157 contract, or a follow-up issue/OpenSpec for gaps. Write boundary: implementation notes or PR description only unless a new OpenSpec is required. Dependencies: `B1`, `P1`. Validation: reviewer can trace every wallet ingestion field to #157 or a deferred gap.

## Blocking Serial Path

- [x] B0: Confirm #157 dependency. Inputs: `openspec/changes/add-broker-simulator-test-harness-v1/**`, `packages/core/tests/wallet_broker_simulator_harness.py`, `packages/core/tests/test_wallet_broker_simulator_harness.py`, `packages/core/tests/README.md`. Outputs: implementation notes naming the exact #157 assets reused: `BrokerSimulatorHarness`, `BrokerSimulatorFixture`, `BrokerSimulatorOrderInput`, `BrokerSimulatorExecutionInput.source_key`, `BrokerSimulatorErrorInput`, and `WalletService.ingest_paper_execution`. Write boundary: no production code; notes may live in test README or PR description. Dependencies: `R0`. Parallel eligibility: no, because all mapping work depends on this contract anchor. Validation: run the existing #157 harness test before starting Alpaca work.
- [x] B1: Freeze Alpaca spike configuration contract. Inputs: this design/spec and #157 contract anchor. Outputs: test/spike configuration names and defaults: `ALPACA_PAPER_BASE_URL`, `APCA_API_KEY_ID`, `APCA_API_SECRET_KEY`, `QUANTAGENT_ALPACA_PAPER_SMOKE`, `QUANTAGENT_ALPACA_PAPER_ORDER_SMOKE`, timeout, symbol whitelist, `notional <= 5 USD`, `quantity <= 1`. Write boundary: `packages/core/tests/**` only unless a minimal test helper module is already established there. Dependencies: `B0`. Parallel eligibility: no, because all smoke and mock tests consume these names. Validation: unit tests for missing env skip, URL guard, and redacted config display.
- [x] B2: Implement paper-only URL guard and redaction helper. Inputs: `B1` config contract. Outputs: deterministic helpers that accept only `https://paper-api.alpaca.markets`, redact API key, secret, account id, order id, client order id and raw third-party response bodies. Write boundary: `packages/core/tests/**`. Dependencies: `B1`. Parallel eligibility: no, because `P1`, `P2` and `B3` must share one guard/redaction behavior. Validation: local tests cover valid paper URL, invalid scheme/host/path, missing credentials, and redacted error output.

## Parallel Work After B2

- [x] P1: Mock / recorded contract mapping tests. Inputs: `B2`, #157 broker simulator harness, Alpaca response shapes captured as redacted fixtures or mock transport payloads. Outputs: deterministic no-network tests for account, cash, buying power, positions, orders, activities/fills, duplicate source key, authentication failure, invalid symbol, insufficient buying power and timeout/external unavailable. Write boundary: `packages/core/tests/**` mock/fixture/test files. Dependencies: `B2`. Parallel eligibility: yes, independent from live smoke implementation after shared config/guard exists. Validation: tests pass with no network, no credentials and no `.env`; fixtures contain only placeholder identifiers such as `acct_redacted`, `order_redacted_1`, `activity_redacted_1`.
- [x] P2: Default-skip read-only external smoke. Inputs: `B2`, Alpaca paper credentials supplied by environment only. Outputs: smoke tests that skip unless `QUANTAGENT_ALPACA_PAPER_SMOKE=1`, credentials exist and URL guard passes; when enabled, they query paper account, positions and orders without writing wallet state. Write boundary: `packages/core/tests/**` smoke files and test README. Dependencies: `B2`. Parallel eligibility: yes, it does not modify mock fixtures or wallet ingestion mapping. Validation: skip-path test without credentials; optional manual run with credentials recorded only in PR notes.

## Serial Extension After P2

- [x] B3: Optional paper order submit smoke. Inputs: `P2`, order-specific flag `QUANTAGENT_ALPACA_PAPER_ORDER_SMOKE=1`, symbol whitelist and order upper bounds. Outputs: order submit smoke that uses verified paper URL, generated `client_order_id`, `notional <= 5 USD` or `quantity <= 1`, and only asserts submission/query status, not fill. Write boundary: `packages/core/tests/**` smoke files and README. Dependencies: `P2`. Parallel eligibility: no, because it depends on read-only smoke config and adds the only external write-side paper behavior. Validation: skip-path tests cover missing order flag, disallowed symbol, invalid URL and oversized notional/quantity; optional manual run records whether a paper order was submitted.

## Merge / Integration Nodes

- [x] M0: Contract convergence review. Inputs: `P1`, `P2`, optional `B3`, and #157 harness results. Outputs: one coherent mapping statement: Alpaca account/position/order/activity fields either map to #157 contract, are recorded as broker context only, or are deferred as gaps. Write boundary: test README, implementation notes, or PR description; no stable spec changes unless a separate OpenSpec is opened. Dependencies: `P1`, `P2`, optional `B3`. Validation: reviewer can verify no live endpoint, secret, account id, order id or raw third-party response is present in tracked files.

## Validation Nodes

- [x] V0: OpenSpec validation after any artifact edits. Command: `openspec validate spike-alpaca-paper-adapter --type change --strict --json`. Dependencies: every OpenSpec artifact edit. Expected result: valid change with zero issues.
- [x] V1: Core harness regression. Command: `uv run --package quantagent-core python -m unittest discover -s packages/core/tests -p 'test_wallet_broker_simulator_harness.py'`. Dependencies: `B0` before Alpaca implementation and `M0` after integration. Expected result: #157 contract still passes.
- [x] V2: Alpaca mock / skip-path tests. Command: use the narrow unittest pattern added for Alpaca spike tests under `packages/core/tests/**`. Dependencies: `P1`, `P2`, `B3` if implemented. Expected result: no network, no credentials and no `.env` required.
- [ ] V3: Optional external Alpaca paper smoke. Command: documented in README with required environment variables. Dependencies: `P2`, optional `B3`. Expected result: PR notes state whether read-only smoke ran, whether order submit smoke ran, and why any external validation was skipped.

## Multi-Agent Plan

- [x] Single-owner delivery is preferred until `B2` is complete because config names, URL guard and redaction are shared by every slice.
- [ ] After `B2`, `P1` and `P2` may be delegated to separate agents only if their write boundaries are disjoint test files under `packages/core/tests/**` and one owner performs `M0`.
- [ ] Do not delegate `B3` until `P2` is merged, because order submit smoke consumes the same external smoke configuration and has higher trading-safety risk.

## PR Readiness

- [x] PR0: Implementation PR description links issue #158 and this change, states #157 dependency status, lists validation commands and results, states whether Alpaca paper was contacted, states whether a paper order was submitted, and explicitly repeats that live trading, official plugin support, `packages/adapters` promotion, broker snapshot and reconciliation are out of scope.
