# Competitor Social Intelligence — Working Prototype

A Mention.com-style competitor tracking tool: mention tracking, content-type
analysis, posting-time patterns, engagement, competitor ad monitoring, and
brand search interest — built to run today, with real (not mocked)
connectors to the APIs that are actually available for this in 2026.

**This has been tested and runs end-to-end** — the demo data seeder,
FastAPI backend, and Streamlit dashboard all work with zero configuration.
Plug in real API keys when you're ready to track real competitors.

## Quick start (demo mode, no API keys needed)

```bash
python -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt
cp .env.example .env
python -m scripts.seed_demo_data      # populates data/social_intel.db with realistic fake data
streamlit run dashboard/app.py        # opens the dashboard at localhost:8501
```

In a second terminal, the API (used for ingestion/sync jobs):

```bash
uvicorn app.main:app --reload --port 8123
# docs at http://localhost:8123/docs
```

## Going live: what's real vs. what needs a decision

I built this against the actual 2026 API landscape rather than assuming
"just call the API" works the way it did a few years ago — several major
platforms have locked competitor data down hard. Here's the honest map:

| Platform | What you get automatically | Access path | Cost |
|---|---|---|---|
| **X (Twitter)** | Mentions (7-day search) + competitor's own recent posts | Official API v2, App-Only Bearer token | Pay-per-use, ~$0.005/post read, no free tier |
| **Facebook/Instagram ads** | Competitor's active/past ad creative, run dates | Official Ad Library API (`ads_archive`) — public, no App Review needed | Free |
| **Facebook/Instagram organic posts** | Single-post metadata, *given the exact public URL* | Official oEmbed endpoints | Free, but requires someone to paste the URL — no feed discovery |
| **News/blogs/forums** | Mentions matching your brand/keyword search | Any NewsAPI-compatible provider (wired to newsapi.org by default) | Free tier available |
| **Google search interest** | Relative brand search volume over time | `pytrends` (unofficial wrapper around Google Trends' public embed data) | Free, but unofficial — can break if Google changes the page |
| **LinkedIn** | Nothing automated | — | — |

**Why no automated Instagram/Facebook/LinkedIn organic feed tracking:**
Meta's Graph API only exposes organic post data for Pages/accounts *you*
manage — not competitors. LinkedIn's API doesn't expose competitor company
page content at all (and LinkedIn has actively sued and shut down
third-party providers that scraped around this, e.g. Proxycurl in 2025).
Tools like Mention, Brandwatch, and Talkwalker cover this gap by paying for
licensed data partnerships most indie/early-stage builds can't access. I
didn't build a scraper to route around platform ToS here — that carries
real legal exposure (civil claims under the platforms' terms, and account
bans) and I'd rather be upfront about the gap than hand you something
fragile and risky.

**Your realistic options for that gap, in order of effort:**
1. **Ship without it initially.** Twitter mentions + Meta ad intelligence +
   news/web mentions + search interest is already a genuinely useful MVP.
2. **Semi-manual workflow.** Use the oEmbed importer — someone on your team
   (or your customers, for a SaaS version) pastes a competitor's post URL
   when they spot something interesting; you get real structured data back
   instantly, no scraping.
3. **License a data vendor.** Services like Brandwatch, Talkwalker, or
   Phyllo have paid the licensing/partnership cost to get broader organic
   coverage. Point `app/connectors/` at their API instead of building your
   own — the database schema and dashboard don't care where the data came
   from.

## Architecture

```
app/
  config.py, database.py, models.py, schemas.py   -- core plumbing
  connectors/
    twitter_connector.py    -- real X API v2 (mentions + competitor timeline)
    meta_ads_connector.py   -- real Meta Ad Library API
    oembed_connector.py     -- real Meta oEmbed (manual single-post import)
    news_connector.py       -- real NewsAPI-compatible mention search
  analysis/
    content_classifier.py   -- content-type rules + optional Claude-based topic/sentiment tagging
    posting_time.py         -- day/hour heatmap, best posting slots, cadence
    engagement.py           -- engagement rate, top posts
    ad_organic_matcher.py   -- flags each organic post as "boosted" (matches an ad) or "organic-only"
    brand_search_trends.py  -- Google Trends (pytrends) search interest
  main.py                    -- FastAPI app (ingestion endpoints + read endpoints)
  scheduler.py                -- APScheduler loop for unattended periodic polling
dashboard/app.py              -- Streamlit UI (Overview / Content & Timing / Mentions / Ads / Search Interest)
scripts/seed_demo_data.py     -- synthetic demo data generator
```

Every connector checks for its own API key and skips itself with a logged
warning if missing — so you can wire up platforms one at a time instead of
needing all keys before anything works.

## Organic vs. boosted posts

Every organic post gets flagged `is_boosted: true/false` — "is this specific
post also running as a paid ad right now, or is it purely organic with no ad
spend behind it?" This is genuinely useful signal: it shows which content a
competitor is doubling down on with budget vs. what they're leaving to
organic reach alone.

**Be clear-eyed about the method, though:** Meta doesn't expose an official
link between a specific organic post and an Ad Library entry for pages you
don't manage (that link only exists via the Graph API's `promotable_posts`
edge, and only for accounts you own). So this is a best-effort *content
match* — it compares each post's caption against the competitor's tracked ad
creatives using document-frequency-weighted word overlap (so generic
marketing boilerplate like "shop now" doesn't trigger false matches, while a
near-identical reused caption does) within a ±21-day window, and only flags
a match at a strict 0.75+ similarity score. In practice this catches the
common case cleanly — a "boost post" in Meta Ads Manager reuses the exact
organic copy — but it will under-flag (not over-flag) anything the
competitor rewrote before running as an ad. Every match reports its
confidence score (`match_confidence`) rather than presenting a boolean guess
as certainty.

Run it via `POST /competitors/{id}/analyze/match-ads` after any sync (the
`scheduler.py` loop runs it automatically on every poll cycle). Filter results
with `GET /competitors/{id}/posts/organic-only` or `.../posts/boosted`.

## Adding a real competitor

```bash
curl -X POST http://localhost:8123/competitors -H "Content-Type: application/json" -d '{
  "name": "Acme Running Co",
  "handle_twitter": "acmerunning",
  "website": "https://acme-running.com"
}'

# Then trigger a sync:
curl -X POST "http://localhost:8123/competitors/1/sync/twitter"
curl -X POST "http://localhost:8123/competitors/1/sync/mentions?query=%22Acme%20Running%22"
curl -X POST "http://localhost:8123/competitors/1/sync/meta-ads?search_term=Acme%20Running"
```

Or run `python -m app.scheduler` to poll every competitor automatically on
an interval (`POLL_INTERVAL_MINUTES` in `.env`).

## Turning this into a commercial SaaS

The prototype is single-tenant (one shared DB). For a real product you'd
add, roughly in priority order:
1. **Auth + multi-tenancy** — user accounts, and a `tenant_id`/`org_id` on
   every table so customers only see their own competitor data.
2. **Postgres** instead of SQLite (swap `DATABASE_URL` — the SQLAlchemy
   models don't change).
3. **Billing** — since X reads and Meta Ad Library both have real
   per-call/rate-limit realities, you'll want usage metering per customer.
4. **A proper frontend** — Streamlit is great for validating the product;
   a dedicated React app gives you the polish a paying customer expects.
5. **Background job infra** — swap APScheduler for Celery/RQ once you have
   enough competitors tracked that a single process polling loop won't keep up.
