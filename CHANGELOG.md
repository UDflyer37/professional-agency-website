# Changelog

All notable changes to this project are recorded here. The format follows Keep a Changelog, and versions follow Semantic Versioning.

## [3.3.0] - 2026-11-02

A security pass before the site goes live for real.

### Added
- **Limits on the open forms.** Each visitor gets five bookings, six requests or quotes and ten sign-in attempts per ten minutes, with a larger shared budget behind it. Without this a script could fill the inbox, book every free slot for a month, and — once Twilio is connected — spend real money on texts. Counters are kept in Postgres, because Vercel answers each request from a fresh function and would forget anything in memory. Only a salted hash of the address is stored, never the address.
- A `request_throttle` table for those counters. `init-db` creates it; run it once after deploying.
- A `429` page that says how long to wait, with a `Retry-After` header.

### Changed
- Portal pages now answer `Cache-Control: no-store`. Flask marked them cacheable, which left the office's own records able to sit in a shared cache or reappear from the back button after signing out.
- `X-Frame-Options: DENY` and `Cross-Origin-Opener-Policy: same-origin` join the existing headers, for browsers that ignore `frame-ancestors`.
- The reminder cron compares its bearer token in constant time. The `?token=` fallback is gone: a secret in a URL ends up in logs and browser history, and Vercel always sends the header.
- `.env.example` now shows `OTTO_SECURE_COOKIES=true`. It said `false` while telling the reader to keep it true in production, which is how a site ends up issuing sign-in cookies over plain http.

### Fixed
- The sign-in redirect accepted a path with a backslash (`/\evil.example`), which browsers can read as a host. Such a path now falls back to the dashboard.

## [3.2.1] - 2026-11-01

### Fixed
- The site now works on Vercel. The framework is pinned to Flask in `vercel.json`, and `functions.includeFiles` ships `otto/templates/**` and `otto/schema.sql` with the function. Vercel bundles Python modules but not the HTML they render, so without it every page answered `TemplateNotFound: public/home.html`.
- The deploy notes claimed Vercel creates `CRON_SECRET` when a cron job is configured. It does not: it only sends the value you set, so the daily reminder check answered 403 with nothing configured. The notes now say to add it yourself.

### Changed
- The deploy notes document the Turbify mail settings the office mailbox needs (`smtp.bizmail.yahoo.com`, port 465, app password) and warn that `vercel env pull .env` replaces local settings.

## [3.2.0] - 2026-10-30

### Added
- **Appointment calendar:** the Appointments page now opens on a real month grid and switches to week or day, with arrows to move back and forward, a Today link, each appointment on its day, "Away" on time-off days and a click-through from any day to its detail view. It is worked out on the server, so it reads correctly with JavaScript off and in the office's timezone.
- **Notes:** a sticky-note board under Today. Write a note, choose one of five colours, drag it anywhere on the board, edit it in place, pin the ones that matter to the top of the numbered list, and switch between both views.
- **Text wording:** every text can now be edited, with `{name}`, `{when}`, `{topic}` and `{kind}` placeholders, a live preview of the reminder filled in with a sample appointment, per-message validation and a note that the wording is saved even before Twilio is connected.
- **Reminder lead time:** choose how far ahead the appointment reminder goes (an hour to three days) instead of a fixed day.
- **Copy a resource:** each saved link or number on the Resources page has a copy button, or press `C` on the highlighted row, so it can be pasted straight into an email or text.

### Changed
- **Announcement banner:** live preview of the bar as it will appear, plus suggestions for the message, the link text and the site's own page addresses.
- **Family photo:** clearer labelling, and the help text now says what the photo is actually used for (or is hidden where it would only repeat itself).
- **Colour schemes:** everyday and seasonal schemes are separate groups, with the hand-picked palette below them.
- **Sections:** the order editor says the wireframes show the real layout, and each row's hint explains the section in one line.
- **Questions and answers:** ↑ and ↓ renumber the list as they move a question, and the position field is optional.
- **Resources:** the page explains who each list is for and what to put in it.
- **Portal surfaces:** work sits on tinted bands and rules instead of rows of white rounded boxes, and the dashboard shortcuts share one border style.
- **Appointment navigation:** the arrows and Today share one bordered control and the month sits centred between it and the Month/Week/Day switch, so the calendar header reads as one bar.
- **Dark bands:** the pointer-following lamp is gone. Each dark section now carries two still pools of light in its bottom corners, so nothing moves under the cursor and no seam can cut the glow.
- **Family photo:** the gold arch is now a true offset sheet behind the picture instead of a rotated frame, and the caption sits clear of it.

