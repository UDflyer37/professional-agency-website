# Otto & Associates website

The public website, online appointment booking and agent portal for Otto & Associates Insurance Agency, Sunbury, Ohio. It replaces the Anvil app in `UDflyer37/professional-agency-website`.

It is a plain Flask app with a PostgreSQL database. It runs on Vercel, but nothing in it is tied to Vercel: any host that runs Python and Postgres works.

## What it does

**Public site**

- Home page: a full-width rotating headline that is sized to fill its own fixed box (so the page never jumps when it changes), a huge but faint Otto mark behind it, two small portrait pills, quick tasks, a scrolling ribbon of what is insured, a company logo gallery, an open coverage list with picture previews, a two-step quote request, a **rolodex-style claims finder**, a draggable document gallery, the family story with hover-reveal portraits, reviews, FAQs and a contact section with live office hours. Dark bands carry a soft lamp that follows the pointer; there is no custom cursor.
- `/appointments`: visitors pick a day, a time and how to meet (phone, video, or in person by arrangement). Days the agency marks as time off are never offered. The visitor and the office both get an email.
- `/contact`: requests for proof of insurance cards, declarations pages, certificates, verification letters, quotes and anything else. Requests are saved and emailed to the office.
- `/privacy`: the existing privacy policy.

**Agent portal** (`/portal`)

