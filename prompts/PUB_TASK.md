# Recover a phase-3 trial's termination reason from its linked publication

Each of these phase-3 trials was terminated/withdrawn/suspended early, but ClinicalTrials.gov
gave NO reason (blank or uninformative). You are given the trial's linked PubMed abstract(s).
Read them and recover WHY the trial stopped early.

Each input line has TWO tab-separated columns:
  NCT_ID <TAB> publication_abstract_text   (tags like [RESULT]/[DERIVED]/[BACKGROUND] mark the source type)

Assign EACH trial to exactly ONE category key:

- `safety` — stopped for adverse events, toxicity, deaths, unacceptable risk/benefit.
- `efficacy_futility` — stopped for lack of efficacy, futility, interim analysis showed no/insufficient benefit, did not meet primary endpoint.
- `efficacy_positive` — stopped EARLY because efficacy was already demonstrated / benefit boundary crossed. A POSITIVE result.
- `enrollment` — stopped because of slow/insufficient recruitment or accrual.
- `business_strategic` — stopped for sponsor business/strategic/commercial/portfolio reasons.
- `funding` — stopped for lack of funding/financial reasons.
- `covid` — stopped due to the COVID-19 pandemic.
- `regulatory` — stopped by a regulatory authority / clinical hold / ethics board.
- `supply_manufacturing` — stopped for drug supply or manufacturing problems.
- `external_evidence` — stopped because external developments (another trial's data, standard-of-care change, competitor approval) made it obsolete.
- `unclear` — the abstract does NOT state or clearly imply why the trial was stopped early (e.g. it reports results but never explains the early termination).

Rules:
- Base the call on what the abstract actually says about the EARLY STOP, not on whether the drug ultimately looked good or bad in general.
- A trial "terminated early because a planned interim analysis met the efficacy boundary" = `efficacy_positive`. "Terminated for futility / crossed the futility boundary" = `efficacy_futility`.
- If the abstract only reports outcomes and never mentions why enrollment was halted, use `unclear`.
- Pick the single primary cause.