### Fixed
- Saving or deleting a note no longer returns the "This form expired" page: both note forms carry the CSRF token, and they return to the view they came from.
- "Write a reply" on Messages is readable again; the shared summary style was overriding the button's own colour.

## [3.1.0] - 2026-10-30

### Changed
- **Hero:** the rotating headline now spans the full page width and is measured to the largest size that fills a fixed box, so changing sayings never moves the page. The portraits are small pills, the Otto mark is the hero image (large and faint), the company count lost its white container, and the scroll cue is gone.
- **Pointer:** the trailing ring is removed; dark bands keep only the soft lamp, which now fades past the shaped seam instead of ending on a visible line.
- **Claims:** the company finder is a card index: names and logos on the left, a dark rolodex frame on the right with one flip-up card, knob arrows and a card count.
- **Contact form:** no white sheet. Numbered steps, ruled fields and outlined choices sit directly on the page, with a dark contact panel beside them.
- **Companies intro:** the line about shopping eight companies is larger, wider and has more air above it.
- **Quote steps:** "Andi or Glenn calls you" is now "We call you when you're ready".
- **Footer:** buttons keep their own borders again, so the quiet button no longer loses its outline, and hovered links keep readable contrast.
- **Open-now badge:** reads the owner's time off dates in the browser, so it stays correct across midnight, weekends and multi-day vacations.
- **Portal:** fewer white rounded boxes. Work sits on the paper separated by rules and tinted bands; repeated items (a question, a request, a resource) get one light tinted card.

### Added
- **Text reminders:** optional Twilio texts to the owner's phone for new bookings, new website requests and before each appointment. A daily Vercel cron checks for due reminders; the portal can also send them on demand and send a test text. Messages are safe to skip: an appointment is only reminded once.
- **Holiday palettes:** Christmas, Halloween, Fourth of July and Thanksgiving, alongside the everyday schemes, plus a hand-picked four-colour palette.
- **Section previews:** each home page section in the order editor now has a small wireframe.
- **Faster questions:** ↑ and ↓ on every FAQ, with positions renumbered automatically.
- **Announcement helpers:** suggestions for common link text and a list of the site's own pages for the address.
- **Resources explained:** the shelf now says what it is for, separates office-only from client-facing links, and offers suggestions for sections and titles.
- **Family photo:** the upload in Text and contact now really is the photo beside the family story, as well as the round pill on the hero.

### Fixed
- Corner style now changes photos, cards and panels instead of only the theme values.

### Database
- `bookings.reminded_at` records which appointments have had a reminder text. `flask --app app init-db` adds it.

### Deployment
- `vercel.json` now exists for one reason only: the daily reminder cron at 12:00 UTC. Zero-configuration Flask detection, `public/` CDN assets and `.python-version` are unchanged and documented.

## [3.0.0] - 2026-10-29

### Changed
- **Full visual redesign: paper, ink and gold.**
  - Warm paper ground, a whisper of grain, and editorial Fraunces headings with italic accent words instead of stacked white rounded cards.
  - Sections sit on coloured bands that draw their own shaped seam above themselves (wave, arch, tear, scallop, tilt, curve), so any order the agents choose still joins cleanly.
  - Section numbers are generated from the live order, so hiding or moving a section keeps the editorial numbering honest.
- **Hero:** two arch-cropped portraits on a slowly morphing gold field, the rotating headline with a marker highlight, live open-now status and a company count.
- **Coverage:** a large open list of what is insured; hovering or opening a line changes a paper arch preview beside it.
- **Quote:** the two-step form sits on a clipped sheet of paper with ruled fields.
- **Claims:** three numbered steps and a company finder that opens a dark policy card with a large claims number.
- **Documents:** a drag-or-scroll shelf of tilted paper sheets with folded corners.
- **About:** the family photo in an arch on a gold backdrop, founders as hover-reveal portraits, and figures set as a ruled ledger row.
- **Reviews, FAQ and contact:** one large quote at a time, a ruled question list, and phone numbers as the closing typography.
- **Inner pages:** booking, requests, confirmation, error and privacy pages use the same paper-sheet language.
- **Motion:** subtle morphing frames, hover reveals everywhere, scrolling galleries, a scroll progress hairline, a small trailing cursor ring on mouse devices and a soft lamp inside the dark bands. All of it is off for `prefers-reduced-motion`.
- **Mobile:** the headline comes first, the portrait pair follows, and the quick-action dock is restyled.
- **Portal:** ink sidebar, paper workspace, ruled tables and fewer shadows, to match the new brand.

