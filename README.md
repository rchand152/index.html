[README.md](https://github.com/user-attachments/files/30403114/README.md)
# Letter to the Universe — daily Reel pipeline

A fully automated system that renders a new Instagram Reel every day, showing
a rotating prompt and the running "letters released" counter — then posts it.

## How it fits together

```
[ your website ]  --release click-->  [ counter API ]
                                            |
                                   (GitHub Actions, daily)
                                            v
                              fetch_count.py --> generate_reel.py
                                            |
                                   reels/reel-YYYY-MM-DD.mp4
                                   reels/reel-YYYY-MM-DD.json  (caption text)
                                            |
                                    committed to this repo
                                            |
                              (Zapier/Make: "new file in repo")
                                            v
                                   Buffer / Later queue
                                            |
                                  auto-published to Instagram
```

## What's already automated (in this folder)

- **`generate_reel.py`** — renders the vertical (1080×1920) video: eyebrow,
  today's quote, the glowing counter, rising embers, and a CTA. Tested and
  working — see `sample-reel.mp4` for actual output.
- **`quotes.json`** — the rotating prompts. Edit this file any time; it
  cycles through by day-of-year so it repeats predictably once you've used
  them all. Add as many as you like.
- **`fetch_count.py`** — reads the current counter value (no auth needed).
- **`.github/workflows/daily-reel.yml`** — runs the above daily on GitHub's
  free Actions runners and commits the finished video + a caption-ready
  JSON file into `reels/`. No server of your own required.

To turn this on: push this folder to a GitHub repo. That's it — the workflow
runs on its own from then on (also triggerable manually from the Actions tab).

## What still needs your one-time setup (can't be automated by me)

1. **Deploy the actual website** somewhere real (Vercel or Netlify both have
   free static hosting — drag-and-drop the `letter-to-the-universe.html`
   file in). Right now it only exists in the Claude preview, so the counter
   has nothing to count yet.
2. **Switch your Instagram account to a free Business or Creator account**
   (Settings → Account type in the Instagram app). This is required by
   *any* scheduling tool, not just a custom build — it's a few taps, not a
   development project.
3. **Create a free Buffer or Later account** and connect that Instagram
   account through their own onboarding — they handle the Meta API
   connection for you, so you never touch API keys directly.
4. **Connect the two with Zapier or Make.com** (both have free tiers): a
   single automation ("when a new file appears in this GitHub repo's
   `reels/` folder → create a post in Buffer/Later using that video and the
   caption from the matching `.json` file"). This is point-and-click, no
   code.

Once those four are in place, the whole thing runs itself: your site counts
releases → the daily workflow renders a video → Zapier hands it to
Buffer/Later → Instagram publishes it.

## Customizing

- **Prompts**: edit `quotes.json`.
- **Posting time**: change the `cron` line in the workflow file (it's in UTC).
- **Caption**: edit the `suggested_caption` template inside `generate_reel.py`'s
  `main()` function, or override it in your Zapier step.
- **Counter durability**: the free counter API (`countapi.mileshilliard.com`)
  needs no signup, which is why it's the starting point — but it's a small,
  unofficial, community-run service with no uptime guarantee. If the
  counter ever matters to you long-term, the sturdier upgrade is a tiny
  serverless function backed by Upstash Redis's free tier (a few lines of
  code) — worth doing once the project is getting real traction.
