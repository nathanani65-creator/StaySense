# Deploying StaySense Phitsanulok (Railway + Netlify, free tier)

Three pieces to stand up: MySQL, the FastAPI backend, and the Vue frontend.
The config files below are already in the repo — this doc is the manual
steps (account creation, dashboard clicks) that only you can do.

**Frontend is already live at https://staysense-pitlok.netlify.app/** — it
just can't reach a backend yet, because step 1 (Railway) hasn't been done.
That's the part still missing.

## 1. Railway — MySQL + backend

1. Go to https://railway.app and sign up (GitHub login is easiest).
2. **New Project → Deploy from GitHub repo** → pick `nathanani65-creator/StaySense`.
3. Railway will try to detect a service from the repo root — delete that
   auto-detected service, we'll add two services manually instead:
   - **Add a MySQL database**: New → Database → Add MySQL. Railway
     provisions it and shows a "Connect" tab with a `MYSQL_URL` / connection
     details (host, port, user, password, database).
   - **Add the backend service**: New → GitHub Repo → same repo again, but
     set **Root Directory** to `staysense-backend` in its Settings. Railway
     will pick up `railway.json` and `Procfile` automatically.
4. On the backend service → **Variables** tab, add (see
   `staysense-backend/.env.example` for the full list):
   - `DATABASE_URL` = `mysql+pymysql://<user>:<password>@<host>:<port>/<database>`
     (take the values from the MySQL service's Connect tab — note the
     `mysql+pymysql://` prefix, not Railway's default `mysql://`)
   - `CORS_ORIGINS` = `http://localhost:5173,https://staysense-pitlok.netlify.app`
   - `JWT_SECRET_KEY` = a random string (ask me to generate one, or run
     `python -c "import secrets; print(secrets.token_hex(32))"`)
   - `PUBLIC_BASE_URL` = your Railway backend URL once it's deployed (looks
     like `https://staysense-backend-production-xxxx.up.railway.app`) —
     Railway shows this under Settings → Networking → **Generate Domain**
     (you need to click that once; it's not public by default)
5. Once the MySQL service is up, send me its **public connection details**
   (host, port, user, password, database name — Railway calls this the
   external/TCP proxy connection) and I'll restore the real StaySense data
   into it from the dump I already took of your local database, so the
   deployed site shows the same real hotels/places you've been testing
   against, not empty tables.
6. Redeploy the backend service after setting the variables. Watch the
   deploy log for `Application startup complete` — first boot is slow
   (~1-2 min) because it downloads the multilingual-e5-small embedding
   model.

## 2. Netlify — frontend (already deployed — just needs to point at the backend)

Your site is live at `https://staysense-pitlok.netlify.app/`, built with
the manual **Base directory / Build command / Publish directory** settings
you set in the dashboard. Once Railway's backend has a public URL (step
1.4's `PUBLIC_BASE_URL`):

1. Netlify site → **Site configuration → Environment variables → Add a
   variable**: `VITE_API_BASE_URL` = your Railway backend URL.
2. **Deploys** tab → **Trigger deploy → Clear cache and deploy site.**
   (Vite bakes env vars in at *build* time, not read at runtime — a plain
   redeploy without clearing cache may skip rebuilding and keep the old
   value, so use "Clear cache and deploy site" specifically.)
3. That's the link for Nifty PM: **https://staysense-pitlok.netlify.app/**

One more thing worth fixing while you're in there: page refreshes on a
route like `/hotels` or `/accommodations/49` will 404 right now, because
Netlify doesn't know to serve `index.html` for those paths (Vue Router
handles routing client-side). The `staysense-vue/netlify.toml` already in
this repo has the fix (a catch-all redirect to `index.html`) — it'll take
effect automatically the next time this repo is pushed to GitHub and
Netlify rebuilds from it. Until then you can also add it manually: Site
configuration → Build & deploy → Post processing → **Redirects and rewrite
rules** → add `/*` → `/index.html` with status `200`.

## Known limitations of this free setup

- **Uploaded images are not persistent.** The backend writes admin-uploaded
  photos to local disk (`uploads/`); Railway's filesystem resets on every
  redeploy. Fine for a demo link, but don't rely on it for real production
  image uploads without adding object storage (e.g. Cloudflare R2 / S3)
  later.
- **Cold starts.** Railway's free tier can sleep an idle service; the first
  request after a while may take a few seconds while it wakes up and
  reloads the embedding model into memory.
- Both free tiers are usage-limited (Railway gives a monthly credit,
  Netlify's free plan is free but has fair-use/bandwidth limits) — fine for
  a thesis demo, not for real public traffic.