### Added
- **Replies from the portal:** answer a website request and the reply is emailed and kept with the request. Messages can be filtered to unread and downloaded as CSV.
- **Appointments taken by phone:** add one to the same calendar, with an optional confirmation email, and download all appointments as CSV.
- **Time off:** mark days or ranges away. The booking calendar skips them and the website's open-now badge says the office is away.
- **Test email:** a button on Hours and booking that checks the mail account without waiting for a real booking.
- **My account:** agents can change their own password.
- **Backup and exports:** one JSON file for everything editable on the website, plus CSV downloads of messages, appointments and FAQs.
- **Vercel verification:** `.python-version` pins Python 3.13; the README documents the zero-configuration Flask deployment (no `vercel.json`, `public/` served at `/static`).
- `pytest` now finds the `otto` package from the project root, so the documented test command works as written.

### Database
- `messages.replied_at` and `messages.reply_body` keep replies beside the request.
- New `time_off` table. `flask --app app init-db` adds both without touching existing data.

## [2.2.0] - 2026-10-30

### Changed
- **Calmer motion:**
  - removed the custom cursor, the magnetic buttons, the tilt-with-the-mouse effect and the cursor spotlight
  - coverage pictures now change in a fixed spot beside the list instead of following the pointer
- **Top banner:**
  - the rotating sayings span the full width in a box of fixed height, and each one is sized to fill it, so the page below never moves
  - the logo sits large behind the lower right on a transparent background, with the badges around it
- **Find your company:**
  - a search box and a grid of logos
  - choosing one shows a card with its claims line in large type, billing number, website and a reminder to call us
- **Family agency section:**
  - the story sits beside the family photo
  - the founders appear as rectangular portraits with an offset colour frame, with their name, role and bio beside them

### Added
- Rectangular portraits cut from the original headshots. `init-db` switches existing sites over to them.

## [2.1.0] - 2026-10-30

### Changed
- **Phones:** (937) 545-6148 is now the office number shown everywhere, and (937) 610-0088 is labelled as the cell. `init-db` fixes sites that saved them the other way round.
- **Fonts:** Fraunces (soft setting) for headings and Figtree for text, both self-hosted.
- **Top banner:**
  - the headline rotates through several sayings, with a word-by-word blur transition, a highlighter sweep and progress dots
  - a large logo replaces the photo, with a slowly morphing shape, a turning dashed ring and floating badges that follow the cursor
- **About:** the family photo now sits on the tilted yellow backdrop. Bios appear when you hover over or focus a portrait.
- **Sections:** set on coloured bands with drawn edges (wave, curve, tilt, scallop) instead of white boxes. Each band draws its own edge, so any order the agents choose still joins cleanly.
- **Coverage:** an open list. Hovering a line floats its picture beside the cursor, and clicking opens the details.
- **Claims:** three illustrated steps, then a list of companies. Hovering a row reveals billing and website.
- **Documents:** a horizontal gallery of paper sheets that can be dragged, scrolled or stepped with arrows.
- **Other sections:** quick tasks on navy with a cursor spotlight, the quote form on a gold band, big phone numbers in Talk to us, and an open FAQ list.

### Added
- **Ribbon section:** a tilted, scrolling ribbon of what we insure.
- **Cursor effects:** a custom cursor ring and buttons that lean toward the pointer. Both apply only on mouse devices and are switched off for visitors who prefer reduced motion.
- **Portal:** edit the rotating headlines (one per line). Phone fields are now labelled Office and Cell.

## [2.0.0] - 2026-10-29

### Changed
- **Design:** returned to the clean 1.1 look that worked best (serif headings, navy, rounded photos and cards) and rebuilt it around research on insurance sites:
  - primary actions above the fold in a contrasting gold
  - task-based navigation
  - click-to-call everywhere
  - a short, two-step quote form
- **Home page:**
  - photo hero with floating badges for the agents, open-now status and companies
  - four quick tasks with illustrations (quote, claim, document, call)
  - a scrolling company logo strip
  - coverage tabs with a picture for each type
  - a two-step quote request
  - a searchable claims directory with three claim steps
  - document request tiles
  - an about section with team cards and animated figures
  - client reviews (hidden until real ones are added)
  - an FAQ accordion
  - a contact card that highlights today's hours
- **Mobile:** an animated menu and the bottom quick-action bar.
- **Portal:** redesigned with a sidebar, a dashboard and confirmation toasts. Appointments moved to `/portal/appointments`.

