# Decision — 001-obsidian-course-unpaywall

DECISION: ESCALATE

## Reasons

- All four reviews passed: security, UX, UI, and code.
- The build is clean: all 25 lessons are public, videos stay paywalled,
  and the acceptance criteria are met.
- The change touches course access, which is on the escalation list in
  the factory skill. Course access is a business decision, not a purely
  technical one, so a human should confirm it before merging.

## Human checklist

- Confirm the intent: lesson text public for everyone, videos/slides/
  attachments still behind purchase.
- Confirm no other course is affected by the flag change.
- If approved, merge with: `/factory approve 001-obsidian-course-unpaywall`
