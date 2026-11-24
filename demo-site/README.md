# demo-site

A minimal static course site used as the factory's demo target. It stands
in for the video's real site (zazencodes.com, Vue + Firebase).

- `index.html` + `app.js` render the course from `content.json`.
- `content.json` holds 25 lessons for the "Obsidian Agent Setup" course.
  Each lesson has `publicContent` (lesson text public or not) and
  `videoPaywalled` (always `true`: videos stay behind purchase).
- `lessons/obsidian-agent-setup.md` is one sample lesson text.

Paywall rules, from the video (t=898s): lesson text may become public, but
video, slides, and attachments stay behind purchase. The factory's sample
job 001 applies exactly that change.
