-- ============================================================
--  Suketu Sarthi Insurance & Investments
--  Contact-form database schema
--  Compatible with: SQLite 3 · MySQL 8 · PostgreSQL 14+
-- ============================================================

-- ------------------------------------------------------------
-- 1. CONTACT SUBMISSIONS
--    One row per form submission from contact.html
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS contact_submissions (
    id               INTEGER       PRIMARY KEY AUTOINCREMENT,

    -- Form fields
    name             TEXT          NOT NULL,           -- "Full Name" (required)
    phone            TEXT          NOT NULL,           -- "Phone Number" (required)
    email            TEXT,                             -- "Email Address" (optional)
    preferred_time   TEXT,                             -- dropdown selection
    service_interest TEXT,                             -- intent-button selection
    message          TEXT,                             -- free-text message (optional)

    -- Metadata
    source_page      TEXT          DEFAULT 'contact.html',
    ip_address       TEXT,                             -- store for dedup / abuse detection
    submitted_at     DATETIME      DEFAULT CURRENT_TIMESTAMP,

    -- CRM status
    -- Allowed: new | contacted | converted | closed
    status           TEXT          NOT NULL DEFAULT 'new',

    CONSTRAINT chk_status CHECK (status IN ('new','contacted','converted','closed'))
);

-- Useful indexes
CREATE INDEX IF NOT EXISTS idx_sub_status   ON contact_submissions(status);
CREATE INDEX IF NOT EXISTS idx_sub_date     ON contact_submissions(submitted_at);
CREATE INDEX IF NOT EXISTS idx_sub_phone    ON contact_submissions(phone);
CREATE INDEX IF NOT EXISTS idx_sub_service  ON contact_submissions(service_interest);


-- ------------------------------------------------------------
-- 2. STATUS HISTORY LOG  (audit trail)
--    Every time a submission's status changes, log it here.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS submission_status_log (
    id               INTEGER       PRIMARY KEY AUTOINCREMENT,
    submission_id    INTEGER       NOT NULL
                                   REFERENCES contact_submissions(id)
                                   ON DELETE CASCADE,
    old_status       TEXT,
    new_status       TEXT          NOT NULL,
    changed_by       TEXT          DEFAULT 'system',  -- agent name or 'system'
    note             TEXT,                             -- internal note on the change
    changed_at       DATETIME      DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_log_sub ON submission_status_log(submission_id);


-- ------------------------------------------------------------
-- 3. CONTACT PREFERENCES  (consent & channel)
--    One row per submission (optional, created on first update)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS contact_preferences (
    id               INTEGER       PRIMARY KEY AUTOINCREMENT,
    submission_id    INTEGER       UNIQUE
                                   REFERENCES contact_submissions(id)
                                   ON DELETE CASCADE,
    consent_given    INTEGER       NOT NULL DEFAULT 0,     -- 0 = no, 1 = yes
    preferred_channel TEXT         DEFAULT 'phone',        -- phone | email | whatsapp
    do_not_contact   INTEGER       NOT NULL DEFAULT 0,     -- 1 = DNC flag
    updated_at       DATETIME      DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
--  USEFUL VIEWS
-- ============================================================

-- All open (actionable) leads
CREATE VIEW IF NOT EXISTS v_open_leads AS
SELECT
    id,
    name,
    phone,
    email,
    service_interest,
    preferred_time,
    submitted_at
FROM contact_submissions
WHERE status IN ('new', 'contacted')
ORDER BY submitted_at DESC;


-- Summary by service interest
CREATE VIEW IF NOT EXISTS v_service_breakdown AS
SELECT
    COALESCE(service_interest, 'Not specified') AS service,
    COUNT(*)                                     AS total,
    SUM(CASE WHEN status = 'new'       THEN 1 ELSE 0 END) AS new_count,
    SUM(CASE WHEN status = 'contacted' THEN 1 ELSE 0 END) AS contacted_count,
    SUM(CASE WHEN status = 'converted' THEN 1 ELSE 0 END) AS converted_count
FROM contact_submissions
GROUP BY service_interest
ORDER BY total DESC;


-- ============================================================
--  SAMPLE DATA (remove before production)
-- ============================================================
INSERT INTO contact_submissions (name, phone, email, preferred_time, service_interest, message, status) VALUES
  ('Ramesh Patil',  '+91 98765 43210', 'ramesh@example.com', 'Morning (9am – 12pm)',   'Life Insurance',   'Looking for term plan for family of 4', 'new'),
  ('Sunita Mehta',  '+91 91234 56789', NULL,                 'Evening (4pm – 7pm)',    'Health Insurance', 'Need floater policy for parents',        'contacted'),
  ('Arun Desai',    '+91 70000 11111', 'arun.d@example.com', 'Anytime works for me',   'Mutual Funds',     'Want to start a SIP',                    'new'),
  ('Priya Joshi',   '+91 88888 22222', 'priya@example.com',  'Afternoon (12pm – 4pm)', 'Retirement',       'Planning retirement in 15 years',        'converted'),
  ('Vijay Kumar',   '+91 77777 33333', NULL,                 'Morning (9am – 12pm)',   'Vehicle Insurance','Car insurance renewal enquiry',          'new');
