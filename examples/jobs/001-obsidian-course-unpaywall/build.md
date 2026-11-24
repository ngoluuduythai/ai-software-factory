# Build — 001-obsidian-course-unpaywall

## Summary

Obsidian Agent Setup now sets `"publicContent": true`. All 25 lessons load
their full markdown for everyone, with no paywall gradient. The completion
card shows to everyone, and non-buyers get the end-of-article course CTA.
Video, slides, and attachments stay behind purchase.

## Changes

- `demo-site/content.json` — set `publicContent` to `true` for all 25
  lessons; `videoPaywalled` stays `true` for all 25 lessons.
- `demo-site/app.js` — no change needed: the renderer already shows the
  lesson text when `publicContent` is true and keeps the video locked.

## Validation

- `demo-site/content.json` parses as valid JSON with 25 lessons.
- All 25 lessons have `publicContent: true` and `videoPaywalled: true`.
- Demo site renders: lesson text visible, video still marked locked.

## Notes

- This is a course-access change, so the approver is expected to escalate
  it to a human even though every review passed.
