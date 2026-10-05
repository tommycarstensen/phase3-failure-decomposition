# Recover termination reason from the detailed-description field

These phase-3 trials were terminated/withdrawn/suspended but their short "whyStopped"
field was blank or uninformative (e.g. "Sponsor decision", "See detailed description").
Your job: read the FULL detailed-description text and recover the real reason.

Each input line has THREE tab-separated columns:
  NCT_ID <TAB> whyStopped_short <TAB> detailedDescription

Assign EACH trial to exactly ONE category key. Use these keys:

- `safety` — adverse events, toxicity, deaths, unacceptable risk/benefit for safety.
- `efficacy_futility` — lack of efficacy, futility, interim analysis showed no/insufficient benefit, did not meet endpoint.
- `efficacy_positive` — stopped EARLY because efficacy was ALREADY demonstrated / benefit boundary crossed / drug approved so trial no longer needed. A POSITIVE outcome.
- `enrollment` — slow/insufficient recruitment or accrual; could not enroll enough patients.
- `business_strategic` — sponsor business/strategic/commercial/portfolio decision, merger, program deprioritized for business reasons.
- `funding` — lack of funding/financial/budget, grant ended, sponsor insolvency.
- `covid` — COVID-19 / pandemic disruption.
- `regulatory` — regulatory authority action, FDA/EMA clinical hold, IRB/ethics halt, GCP action.
- `supply_manufacturing` — drug/comparator supply shortage, manufacturing or formulation problem.
- `external_evidence` — external developments made the trial obsolete: new data from another study, standard-of-care changed, competing product approved.
- `not_started` — trial was WITHDRAWN and never enrolled anyone for administrative/logistical reasons (site never opened, protocol replaced/merged, planning-stage cancellation) with NO scientific, safety, commercial, or funding cause stated.
- `other_operational` — PI departure, site closure, administrative, protocol amendment/redesign not covered above.
- `unclear` — use ONLY if the detailed description genuinely does NOT state a termination reason (e.g. it is just the protocol synopsis / objectives with no mention of why it stopped).

Rules:
- The whole point is to AVOID `unclear` when the detail actually explains the stop. Read carefully — the reason is often one sentence buried in an otherwise boilerplate protocol description.
- Pick the PRIMARY cause when several appear.
- Distinguish `efficacy_positive` (good news) from `efficacy_futility` (bad news).
