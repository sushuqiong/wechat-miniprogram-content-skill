# Contributing

Thanks for considering a contribution. This project values evidence over opinion: every rule in the docs exists because something real broke or got rejected.

## What makes a good contribution

- **New gate criteria**: a check that catches a failure mode you have actually seen, with a brief incident description.
- **Compliance patterns from real rejections**: review-rejection or ICP-filing cases, anonymized, with the wording that caused them and the fix.
- **Script improvements**: better precision (fewer false positives), clearer failure output, Windows/macOS/Linux parity.
- **Translations**: the Chinese word lists inside `scripts/compliance_scan.py` must stay Chinese (they match Chinese content), but docs and guidance can be localized.

## Ground rules

- Scripts must remain dependency-free (Python 3.8+ standard library only).
- Scripts must return meaningful exit codes (0 pass / 1 fail) and file-level failure detail.
- Test any script change against at least one real mini program source tree before submitting.
- Do not add promotional content, affiliate links, or scraped assets of any kind.

## Process

1. Open an issue describing the failure mode or case first — one paragraph is enough.
2. Reference the issue in your PR.
3. Keep PRs small: one gate, one pattern, or one fix per PR.