### Added
- **Website editing in the portal, live on save:**
  - headline, intro and top photo
  - phones, email and address, with a switch to hide the street
  - an announcement banner
  - a colour scheme (four presets) and corner style
  - which home page sections show, and in what order
  - insurance companies (logos, claims and billing numbers)
  - coverage types (text, checklist, picture)
  - people (bios, photos)
  - client reviews
- **Uploads:** photo and logo uploads stored in Postgres. Each file is checked by its contents and limited to 3 MB.
- **Logins:** manage logins in the portal (add, reset password, remove).
- **Quote endpoint:** `POST /quote` for the home page quote form.
- **Database:** new tables `site_settings`, `carriers`, `coverage`, `team`, `testimonials` and `media`. `init-db` creates and fills them.

## [1.2.1] - 2026-10-29

### Changed
- **Home page first screen:** now fits in one view. The motto, the one-line description, the open-now status and the three quick actions (start a quote, claims numbers, book a call) are all visible without scrolling.
- **Claims:** a full-width, two-column list of all eight companies with logos and large tap-to-call claims numbers. The duplicate family photo was removed.

### Added
- **Mobile quick-action bar** fixed at the bottom of small screens: Call, Quote, Claims, Book.

## [1.2.0] - 2026-10-29

### Changed
- **New address.** The agency moved to 6650 Kilbourne Rd., Sunbury, OH 43074 and works from home. The site, emails, privacy policy and footer show the new address, list visits as by appointment, and include the second phone line (937) 545-6148.
- **New design built with the design-taste-frontend skill (direction "The sentence is the layout"):**
  - The motto "Appreciated, not tolerated." is set at poster size across two fields, with a strip of the family photo inside the sentence.
  - The header changes colour with each section beneath it.
  - Coverage is a list you can open, one kind at a time.
  - Claims lines appear as a table with carrier logos.
  - Andi and Glenn's portraits sit as drop capitals in their bios.
  - The page ends with the email address and phone number as the closing lines.
- **Booking.** Appointments are now "Book a call". Visitors choose a phone call, a video call, or in person by arrangement, and a phone number is required for phone calls.

### Added
- **Quote builder.** A sentence on the home page ("I'd like a quote for my home, car, boat...") where visitors tap the things they own. It opens the request form with the quote already filled in, and works without JavaScript.
- **Portal.** The bookings list shows how each client wants to meet.
- **Database.** A `bookings.meeting_kind` column. Running `flask --app app init-db` adds it to existing databases.

### Removed
- The old Fishburg Road office photo.

## [1.1.0] - 2026-10-29

### Changed
- **Full visual redesign:**
  - Newsreader serif headings with Hanken Grotesk text.
  - The agency's swoosh logo in the header, footer, favicon and portal.
  - Rounded photo and card treatment and a calmer navy palette.
- **Home page:** rebuilt around a photo hero with the agents' portraits and live open-now status. It adds:
  - a strip of all eight carrier logos
  - a tabbed coverage explorer
  - quick document request tiles
  - a carrier directory with logos, claims and billing numbers
  - an about section with portraits, facts and community work
  - a motto band, a two-column FAQ and a visit card with today's hours highlighted
- **Booking, request, confirmation, privacy and error pages:** restyled with page headers and form panels.
- **Booking page:** opens on the first day that still has free times.
- **Mobile:** collapsible menu on small screens.

### Added
- Carrier logos and agency mark under `public/static/img/`.

## [1.0.0] - 2026-10-29

First release. It replaces the Anvil app.

### Added
- Flask application with PostgreSQL storage, deployable on Vercel or any Python host.
- Redesigned public home page:
  - coverage list
  - claims and billing numbers for all eight carriers
  - the agency's story and community record
  - FAQs and contact details
  - a live open-now status
- Appointment booking with server-side slot checks and per-slot locking to prevent double booking. Confirmation emails go to the client and the office.
- Request form for proof of insurance cards, declarations pages, certificates, verification letters, quotes and general questions.
- Agent portal for appointments, messages, office hours and booking rules, FAQs and resource links.
- CLI commands: `init-db`, `create-agent`, `import-faqs`.
- Test suite covering scheduling, validation and the main user flows.
- Self-hosted Hanken Grotesk font. No third-party requests from any page.

### Security
- Every server action that the Anvil app exposed without authentication now requires an agent login. This includes sending email, listing bookings and messages, and deleting bookings.
- CSRF protection on all forms, a strict Content-Security-Policy, secure session cookies and login lockout after repeated failures.
