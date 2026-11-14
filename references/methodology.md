# Methodology: Content Pipeline and Project Structure

A content mini program is, at its core, "pack a content dataset into a 2 MB main package plus subpackages — and keep it from rotting over time". This chapter walks through each pipeline stage and why it exists.

## Contents

1. Topic matrix and production schedule
2. Two-layer data (index / full text)
3. Subpackage strategy and the size ledger
4. Illustration pipeline: produced by code, never scraped
5. Single source of truth and template distribution
6. README as the project status board

## 1. Topic matrix and production schedule

Fix the total and the structure first, then write content. Using 365 cards as the example:

- Draw the matrix across three axes — **total × categories × difficulty** (e.g. 365 cards / 10 categories / 120 beginner + 160 intermediate + 85 applied). Every card owns a unique cell, so "no duplicates, no gaps" becomes machine-checkable the moment writing finishes.
- The **production schedule** maps card IDs to calendar dates (for the daily card). Pin the rules down as criteria: same-category spacing ≥ N days, a cap on seven-day peaks, progressive difficulty, full category coverage in the final stretch. Encode the rules as a gate script (check_order); do not rely on spot checks.
- Keep the schedule as a **data file** (e.g. cards_365.json), not a magic array in code, so the gate script and the runtime read the same source.

## 2. Two-layer data

- **Index layer** (cards-index.js): only id/title/category/difficulty/summary/image path per card; always in the main package. Lists, search, and the daily card read only the index.
- **Full-text layer** (pkgA/pkgB data): complete body, code, sample output; lives in subpackages, loaded when entering the detail page.

Payoff: small main package, fast lists; search runs on the index without loading full text into memory. The cost is maintaining an index/full-text consistency gate (check_consistency: counts, ID sets, routing parity, image paths exist).

## 3. Subpackage strategy and the size ledger

- WeChat caps the main package at 2 MB and each subpackage at 2 MB. **Do not ride the limit** — in the source project the main-package target line is 1950 KB, keeping a 50 KB buffer.
- Split content roughly in half across two subpackages (e.g. odd cards → pkgA, even cards → pkgB) so the routing rule is simple enough to verify by script.
- **Size ledger** (check_milestone_sum): every build prints "file count / source size / compressed estimate" per package and writes it into the README. Size problems should surface the day content is added, not the day before release.

## 4. Illustration pipeline: produced by code, never scraped

- Content illustrations (e.g. plots of code output) are **actually produced by the content code**: run the code → render the figure → compress into the package. This guarantees figure-code consistency and gives you clean copyright.
- For atmosphere images (theme backgrounds), **do not scrape web images**: unlicensed web images are the two most frequent causes of copyright complaints and review rejections for personal accounts. Generate original art instead, and afterwards you must:
  1. Crop the generator's watermark (usually bottom-right, ~5% of height);
  2. Compress to the target size and per-image budget (e.g. 640 px / <100 KB);
  3. Manually verify every image: no text, no watermark, no recognizable faces, no third-party brand marks.
- Encode the pipeline as a script (fixed crop ratio, dimensions, quality) so it is repeatable.

## 5. Single source of truth and template distribution

When the same page exists in multiple copies (e.g. a detail page in both pkgA and pkgB), **edit only the template, then run the distribution script** (e.g. make_subpackages.py). Editing a copy directly guarantees drift — real incident: the template gained a disclaimer, the subpackage copies did not, and it surfaced only at release time. After distribution, run the consistency gate to confirm the copies are byte-identical.

## 6. README as the project status board

The README carries **state**, not slogans:

- Current completeness and key numbers (measured, not estimated);
- Gate table: every check's name and latest result;
- Pending human tasks (fill in AppID, on-device test, filing number);
- Reproduction steps: every check command, numbered.

That way anyone — including you three months later, or another AI — knows the project's exact state and the next step just by reading the README.
