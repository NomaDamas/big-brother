# Compliance Boundary

`big-brother` is compliance-support tooling. It is not legal advice, does not
replace Korean counsel, and does not promise that an operator's deployment
meets any statute, decree, regulator notice, or platform-specific obligation.

The project separates statutory-support workflows from operator moderation
policy:

- `known_illegal_match`: deterministic matching against an operator-authorized
  hash list or official feed.
- `regulatory_review_match`: matching against material reviewed through an
  authorized regulator or partner process.
- `policy_model_signal`: optional model output used for review routing or
  operator policy enforcement.
- `human_decision`: an auditable operator action, override, appeal result, or
  deletion/report workflow state.

Unknown-content model output is not an illegality finding. Model signals must
route to review or policy handling unless a human or authorized known-content
source makes the relevant decision.

## Legal source table

| Source | Date checked | Why it matters |
| --- | --- | --- |
| law.go.kr Telecommunications Business Act and related Enforcement Decree pages | 2026-06-07 | Baseline for covered-operator technical and administrative measure references, deletion/report workflow, and operation-management logs. |
| Korea policy briefing on illegal filming distribution prevention measures | 2026-06-07 | Notes public DNA/filtering support and operator duties discussed in Korean government communications. |
| GeekNews topic 30222 | 2026-06-07 | Community summary of the July 2026 concern around image/video scanning cost and deployment pressure. |
| Privacy Guides community thread 38341 | 2026-06-07 | English-language community discussion raising privacy, censorship, and hardware-cost concerns. |

## Operator responsibilities

- Confirm whether the service is legally covered before deployment.
- Confirm whether an official or performance-evaluated filtering technology is
  required for the operator's exact service category.
- Import only authorized hash lists with source, authority, version, received
  date, revocation, and retention metadata.
- Avoid storing original images unless a documented retention and access-control
  policy requires it.
- Provide user notice, deletion/report workflow support, review records, and
  appeal handling where the operator's policy or law requires them.
- Keep audit records for ingest, scan, match, model signal, decision, override,
  policy change, deletion request, and report workflow events.

## Legal review checklist

- [ ] Confirm covered-business applicability.
- [ ] Confirm current statute, decree, and regulator notice versions.
- [ ] Confirm whether official filtering technology or performance evaluation is
      mandatory.
- [ ] Confirm the operator is authorized to receive each imported hash source.
- [ ] Confirm retention periods for hash entries, audit logs, quarantined media,
      and human review records.
- [ ] Confirm user notice, deletion request, report, review, and appeal flows.
- [ ] Confirm false-positive handling and emergency override procedures.
- [ ] Confirm model and dependency licenses before production use.

## Privacy and security defaults

- Local-only processing by default.
- No default telemetry.
- Redacted audit records.
- No bundled real illegal media.
- No bundled restricted hash lists.
- No silent model-weight downloads.

