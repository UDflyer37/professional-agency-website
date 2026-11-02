CREATE TABLE IF NOT EXISTS agents (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email TEXT NOT NULL,
    name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    failed_logins INTEGER NOT NULL DEFAULT 0,
    locked_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS agents_email_key ON agents (lower(email));

-- weekday follows Python's date.weekday(): 0 is Monday.
CREATE TABLE IF NOT EXISTS office_hours (
    weekday SMALLINT PRIMARY KEY CHECK (weekday BETWEEN 0 AND 6),
    is_open BOOLEAN NOT NULL,
    opens_at TIME NOT NULL,
    closes_at TIME NOT NULL,
    CHECK (opens_at < closes_at)
);

CREATE TABLE IF NOT EXISTS booking_rules (
    id SMALLINT PRIMARY KEY CHECK (id = 1),
    slot_minutes INTEGER NOT NULL CHECK (slot_minutes BETWEEN 10 AND 240),
    days_ahead INTEGER NOT NULL CHECK (days_ahead BETWEEN 1 AND 180),
    per_slot INTEGER NOT NULL CHECK (per_slot BETWEEN 1 AND 10)
);

CREATE TABLE IF NOT EXISTS bookings (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    client_name TEXT NOT NULL,
    client_email TEXT NOT NULL,
    client_phone TEXT NOT NULL DEFAULT '',
    reason TEXT NOT NULL DEFAULT '',
    starts_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS bookings_starts_at ON bookings (starts_at);
-- Added in 1.2.0 when the agency moved to working from home.
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS meeting_kind TEXT NOT NULL DEFAULT 'phone';

CREATE TABLE IF NOT EXISTS messages (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sender_name TEXT NOT NULL,
    sender_email TEXT NOT NULL,
    sender_phone TEXT NOT NULL DEFAULT '',
    topic TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    read_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS messages_created_at ON messages (created_at);

CREATE TABLE IF NOT EXISTS faqs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    position INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS links (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    audience TEXT NOT NULL CHECK (audience IN ('agent', 'client')),
    section TEXT NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL CHECK (url ~ '^(https?://|tel:|mailto:)')
);

-- Added in 2.0.0: everything the agents can change on the website without a deploy.
CREATE TABLE IF NOT EXISTS media (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content_type TEXT NOT NULL CHECK (content_type IN ('image/jpeg', 'image/png', 'image/webp')),
    filename TEXT NOT NULL,
    data BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS site_settings (
    key TEXT PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS carriers (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    website TEXT NOT NULL DEFAULT '',
    claims_phone TEXT NOT NULL DEFAULT '',
    billing_phone TEXT NOT NULL DEFAULT '',
    logo_static TEXT NOT NULL DEFAULT '',
    logo_media_id BIGINT REFERENCES media (id) ON DELETE SET NULL,
    logo_height INTEGER NOT NULL DEFAULT 40 CHECK (logo_height BETWEEN 16 AND 80),
    position INTEGER NOT NULL DEFAULT 0,
    visible BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS coverage (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    headline TEXT NOT NULL,
    summary TEXT NOT NULL,
    items JSONB NOT NULL DEFAULT '[]'::jsonb,
    illustration TEXT NOT NULL DEFAULT 'home',
    position INTEGER NOT NULL DEFAULT 0,
    visible BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS team (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT '',
    bio TEXT NOT NULL DEFAULT '',
    photo_static TEXT NOT NULL DEFAULT '',
    photo_media_id BIGINT REFERENCES media (id) ON DELETE SET NULL,
    position INTEGER NOT NULL DEFAULT 0,
    visible BOOLEAN NOT NULL DEFAULT true
);

CREATE TABLE IF NOT EXISTS testimonials (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    quote TEXT NOT NULL,
    name TEXT NOT NULL,
    detail TEXT NOT NULL DEFAULT '',
    position INTEGER NOT NULL DEFAULT 0,
    visible BOOLEAN NOT NULL DEFAULT true
);

-- Added in 2.3.0: replies sent from the portal, kept next to the request they answer.
ALTER TABLE messages ADD COLUMN IF NOT EXISTS replied_at TIMESTAMPTZ;
ALTER TABLE messages ADD COLUMN IF NOT EXISTS reply_body TEXT NOT NULL DEFAULT '';

-- Added in 3.1.0: the owner can ask for a reminder text before each appointment.
ALTER TABLE bookings ADD COLUMN IF NOT EXISTS reminded_at TIMESTAMPTZ;

-- Added in 2.3.0: days the office is away, so the booking calendar skips them.
CREATE TABLE IF NOT EXISTS time_off (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    starts_on DATE NOT NULL,
    ends_on DATE NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (ends_on >= starts_on)
);
CREATE INDEX IF NOT EXISTS time_off_range ON time_off (starts_on, ends_on);

-- Added in 3.2.0: sticky notes the owner can leave for herself.
CREATE TABLE IF NOT EXISTS notes (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    body TEXT NOT NULL,
    color TEXT NOT NULL DEFAULT 'gold' CHECK (color IN ('gold', 'rose', 'sky', 'mint', 'lilac')),
    pos_x INTEGER NOT NULL DEFAULT 24,
    pos_y INTEGER NOT NULL DEFAULT 24,
    z_index INTEGER NOT NULL DEFAULT 0,
    pinned BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE notes ADD COLUMN IF NOT EXISTS pinned BOOLEAN NOT NULL DEFAULT false;
CREATE INDEX IF NOT EXISTS notes_updated_at ON notes (updated_at DESC);
