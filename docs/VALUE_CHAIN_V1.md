# MatVerse Governed Value Chain v1

Status: `IMPLEMENTATION_CANDIDATE / NOT_CANONICAL_YET`

This module implements a narrow, fail-closed bridge between the historical MatVerse information ontology and the Captals economic layer.

## Scope

```text
MNB
  -> MemNanoBit
  -> MemBit
  -> MBit
  -> RightsObject
  -> CaptalsSnapshot
```

### Semantics

- **MNB**: event + minimum context/provenance.
- **MemNanoBit**: continuity and relations over an MNB.
- **MemBit**: formal, evidenced commitment under policy and authority.
- **MBit**: realized transformation/value derived only from a `PASS` MemBit.
- **RightsObject**: delimited rights over an artifact; may exist before value realization, but settlement requires an MBit.
- **Captals**: economic metabolism over verified realized value and rights. It is not a currency, token, exchange, or universal pricing oracle.

## Invariants

1. `MBit` cannot be created from `HOLD`, `BLOCK`, or `ESCALATE` MemBit state.
2. A RightsObject referencing an MBit must reference the same MemBit lineage.
3. Rights can exist ex ante from a valid MemBit; realized-value settlement is ex post and requires an MBit.
4. Captals settlement does not mint tokens or infer market price.
5. Economic inputs are fail-closed for negative values and invalid royalty rates.
6. Every object exposes a deterministic canonical SHA-256 hash over its observable fields.

## Architectural boundary

This code does not modify the historical Ω score or Symbios execution engine. It is intentionally isolated until the ontology and runtime binding are reviewed.

Future integration should bind:

- `MemBit.decision_gate` to the real Trust Kernel / Ω-Gate decision receipt;
- `evidence_hash` to EvidenceOS / ProofPack;
- `signer_key_id` and `authority_scope` to the Registry;
- MBit milestones to execution receipts;
- Captals cost/risk/debt to measured instruments only;
- MMNB to the complete replayable envelope.

## Explicit HOLD

- tokenization / blockchain adapters;
- universal valuation formulas;
- automatic asset pricing;
- financial-instrument classification;
- claims that Captals is already calibrated in production.
