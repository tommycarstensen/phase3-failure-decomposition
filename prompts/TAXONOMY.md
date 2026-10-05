# whyStopped classification taxonomy

You are classifying the free-text "why was this phase-3 trial stopped early" field
from ClinicalTrials.gov. Assign EACH trial to EXACTLY ONE category below. Pick the
single dominant reason. Use the category KEY (lowercase, left column) verbatim.

- `safety` — adverse events, toxicity, deaths, unacceptable side effects, negative benefit-risk/risk-benefit for SAFETY reasons, DSMB stop for safety.
- `efficacy_futility` — lack of efficacy, futility, did not meet endpoint, interim analysis showed no/insufficient benefit, unlikely to succeed, negative benefit-risk driven by LACK of efficacy.
- `efficacy_positive` — stopped EARLY because efficacy was ALREADY demonstrated / benefit crossed the pre-specified boundary / overwhelming efficacy. This is a POSITIVE outcome, not a failure. Also: drug got approved/endpoint met so trial no longer needed.
- `enrollment` — slow, insufficient, or failed recruitment/accrual; could not enroll enough patients; low enrollment.
- `business_strategic` — sponsor business/strategic/commercial decision, portfolio reprioritization, company merger/acquisition, "sponsor decision" tied to strategy, program discontinued for business reasons.
- `funding` — lack of funding, financial reasons, budget, grant ended, sponsor insolvency/bankruptcy.
- `covid` — COVID-19 / pandemic-related disruption.
- `regulatory` — regulatory authority action: FDA/EMA clinical hold, regulatory hold, IRB/ethics-committee halt, GCP/compliance action.
- `supply_manufacturing` — drug supply shortage, manufacturing problem, product/comparator unavailable, formulation/stability issue.
- `external_evidence` — external developments made the trial obsolete: new data from another study, standard-of-care changed, a competing/better product approved, another trial answered the question.
- `other_operational` — PI departure, site closure, administrative, protocol amendment/redesign, logistical, "study design" changes, merged into another protocol — operational reasons not covered above.
- `unclear` — uninformative or ambiguous text that does not state a real reason: e.g. "sponsor decision" (no reason), "terminated", "study stopped", "see summary", "administrative reasons" with no detail, "-", "N/A", or text you genuinely cannot map.

Rules:
- One category per trial. When two reasons appear, pick the PRIMARY/first-stated cause.
- "Business decision" WITH a stated strategic/portfolio/commercial reason → `business_strategic`. A bare "sponsor decision" with no reason → `unclear`.
- Do not confuse `efficacy_positive` (good news, benefit shown) with `efficacy_futility` (bad news, no benefit). Read carefully.
