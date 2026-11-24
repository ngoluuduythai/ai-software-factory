# Spec — 001-obsidian-course-unpaywall

## Feature

The Obsidian Agent Setup course lesson pages should not be paywalled.
Only the videos should be paywalled.

## Goal

Make the lesson text of all 25 Obsidian Agent Setup lessons public while
keeping videos, slides, and attachments behind purchase.

## Acceptance criteria

- [ ] All 25 lessons load their full markdown for everyone, with no
      paywall gradient on the lesson text.
- [ ] The completion card shows to everyone.
- [ ] Non-buyers get the end-of-article course CTA.
- [ ] Video, slides, and attachments stay behind purchase.

## Out of scope

- Changing course pricing, checkout, or certificates.
- Changing the video player or the paywall for videos.
- Any other course.

## Assumptions

- "Lesson text" means the markdown body of each lesson page; the video,
  slides, and attachments are separate assets and stay locked.
- The `publicContent` flag on a lesson is the single switch that makes
  its text public. This is an assumption about the implementation, not a
  business decision.

## Files likely to change

- `demo-site/content.json`
- `demo-site/app.js` (only if the renderer needs the flag wired through)