- Dashboard: today's appointments, unread requests, shortcuts and office tools.
- Appointments: a month, week or day calendar of the book (arrows, Today, time-off days marked "Away", click a day for its list), upcoming and past bookings, cancel one (with an optional email to the client), email a client, add an appointment taken by phone, download everything as CSV, clear past bookings.
- **Notes:** a sticky-note board for everything with no other home. Write, colour, drag, edit in place, pin the important ones to the top, or read the board as a numbered list. Notes are private to the office and kept in the database.
- Messages: read requests, **reply from the portal** (saved with the request and emailed), filter by unread, mark handled, delete, download as CSV.
- **Time off:** mark days or ranges away. The booking calendar skips them, the website says the office is away instead of "open now", and the badge stays right even if a visitor leaves the page open overnight.
- Website: change the live site without a deploy. Covers headline and rotating sayings, intro, the family photo, contact details, announcement banner (with suggestions for the link text and a list of the site's own pages), colour scheme, corner style, which home page sections show and in what order, insurance companies and logos, coverage types, people and photos, client reviews and FAQs.
- **Colours:** four everyday palettes, four seasonal ones (Christmas, Halloween, Fourth of July, Thanksgiving) and a hand-picked palette with four colour pickers. The corner style really does change photos, cards and panels.
- **Layout:** each home page section in the order editor has a small wireframe so it is obvious what is being moved; hide a section with its tick box, reorder with the arrows.
- **Questions and answers:** edit in place, with ↑ and ↓ buttons that reorder and renumber automatically.
- **Text reminders:** optional texts to the owner's phone for new bookings, new requests and before each appointment. The wording of each message and how far ahead the reminder goes are both editable, with a live preview and a "send due reminders now" button and a daily automatic check.
- Hours and booking: office hours per day, appointment length, how far ahead clients can book, clients per time, and a **test email** button to check mail delivery.
- Resources: a private shelf of carrier logins, forms and phone numbers, split into agent-only and client-facing lists, with suggestions, an explanation of what the page is for, and a copy button (or `C`) on every entry so a link or number can be pasted straight into a message.
- **Backup and exports:** a JSON copy of everything editable on the website, plus CSV downloads of messages, appointments and FAQs.
- **Account:** change your own password. Logins: add colleagues, reset passwords, remove access.

## Project layout

```
app.py                 Entry point (Vercel and `flask --app app` look for `app` here)
.python-version        Pins the Vercel Python runtime to 3.13
otto/
  __init__.py          App factory and CLI commands
  config.py            Settings from environment variables; fails fast if any are missing
  db.py                Postgres connection per request, schema setup, default rows
  schema.sql           Tables (safe to re-run; adds new columns and tables)
  scheduling.py        Pure functions: open slots, open-now status, time off
  store.py             All SQL (parameterised)
  validation.py        Form input checks
  mailer.py            SMTP sender, or a logger when SMTP is not configured
  sms.py               Twilio text sender, or a logger when Twilio is not configured
  notify.py            When to text the owner: new booking, new request, reminders
  security.py          CSRF tokens, login guard, security headers
  public.py            Public routes
  portal.py            Agent portal: sign-in, dashboard, appointments, messages, time off, hours, FAQs, exports
  portal_site.py       Agent portal: website editor, backup-adjacent content, logins
  site.py              Editable website content: defaults, loading, saving, ordering
  media.py             Photo and logo uploads (validated, stored in Postgres)
  content.py           Copy and facts for the public pages (carriers, coverage, community)
  templates/           Jinja templates
public/static/         CSS, JS, fonts and images, served by Vercel's CDN
tests/                 pytest suite
vercel.json            Only the daily reminder cron; no build settings
```

## Run it on your computer

You need Python 3.12 or newer (3.13 is what production uses) and PostgreSQL 14 or newer.

```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

createdb otto                        # or create a database any way you like
cp .env.example .env                 # then fill in OTTO_SECRET_KEY and DATABASE_URL

flask --app app init-db              # creates or upgrades tables, default hours and FAQs; safe to run again
flask --app app create-agent andi@theottoagency.com "Andi Otto"   # prompts for a password
flask --app app run --debug
```

Open http://127.0.0.1:5000. The portal is at http://127.0.0.1:5000/portal.

Flask reads `.env` automatically because `python-dotenv` is installed. If `OTTO_SMTP_HOST` is empty, the app writes emails to the terminal instead of sending them, so you can test bookings safely. The portal's **Hours and booking** page shows whether email is connected and can send a test message.

After pulling a new version, run `flask --app app init-db` once. It only adds what is missing (tables, columns, default hours and FAQs) and never deletes data. Version 3 adds message reply columns and the `time_off` table this way; 3.1 adds `bookings.reminded_at`, and 3.2 adds the `notes` table.

Texts are optional and off by default. To try them locally, leave the three `OTTO_TWILIO_*` values empty: the app logs each message to the terminal instead of sending it, so the portal's **Send a test text** and **Send any due reminders now** buttons can be exercised safely. `CRON_SECRET` is only needed to call `/tasks/reminders` by hand.

## Tests

```bash
pytest
```

The scheduling and validation tests always run. The end-to-end tests in `tests/test_app.py` also need an empty database that the tests may wipe:

```bash
createdb otto_test
OTTO_TEST_DATABASE_URL=postgresql://localhost/otto_test pytest
```

## Deploy on Vercel

This project is already shaped for Vercel's Python runtime. There is no `/api` folder and no build command, because Vercel's Flask support finds `app.py` by itself. `vercel.json` does two things: it pins the framework to `flask`, so a fresh import is not mistaken for a static site that serves only `public/`, and it schedules the daily reminder check. Delete the `crons` entry if you do not want texts.

What makes it work:

- `app.py` at the repository root exposes `app`. Vercel's zero-configuration Flask support finds it and runs the whole site as one Python function.
- `requirements.txt` lists Flask and psycopg. No build command or output directory is needed.
- `.python-version` pins Python 3.13, matching local development. Vercel also accepts this as `requires-python` in `pyproject.toml`.
- Everything in `public/` is served from the site root by Vercel's CDN. That is why the stylesheet lives at `public/static/css/site.css` and is requested as `/static/css/site.css`. Flask serves the same folder locally from `static_folder`.
- The function filesystem is read-only, so uploaded photos and logos are stored in Postgres and served from `/media/<id>`.
- `db.py` disables server-side prepared statements, which Neon's pooled connection (PgBouncer) requires.
- `vercel.json` also lists `otto/templates/**` and `otto/schema.sql` under `functions.includeFiles`. Vercel bundles Python modules but not the HTML they render, so without that every page answers with `TemplateNotFound: public/home.html`.

Steps:

1. Push this folder to a GitHub repository and import it at vercel.com/new. Leave the framework preset on its detected default and add no build settings.
2. In the project, open **Storage**, add **Neon** (Postgres) and connect it. This sets `DATABASE_URL`. Use the pooled connection string. From the CLI, `vercel integration add neon` does the same thing and sets the variable for every environment.
3. In **Settings → Environment Variables**, add:
   - `OTTO_SECRET_KEY`: 64 random hex characters.
   - `OTTO_AGENCY_EMAIL`: the inbox for bookings and requests.
   - `OTTO_SMTP_HOST`, `OTTO_SMTP_PORT`, `OTTO_SMTP_USERNAME`, `OTTO_SMTP_PASSWORD`, `OTTO_SMTP_SENDER`: the mail account the site sends from. The Turbify values are in [Email](#email) below.
   - Optional texts: `OTTO_TWILIO_ACCOUNT_SID`, `OTTO_TWILIO_AUTH_TOKEN` and `OTTO_TWILIO_FROM` (the Twilio number texts are sent from). Nothing is sent until these are set *and* texts are switched on in the portal.
   - `CRON_SECRET`: any random string of 16 or more characters. Vercel does **not** create this for you; it only sends the value you set as the `Authorization: Bearer` header when it invokes the cron. Without it, `/tasks/reminders` answers 403, so the daily check does nothing.
   - Leave `OTTO_SECURE_COOKIES` unset (it defaults to `true`).
   - `vercel.json` adds a daily cron at 12:00 UTC (8:00 am Eastern) that calls `/tasks/reminders`. Vercel's Hobby plan allows one run a day, which matches the default reminder window.
4. Create the tables and a login once, from your computer, against the Neon database:

   ```bash
   npm i -g vercel
   vercel link
   vercel env pull /tmp/vercel.env   # NOT .env: pulling over .env replaces your local settings
   # Set OTTO_SECURE_COOKIES=false in .env only while testing the portal on localhost.
   flask --app app init-db
   flask --app app create-agent andi@theottoagency.com "Andi Otto"
   ```

5. Deploy. Every push to `main` deploys to production; other branches get preview URLs.
6. Open the deployment, sign in at `/portal`, and use **Hours and booking → Send a test message** to confirm email works. Check the spam folder too. If you set up Twilio, use **Text reminders → Send a test text**, then switch texts on.
7. To use theottoagency.com, add it under **Settings → Domains** and update DNS where the domain is registered. Do this only when you are ready to switch off Anvil.

Optional: `vercel dev` runs the site through Vercel's local emulator instead of `flask run`. It is useful before a first deploy, but it needs the CLI and a linked project. `flask --app app run` is enough for everyday work.

### Email

Vercel does not send mail itself. Use any SMTP account:

- **Turbify business mail** (the current inbox, and where theottoagency.com is registered):
  - `OTTO_SMTP_HOST=smtp.bizmail.yahoo.com`
  - `OTTO_SMTP_PORT=465`
  - `OTTO_SMTP_USERNAME` and `OTTO_SMTP_SENDER`: `andi@theottoagency.com` (the full address, not just `andi`)
  - `OTTO_SMTP_PASSWORD`: an **app password**, not the mailbox password. In Turbify Mail, open Settings → Account security → Generate app password, name it `website`, and use the 16-character code it shows once.
- **Google Workspace**: `smtp.gmail.com`, port 587, with an app password.
- **Resend** or **Postmark**: better delivery from your own domain. Both need DNS records added for theottoagency.com.

Port 465 uses SSL; any other port uses STARTTLS.

## Moving data from Anvil

In the Anvil editor, open **Data Tables** and export each table you want to keep as CSV.

- **FAQs:** `flask --app app import-faqs faqs.csv` (add `--replace` to drop the starter FAQs).
- **Bookings:** only future ones matter. Re-enter them in the portal, or ask clients to rebook.
- **Contact messages:** old ones can stay in the CSV.
- **Resources and phone numbers:** add them in the portal under Resources.
- **Agent logins:** Anvil password hashes cannot be carried over. Create new logins with `create-agent`.

## Upgrading an existing database

After deploying a new version, run `flask --app app init-db` once against the production database (see the Vercel steps). It only adds what is missing, such as new columns or tables, and never deletes data.

## Editing the site

Most day-to-day changes happen in the portal and appear as soon as you save.

Photos and logos uploaded there are stored in the database, because Vercel's file system is read-only. They must be JPG, PNG or WebP, up to 3 MB each. Keep the originals in your own photo library as well; they are not included in the website backup file.

The notes below are for developers changing what the portal cannot.

- **Copy, address, phone numbers, carriers, claims numbers, coverage and the quote builder words:** `otto/content.py`.
- **Page structure:** `otto/templates/public/`.
- **Look and feel:** `public/static/css/site.css`. The six values the portal controls (primary, deep, accent, on-accent and two corner radii) arrive on the `<html>` style attribute; everything else is derived from them with `color-mix`.
- **Interactions:** `public/static/js/site.js`. All of it enhances markup that already works without JavaScript.
- **Carrier logos:** `public/static/img/carriers/<slug>.png`. To size a logo, change `logo_height` in the portal (or for a new database, `otto/content.py`).
- **FAQs, hours and time off:** change them in the portal. No deploy is needed.

### Design notes

The site is built as a stack of coloured bands on warm paper, not as a grid of white cards. Each band draws its own shaped seam above itself (wave, arch, tear, scallop, tilt or curve) in its own top colour, so any section order the owner chooses still joins cleanly. Section numbers are generated from the live order, not hard-coded.

Motion follows the same rule: a slow morph on the hero background, arch frames that change radius on hover, two still pools of light in the bottom corners of the dark bands, and a headline that is measured to the largest size that fits its box on every resize or font load. Nothing follows the pointer and there is no custom cursor. Everything stops for `prefers-reduced-motion`.

## Security notes

- Every form carries a CSRF token, and posts without one are rejected.
- All SQL is parameterised.
- Portal pages require a login. Five wrong passwords lock that login for 15 minutes.
- Passwords are stored as salted scrypt hashes.
- Cookies are HttpOnly, SameSite=Lax and Secure in production.
- A strict Content-Security-Policy allows scripts, styles, fonts and images only from this site.
- The booking and contact forms have a hidden field that catches simple bots.
- Replies, exports and backups are only available to signed-in agents.
- Secrets come only from environment variables. Nothing secret is committed; `.env` is git-ignored.
