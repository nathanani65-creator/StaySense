# Deploying StaySense Phitsanulok (Railway + Vercel, free tier)

Three pieces to stand up: MySQL, the FastAPI backend, and the Vue frontend.
The config files below are already in the repo — this doc is the manual
steps (account creation, dashboard clicks) that only you can do.

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
   - `CORS_ORIGINS` = leave as `http://localhost:5173` for now, we'll add
     the Vercel URL after step 2
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

## 2. Vercel — frontend

1. Go to https://vercel.com and sign up (GitHub login).
2. **Add New → Project** → import the same GitHub repo.
3. Set **Root Directory** to `staysense-vue`. Vercel auto-detects Vite
   (build command `npm run build`, output `dist`) — leave those as-is.
4. Add an environment variable: `VITE_API_BASE_URL` = your Railway backend
   URL from step 1.4 (the `PUBLIC_BASE_URL` one).
5. Deploy. Vercel gives you a URL like
   `https://staysense-phitsanulok.vercel.app` — **that's the link for
   Nifty PM.**
6. Go back to Railway's backend service → Variables → update `CORS_ORIGINS`
   to include this Vercel URL (comma-separated with localhost), e.g.
   `http://localhost:5173,https://staysense-phitsanulok.vercel.app`, and
   redeploy the backend once more.

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
  Vercel's Hobby plan is free but has fair-use limits) — fine for a thesis
  demo, not for real public traffic.
