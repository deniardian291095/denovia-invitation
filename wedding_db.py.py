#!/usr/bin/env python3
"""
wedding_db.py  ─  Multi-Tenant Wedding Invitation Platform
Roles: super_admin | client (per-wedding admin) | guest (view only)

Usage:
  python3 wedding_db.py            → buat/cek database + tampilkan info
  python3 wedding_db.py --serve    → jalankan API server (port 8000)
  python3 wedding_db.py --reset    → hapus & buat ulang database
"""
import sqlite3, json, hashlib, sys, os
from datetime import datetime, timedelta

# Railway & hosting: pakai environment variables
DB_PATH = os.environ.get('DATABASE_PATH', 'wedding.db')
PORT    = int(os.environ.get('PORT', 8000))

SCHEMA = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode  = WAL;

-- ─────────────────────────────────────────────────────────────
-- TABLE: service_packages — Paket layanan (Basic & Premium)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS service_packages (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         VARCHAR(50) NOT NULL UNIQUE,   -- 'basic' | 'premium'
    label        VARCHAR(100) NOT NULL,
    description  TEXT,
    max_gallery  INTEGER DEFAULT 10,
    max_rsvp     INTEGER DEFAULT 100,
    features     TEXT DEFAULT '{}',             -- JSON fitur toggle
    price        INTEGER DEFAULT 0,             -- harga (IDR)
    is_active    BOOLEAN NOT NULL DEFAULT 1,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────────────────────
-- TABLE: users — Super Admin & Client accounts
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          VARCHAR(150) NOT NULL,
    username      VARCHAR(100) UNIQUE NOT NULL,
    email         VARCHAR(150),
    password_hash VARCHAR(255) NOT NULL,
    role          VARCHAR(20) NOT NULL DEFAULT 'client'
                      CHECK(role IN ('super_admin','client')),
    avatar_data   TEXT,
    package_id    INTEGER REFERENCES service_packages(id),
    account_status VARCHAR(20) NOT NULL DEFAULT 'pending'
                      CHECK(account_status IN ('pending','active','expired','rejected')),
    is_active     BOOLEAN NOT NULL DEFAULT 1,
    expires_at    DATETIME,
    approved_at   DATETIME,
    approved_by   INTEGER REFERENCES users(id),
    payment_proof TEXT,
    last_login    DATETIME,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────────────────────
-- TABLE: weddings — Satu per client
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS weddings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    client_user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    package_id      INTEGER NOT NULL REFERENCES service_packages(id),
    groom_name      VARCHAR(150) NOT NULL DEFAULT 'Nama Pria',
    bride_name      VARCHAR(150) NOT NULL DEFAULT 'Nama Wanita',
    groom_parents   VARCHAR(255),
    bride_parents   VARCHAR(255),
    groom_photo     TEXT,
    bride_photo     TEXT,
    wedding_date    DATE NOT NULL DEFAULT '2026-01-01',
    wedding_city    VARCHAR(100),
    invite_code     VARCHAR(50) NOT NULL UNIQUE,
    slug            VARCHAR(100) UNIQUE,         -- URL cantik: deni-anisa
    music_url       VARCHAR(255) DEFAULT '',
    website_title   VARCHAR(255),
    features        TEXT DEFAULT '{"music":1,"countdown":1,"rsvp":1,"wishes":1,"gift":1,"gallery":1,"maintenance":0}',
    is_active       BOOLEAN NOT NULL DEFAULT 1,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────────────────────
-- TABLE: events — Detail acara (akad, resepsi, dll)
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS events (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    wedding_id       INTEGER NOT NULL REFERENCES weddings(id) ON DELETE CASCADE,
    event_type       VARCHAR(50) NOT NULL,   -- 'akad' | 'resepsi'
    event_name       VARCHAR(150) NOT NULL,
    event_date       DATE NOT NULL,
    event_time_start TIME NOT NULL,
    event_time_end   TIME,
    venue_name       VARCHAR(200),
    venue_address    TEXT,
    venue_city       VARCHAR(100),
    maps_url         TEXT,
    is_active        BOOLEAN NOT NULL DEFAULT 1,
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────────────────────
-- TABLE: rsvp — Konfirmasi kehadiran tamu
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rsvp (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    wedding_id  INTEGER NOT NULL REFERENCES weddings(id) ON DELETE CASCADE,
    guest_name  VARCHAR(150) NOT NULL,
    guest_count INTEGER NOT NULL DEFAULT 1 CHECK(guest_count >= 1),
    attendance  VARCHAR(20) NOT NULL DEFAULT 'pending'
                    CHECK(attendance IN ('hadir','tidak','pending')),
    message     TEXT,
    phone       VARCHAR(20),
    ip_address  VARCHAR(45),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────────────────────
-- TABLE: wishes — Ucapan tamu
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS wishes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    wedding_id  INTEGER NOT NULL REFERENCES weddings(id) ON DELETE CASCADE,
    guest_name  VARCHAR(150) NOT NULL,
    message     TEXT NOT NULL,
    is_approved BOOLEAN NOT NULL DEFAULT 1,
    is_pinned   BOOLEAN NOT NULL DEFAULT 0,
    ip_address  VARCHAR(45),
    rsvp_id     INTEGER REFERENCES rsvp(id) ON DELETE SET NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────────────────────
-- TABLE: gallery — Galeri foto
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS gallery (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    wedding_id  INTEGER NOT NULL REFERENCES weddings(id) ON DELETE CASCADE,
    title       VARCHAR(200),
    description TEXT,
    file_name   VARCHAR(255),
    file_url    TEXT,
    file_data   TEXT,
    file_type   VARCHAR(50) DEFAULT 'image/jpeg',
    sort_order  INTEGER DEFAULT 0,
    is_featured BOOLEAN NOT NULL DEFAULT 0,
    is_active   BOOLEAN NOT NULL DEFAULT 1,
    like_count  INTEGER NOT NULL DEFAULT 0,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────────────────────
-- TABLE: photo_likes
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS photo_likes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    gallery_id INTEGER NOT NULL REFERENCES gallery(id) ON DELETE CASCADE,
    wedding_id INTEGER NOT NULL REFERENCES weddings(id) ON DELETE CASCADE,
    session_id VARCHAR(100),
    ip_address VARCHAR(45),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(gallery_id, session_id)
);

-- ─────────────────────────────────────────────────────────────
-- TABLE: bank_accounts — Amplop digital / rekening
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bank_accounts (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    wedding_id     INTEGER NOT NULL REFERENCES weddings(id) ON DELETE CASCADE,
    bank_name      VARCHAR(100) NOT NULL,
    account_number VARCHAR(50) NOT NULL,
    account_name   VARCHAR(150) NOT NULL,
    phone_number   VARCHAR(20),
    sort_order     INTEGER DEFAULT 0,
    is_active      BOOLEAN NOT NULL DEFAULT 1,
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────────────────────
-- TABLE: gift_address — Alamat kado fisik
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS gift_address (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    wedding_id     INTEGER NOT NULL REFERENCES weddings(id) ON DELETE CASCADE UNIQUE,
    recipient_name VARCHAR(150) NOT NULL,
    street_address TEXT NOT NULL,
    city           VARCHAR(100),
    province       VARCHAR(100),
    postal_code    VARCHAR(10),
    phone          VARCHAR(20),
    notes          TEXT,
    updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────────────────────
-- TABLE: love_story — Timeline kisah cinta
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS love_story (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    wedding_id  INTEGER NOT NULL REFERENCES weddings(id) ON DELETE CASCADE,
    year        INTEGER NOT NULL,
    month       INTEGER,
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    sort_order  INTEGER DEFAULT 0,
    is_active   BOOLEAN NOT NULL DEFAULT 1
);

-- ─────────────────────────────────────────────────────────────
-- TABLE: invite_codes — Kode undangan tamu
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS invite_codes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    wedding_id INTEGER NOT NULL REFERENCES weddings(id) ON DELETE CASCADE,
    code       VARCHAR(50) NOT NULL UNIQUE,
    label      VARCHAR(100),
    max_uses   INTEGER DEFAULT NULL,
    used_count INTEGER DEFAULT 0,
    is_active  BOOLEAN NOT NULL DEFAULT 1,
    expires_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────────────────────
-- TABLE: activity_log — Audit trail
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS activity_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    wedding_id  INTEGER REFERENCES weddings(id) ON DELETE SET NULL,
    action_type VARCHAR(50) NOT NULL,
    description TEXT NOT NULL,
    entity_type VARCHAR(50),
    entity_id   INTEGER,
    actor_name  VARCHAR(150),
    ip_address  VARCHAR(45),
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────────────────────
-- INDEXES
-- ─────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_weddings_client   ON weddings(client_user_id);
CREATE INDEX IF NOT EXISTS idx_rsvp_wedding      ON rsvp(wedding_id);
CREATE INDEX IF NOT EXISTS idx_wishes_wedding    ON wishes(wedding_id);
CREATE INDEX IF NOT EXISTS idx_gallery_wedding   ON gallery(wedding_id);
CREATE INDEX IF NOT EXISTS idx_likes_gallery     ON photo_likes(gallery_id);
CREATE INDEX IF NOT EXISTS idx_events_wedding    ON events(wedding_id);
CREATE INDEX IF NOT EXISTS idx_activity_wedding  ON activity_log(wedding_id);
CREATE INDEX IF NOT EXISTS idx_invite_code       ON invite_codes(code);
CREATE INDEX IF NOT EXISTS idx_users_role        ON users(role);
"""

def hp(pw):  return hashlib.sha256(pw.encode()).hexdigest()

def make_slug(groom, bride):
    """Generate URL slug cantik: deni_anisa (tampil sebagai deni&anisa di URL)"""
    import unicodedata, re as _re
    def clean(s):
        # Normalize unicode (hapus aksen)
        s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode()
        s = s.lower().strip()
        # Hapus karakter non-alphanumeric kecuali spasi
        s = _re.sub(r'[^a-z0-9\s]', '', s)
        s = s.strip()
        # Ambil nama depan saja
        return s.split()[0] if s.split() else s
    g = clean(groom or 'mempelai')
    b = clean(bride or 'pasangan')
    return f"{g}_{b}"   # deni_anisa → URL: /deni_anisa (display: deni&anisa)

def ts(d=0): return (datetime.now()-timedelta(days=d)).strftime('%Y-%m-%d %H:%M:%S')
def rows_to_list(rows): return [dict(r) for r in rows]

def get_stats(conn, wid):
    c = conn.cursor()
    return {
        'total_rsvp':    c.execute("SELECT COUNT(*) FROM rsvp WHERE wedding_id=?",(wid,)).fetchone()[0],
        'hadir':         c.execute("SELECT COUNT(*) FROM rsvp WHERE wedding_id=? AND attendance='hadir'",(wid,)).fetchone()[0],
        'tidak_hadir':   c.execute("SELECT COUNT(*) FROM rsvp WHERE wedding_id=? AND attendance='tidak'",(wid,)).fetchone()[0],
        'pending':       c.execute("SELECT COUNT(*) FROM rsvp WHERE wedding_id=? AND attendance='pending'",(wid,)).fetchone()[0],
        'total_guests':  c.execute("SELECT COALESCE(SUM(guest_count),0) FROM rsvp WHERE wedding_id=? AND attendance='hadir'",(wid,)).fetchone()[0],
        'total_wishes':  c.execute("SELECT COUNT(*) FROM wishes WHERE wedding_id=? AND is_approved=1",(wid,)).fetchone()[0],
        'total_gallery': c.execute("SELECT COUNT(*) FROM gallery WHERE wedding_id=? AND is_active=1",(wid,)).fetchone()[0],
        'total_likes':   c.execute("SELECT COALESCE(SUM(like_count),0) FROM gallery WHERE wedding_id=?",(wid,)).fetchone()[0],
    }

def seed(conn):
    c = conn.cursor()

    # ── Paket Layanan ──
    c.execute("""INSERT OR IGNORE INTO service_packages(id,name,label,description,max_gallery,max_rsvp,features,price) VALUES
        (1,'basic','Basic','Paket undangan digital standar',10,100,
         '{"music":0,"countdown":1,"rsvp":1,"wishes":1,"gift":0,"gallery":1,"maintenance":0}',0)""")
    c.execute("""INSERT OR IGNORE INTO service_packages(id,name,label,description,max_gallery,max_rsvp,features,price) VALUES
        (2,'premium','Premium','Paket undangan digital lengkap dengan semua fitur',100,500,
         '{"music":1,"countdown":1,"rsvp":1,"wishes":1,"gift":1,"gallery":1,"maintenance":0}',299000)""")
    conn.commit()

    # ── Users: Super Admin + 2 Client ──
    exp2 = (datetime.now() + timedelta(days=60)).strftime('%Y-%m-%d %H:%M:%S')

    c.execute("INSERT OR IGNORE INTO users(id,name,username,email,password_hash,role,account_status) VALUES(1,'Super Administrator','superadmin','super@denovia.com',?,'super_admin','active')",(hp('super2026'),))

    # Client 1: Deni Ardianto — mempelai Deni & Anisa — Premium
    c.execute("INSERT OR IGNORE INTO users(id,name,username,email,password_hash,role,package_id,account_status,is_active,expires_at) VALUES(2,'Deni Ardianto','deni','deni@email.com',?,'client',2,'active',1,?)",(hp('deni2026'),exp2))

    # Client 2: Bagas Pamungkas — mempelai Bagas & Anisa — Basic
    c.execute("INSERT OR IGNORE INTO users(id,name,username,email,password_hash,role,package_id,account_status,is_active,expires_at) VALUES(3,'Bagas Pamungkas','bagas','bagas@email.com',?,'client',1,'active',1,?)",(hp('bagas2026'),exp2))
    conn.commit()

    # ── Weddings ──
    c.execute("""INSERT OR IGNORE INTO weddings(id,client_user_id,package_id,groom_name,bride_name,groom_parents,bride_parents,
        wedding_date,wedding_city,invite_code,website_title,features) VALUES
        (1,2,2,'Deni Ardianto','Anisa Putri','Bapak Ardianto & Ibu Yuni',
         'Bapak Santoso & Ibu Dewi','2026-08-17','Purwokerto','WED2026',
         'Deni & Anisa Wedding',
         '{"music":1,"countdown":1,"rsvp":1,"wishes":1,"gift":1,"gallery":1,"maintenance":0}')""")
    c.execute("""INSERT OR IGNORE INTO weddings(id,client_user_id,package_id,groom_name,bride_name,groom_parents,bride_parents,
        wedding_date,wedding_city,invite_code,website_title,features) VALUES
        (2,3,1,'Bagas Pamungkas','Anisa Ramadhani','Bapak Hendra & Ibu Wulan',
         'Bapak Rudi & Ibu Kartini','2026-10-10','Semarang','WED2026B',
         'Bagas & Anisa Wedding',
         '{"music":0,"countdown":1,"rsvp":1,"wishes":1,"gift":0,"gallery":1,"maintenance":0}')""")
    conn.commit()

    # ── Set slug untuk wedding seed (panggil Python function, bukan SQL) ──
    c.execute("UPDATE weddings SET slug=? WHERE id=1", (make_slug('Deni Ardianto','Anisa Putri'),))
    c.execute("UPDATE weddings SET slug=? WHERE id=2", (make_slug('Bagas Pamungkas','Anisa Ramadhani'),))
    conn.commit()

    # ── Events — Wedding 1: Deni & Anisa ──
    for row in [
        (1,'akad','Akad Nikah','2026-08-17','08:00','10:00','Masjid Agung Purwokerto','Jl. KH. Ahmad Dahlan No. 1, Purwokerto','Purwokerto','https://maps.google.com/?q=Masjid+Agung+Purwokerto'),
        (1,'resepsi','Walimatul Ursy','2026-08-17','11:00',None,'Gedung Serbaguna Purwokerto','Jl. Jend. Sudirman No. 5, Purwokerto','Purwokerto','https://maps.google.com/?q=Gedung+Serbaguna+Purwokerto'),
    ]:
        c.execute("INSERT OR IGNORE INTO events(wedding_id,event_type,event_name,event_date,event_time_start,event_time_end,venue_name,venue_address,venue_city,maps_url) VALUES(?,?,?,?,?,?,?,?,?,?)", row)

    # ── Events — Wedding 2: Bagas & Anisa ──
    for row in [
        (2,'akad','Akad Nikah','2026-10-10','09:00','11:00','Masjid Baiturrahman Semarang','Jl. Pemuda No. 10, Semarang','Semarang','https://maps.google.com/?q=Masjid+Baiturrahman+Semarang'),
        (2,'resepsi','Walimatul Ursy','2026-10-10','12:00',None,'Hotel Gumaya Tower','Jl. Gajah Mada No. 59, Semarang','Semarang','https://maps.google.com/?q=Hotel+Gumaya+Semarang'),
    ]:
        c.execute("INSERT OR IGNORE INTO events(wedding_id,event_type,event_name,event_date,event_time_start,event_time_end,venue_name,venue_address,venue_city,maps_url) VALUES(?,?,?,?,?,?,?,?,?,?)", row)

    # ── Bank Accounts ──
    for row in [
        (1,'Bank BCA','1234567890','Deni Ardianto','081234567890',1),
        (1,'Bank Mandiri','0987654321','Anisa Putri','081987654321',2),
        (1,'Dana','081234567890','Deni Ardianto','081234567890',3),
        (2,'Bank BCA','9988776655','Bagas Pamungkas','085599887766',1),
        (2,'GoPay','085599887766','Bagas Pamungkas','085599887766',2),
    ]:
        c.execute("INSERT OR IGNORE INTO bank_accounts(wedding_id,bank_name,account_number,account_name,phone_number,sort_order) VALUES(?,?,?,?,?,?)", row)

    # ── Gift Address ──
    c.execute("INSERT OR IGNORE INTO gift_address(wedding_id,recipient_name,street_address,city,province,postal_code,phone) VALUES(1,'Deni Ardianto & Anisa Putri','Jl. Melati No. 10, RT 02/RW 05','Purwokerto','Jawa Tengah','53111','081234567890')")
    c.execute("INSERT OR IGNORE INTO gift_address(wedding_id,recipient_name,street_address,city,province,postal_code,phone) VALUES(2,'Bagas Pamungkas & Anisa Ramadhani','Jl. Anggrek No. 15, RT 03/RW 02','Semarang','Jawa Tengah','50131','085599887766')")

    # ── Love Story — Wedding 1: Deni & Anisa ──
    for row in [
        (1,2020,6,'Pertama Bertemu','Pertemuan tak terduga di sebuah seminar yang mengubah segalanya.',1),
        (1,2021,9,'Persahabatan Tumbuh','Dari sekadar kenalan, kami mulai sering berbagi cerita dan mimpi.',2),
        (1,2023,2,'Menjalin Hubungan','Dengan keberanian dan doa, kami resmi menjalin hubungan.',3),
        (1,2025,7,'Lamaran','Momen sakral saat keluarga bertemu dan restu diraih dengan penuh haru.',4),
        (1,2026,8,'Hari Pernikahan','Dengan penuh rasa syukur, kami menghalalkan cinta ini.',5),
    ]:
        c.execute("INSERT OR IGNORE INTO love_story(wedding_id,year,month,title,description,sort_order) VALUES(?,?,?,?,?,?)", row)

    # ── Love Story — Wedding 2: Bagas & Anisa ──
    for row in [
        (2,2021,3,'Pertama Bertemu','Bertemu di acara reunian yang tak terduga.',1),
        (2,2022,8,'Sering Berjumpa','Takdir mempertemukan kami kembali di setiap kesempatan.',2),
        (2,2024,1,'Menjalin Hubungan','Keberanian hadir, hubungan pun dimulai.',3),
        (2,2026,10,'Hari Pernikahan','Bersama, kami melangkah ke jenjang pernikahan.',4),
    ]:
        c.execute("INSERT OR IGNORE INTO love_story(wedding_id,year,month,title,description,sort_order) VALUES(?,?,?,?,?,?)", row)

    # ── Invite Codes ──
    c.execute("INSERT OR IGNORE INTO invite_codes(wedding_id,code,label) VALUES(1,'WED2026','Kode Umum')")
    c.execute("INSERT OR IGNORE INTO invite_codes(wedding_id,code,label) VALUES(2,'WED2026B','Kode Umum')")

    # ── Gallery (placeholder) ──
    for i in range(1,6):
        c.execute("INSERT OR IGNORE INTO gallery(wedding_id,title,file_name,sort_order,like_count) VALUES(1,?,?,?,?)",
                  (f'Foto Prewedding {i}',f'photo_{i:02d}.jpg',i,i*3))
    for i in range(1,4):
        c.execute("INSERT OR IGNORE INTO gallery(wedding_id,title,file_name,sort_order) VALUES(2,?,?,?)",
                  (f'Foto Prewedding {i}',f'photo_b{i:02d}.jpg',i))

    # ── Sample RSVP + Wishes — Wedding 1 ──
    for name,cnt,attend,msg,days in [
        ('Rizky Pratama',2,'hadir','Selamat berbahagia! Kami siap hadir.',7),
        ('Dewi Kartika',1,'hadir','Semoga sakinah mawaddah warahmah.',7),
        ('Hendra Gunawan',3,'hadir','Doa terbaik dari kami sekeluarga.',6),
        ('Budi Setiawan',2,'tidak','Mohon maaf tidak bisa hadir.',5),
        ('Ayu Lestari',1,'hadir','Barakallah untuk kalian!',5),
        ('Farhan Hidayat',2,'pending','',4),
    ]:
        created = ts(days)
        c.execute("INSERT INTO rsvp(wedding_id,guest_name,guest_count,attendance,message,created_at,updated_at) VALUES(1,?,?,?,?,?,?)",
                  (name,cnt,attend,msg,created,created))
        rid = c.lastrowid
        if msg:
            c.execute("INSERT INTO wishes(wedding_id,guest_name,message,rsvp_id,created_at) VALUES(1,?,?,?,?)",
                      (name,msg,rid,created))

    # ── Activity Log ──
    for row in [
        (1,'login','Deni Ardianto login ke dashboard','user','Deni Ardianto'),
        (1,'rsvp','Rizky Pratama mengisi RSVP — Hadir','rsvp','Rizky Pratama'),
        (1,'wish','Dewi Kartika mengirim ucapan','wish','Dewi Kartika'),
        (2,'login','Bagas Pamungkas login ke dashboard','user','Bagas Pamungkas'),
    ]:
        c.execute("INSERT INTO activity_log(wedding_id,action_type,description,entity_type,actor_name) VALUES(?,?,?,?,?)", row)

    conn.commit()
    print("  ✦ Seed data berhasil dimasukkan.")

def migrate_database(conn):
    """Jalankan migrasi kolom baru pada database yang sudah ada (ALTER TABLE)."""
    c = conn.cursor()
    # Daftar migrasi yang aman — lewati jika kolom sudah ada
    migrations = [
        # weddings table — slug
        "ALTER TABLE weddings ADD COLUMN slug VARCHAR(100)",
        # users table
        "ALTER TABLE users ADD COLUMN account_status VARCHAR(20) NOT NULL DEFAULT 'active'",
        "ALTER TABLE users ADD COLUMN expires_at    DATETIME",
        "ALTER TABLE users ADD COLUMN approved_at   DATETIME",
        "ALTER TABLE users ADD COLUMN approved_by   INTEGER",
        "ALTER TABLE users ADD COLUMN payment_proof TEXT",
        "ALTER TABLE users ADD COLUMN package_id    INTEGER",
        # weddings table
        "ALTER TABLE weddings ADD COLUMN groom_photo   TEXT",
        "ALTER TABLE weddings ADD COLUMN bride_photo   TEXT",
        "ALTER TABLE weddings ADD COLUMN groom_parents VARCHAR(255)",
        "ALTER TABLE weddings ADD COLUMN bride_parents VARCHAR(255)",
        "ALTER TABLE weddings ADD COLUMN wedding_city  VARCHAR(100)",
        "ALTER TABLE weddings ADD COLUMN music_url     VARCHAR(255) DEFAULT ''",
        "ALTER TABLE weddings ADD COLUMN website_title VARCHAR(255)",
        # service_packages (jika tabel lama pakai nama packages)
        "ALTER TABLE service_packages ADD COLUMN description TEXT",
    ]
    migrated = 0
    for stmt in migrations:
        try:
            c.execute(stmt)
            migrated += 1
        except Exception:
            pass   # Kolom sudah ada — lewati
    if migrated:
        conn.commit()
        print(f"  ✦ Migrasi database: {migrated} kolom baru ditambahkan.")
    # Pastikan service_packages & weddings tabel punya kolom package_id
    try:
        c.execute("ALTER TABLE weddings ADD COLUMN package_id INTEGER NOT NULL DEFAULT 1")
        conn.commit()
    except Exception:
        pass


def create_database(db_path=DB_PATH, force=False):
    if force and os.path.exists(db_path):
        os.remove(db_path)
        print("  ✦ Database lama dihapus.")
    new_db = not os.path.exists(db_path)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Jalankan DDL statement per statement (aman untuk DB lama maupun baru)
    c = conn.cursor()
    try: c.execute("PRAGMA foreign_keys = ON")
    except: pass
    try: c.execute("PRAGMA journal_mode = WAL")
    except: pass
    conn.commit()

    schema_stmts = [s.strip() for s in SCHEMA.split(';')
                    if s.strip() and any(k in s.upper() for k in
                    ('CREATE TABLE','CREATE INDEX','CREATE UNIQUE'))]
    for stmt in schema_stmts:
        try:
            c.execute(stmt)
            conn.commit()
        except Exception as e:
            if 'already exists' not in str(e).lower():
                print(f"  [WARN] DDL skip: {str(e)[:80]}")

    # Migrasi kolom baru untuk database lama
    migrate_database(conn)

    if new_db:
        print(f"  ✦ Database baru dibuat: {db_path}")
        seed(conn)
    else:
        print(f"  ✦ Database ditemukan: {db_path}")
    return conn

def start_server(conn, port=PORT):
    from http.server import HTTPServer, BaseHTTPRequestHandler
    from urllib.parse import urlparse, parse_qs
    import json as J

    class H(BaseHTTPRequestHandler):
        def log_message(self,f,*a): print(f"  [REQ] {self.command} {self.path}")
        def send_json(self,data,st=200):
            b=J.dumps(data,ensure_ascii=False,default=str).encode('utf-8')
            self.send_response(st)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin','*')
            self.send_header('Access-Control-Allow-Headers','Content-Type,X-Wedding-ID,X-Session-ID')
            self.send_header('Access-Control-Expose-Headers','Content-Length')
            self.send_header('Access-Control-Allow-Methods','GET,POST,PUT,DELETE,OPTIONS')
            self.send_header('Content-Length',str(len(b)))
            self.end_headers(); self.wfile.write(b)

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header('Access-Control-Allow-Origin','*')
            self.send_header('Access-Control-Allow-Methods','GET,POST,PUT,DELETE,OPTIONS')
            self.send_header('Access-Control-Allow-Headers','Content-Type,X-Wedding-ID,X-Session-ID')
            self.end_headers()

        def rb(self):
            l=int(self.headers.get('Content-Length',0))
            return J.loads(self.rfile.read(l)) if l else {}

        def wid(self,qs=None):
            v=self.headers.get('X-Wedding-ID')
            if not v and qs: v=(qs.get('wedding_id',[None])[0])
            return int(v) if v else None

        def sid(self): return self.headers.get('X-Session-ID',self.client_address[0])

        # ══════════════════════════════════════════════════════
        # GET
        # ══════════════════════════════════════════════════════
        def do_GET(self):
            prs=urlparse(self.path); path=prs.path.rstrip('/'); qs=parse_qs(prs.query); c=conn.cursor()

            # ── Serve static files (HTML/CSS/JS/images) ──────────────
            # Railway tidak punya Nginx — Python harus serve semua file statis
            import mimetypes as _mt
            static_ext = ('.html','.css','.js','.png','.jpg','.jpeg','.gif','.ico','.svg','.woff','.woff2','.ttf','.mp3','.ogg','.wav')
            raw_path = prs.path.split('?')[0]
            if raw_path == '/' or raw_path == '':
                raw_path = '/index.html'
            local_file = raw_path.lstrip('/')
            if any(local_file.endswith(ext) for ext in static_ext):
                if os.path.isfile(local_file):
                    mime = _mt.guess_type(local_file)[0] or 'application/octet-stream'
                    with open(local_file, 'rb') as _sf: data = _sf.read()
                    self.send_response(200)
                    self.send_header('Content-Type', mime)
                    self.send_header('Content-Length', str(len(data)))
                    self.send_header('Access-Control-Allow-Origin','*')
                    self.end_headers(); self.wfile.write(data); return
                # File not found
                self.send_response(404); self.end_headers(); return

            wid=self.wid(qs)

            # ── Serve static files (.html, .js, .css, .png, dll) ──
            import os as _os, mimetypes as _mt
            if path in ('','/'): path='/index.html'
            static_file = path.lstrip('/')
            if '.' in static_file.split('/')[-1] and not path.startswith('/api'):
                if _os.path.exists(static_file):
                    mime,_=_mt.guess_type(static_file)
                    with open(static_file,'rb') as sf: data=sf.read()
                    self.send_response(200)
                    self.send_header('Content-Type', mime or 'application/octet-stream')
                    self.send_header('Content-Length', str(len(data)))
                    self.send_header('Access-Control-Allow-Origin','*')
                    self.end_headers(); self.wfile.write(data); return

            # ── Slug route: /:slug → serve index.html ──
            # Format: /deni_anisa atau /deni-anisa
            if not path.startswith('/api') and '/' not in path.lstrip('/'):
                slug=path.lstrip('/')
                if slug and not slug.startswith('api'):
                    # Support deni_anisa dan deni&anisa
                    slug_db = slug.replace('&','_').replace('-','_') if slug else slug
                    row=c.execute("SELECT id FROM weddings WHERE (slug=? OR slug=?) AND is_active=1",(slug,slug_db)).fetchone()
                    if row:
                        if os.path.isfile('index.html'):
                            # Serve index.html dan biarkan JS handle wedding_id via slug
                            with open('index.html','rb') as f: data=f.read()
                            self.send_response(200)
                            self.send_header('Content-Type','text/html; charset=utf-8')
                            self.send_header('Access-Control-Allow-Origin','*')
                            self.send_header('Content-Length',str(len(data)))
                            self.end_headers(); self.wfile.write(data); return
                        else:
                            # Redirect ke ?wedding_id=X jika index.html tidak ada
                            self.send_response(302)
                            self.send_header('Location',f'/index.html?wedding_id={row["id"]}')
                            self.end_headers(); return

            # ── Super Admin endpoints ──
            if path=='/api/super/weddings':
                rows=c.execute("""SELECT w.*,u.name client_name,u.username client_username,
                    u.avatar_data client_avatar,p.label package_label,p.name package_name,
                    (SELECT COUNT(*) FROM rsvp r WHERE r.wedding_id=w.id) rsvp_count,
                    (SELECT COUNT(*) FROM wishes wh WHERE wh.wedding_id=w.id) wish_count
                    FROM weddings w
                    JOIN users u ON w.client_user_id=u.id
                    JOIN service_packages p ON w.package_id=p.id
                    ORDER BY w.created_at DESC""").fetchall()
                return self.send_json(rows_to_list(rows))

            if path=='/api/super/users':
                rows=c.execute("""SELECT u.*,p.label package_label,p.name package_name,
                    w.groom_name,w.bride_name,w.invite_code,w.wedding_date,w.wedding_city
                    FROM users u LEFT JOIN service_packages p ON u.package_id=p.id
                    LEFT JOIN weddings w ON w.client_user_id=u.id
                    ORDER BY u.account_status='pending' DESC, u.created_at DESC""").fetchall()
                return self.send_json(rows_to_list(rows))

            if path=='/api/super/packages':
                rows=c.execute("SELECT * FROM service_packages ORDER BY price").fetchall()
                return self.send_json(rows_to_list(rows))

            if path=='/api/super/stats':
                return self.send_json({
                    'total_weddings': c.execute("SELECT COUNT(*) FROM weddings").fetchone()[0],
                    'total_clients':  c.execute("SELECT COUNT(*) FROM users WHERE role='client'").fetchone()[0],
                    'total_rsvp':     c.execute("SELECT COUNT(*) FROM rsvp").fetchone()[0],
                    'total_wishes':   c.execute("SELECT COUNT(*) FROM wishes").fetchone()[0],
                    'basic_count':    c.execute("SELECT COUNT(*) FROM weddings WHERE package_id=1").fetchone()[0],
                    'premium_count':  c.execute("SELECT COUNT(*) FROM weddings WHERE package_id=2").fetchone()[0],
                })

            # ── Guest: lookup wedding by code ──
            if path=='/api/wedding-by-code':
                code=(qs.get('code',[None])[0] or '').upper()
                row=c.execute("SELECT wedding_id FROM invite_codes WHERE code=? AND is_active=1",(code,)).fetchone()
                if not row: return self.send_json({'error':'Kode tidak valid'},404)
                return self.send_json({'wedding_id':row['wedding_id']})

            # ── Guest: lookup wedding by slug (URL cantik) ──
            if path=='/api/wedding-by-slug':
                slug=(qs.get('slug',[None])[0] or '').lower().strip()
                if not slug: return self.send_json({'error':'Slug diperlukan'},400)
                # Support both formats: deni_anisa dan deni&anisa
                slug_db = slug.replace('&','_').replace('-','_')
                row=c.execute("SELECT id,slug,groom_name,bride_name FROM weddings WHERE (slug=? OR slug=?) AND is_active=1",(slug,slug_db)).fetchone()
                if not row: return self.send_json({'error':'Undangan tidak ditemukan'},404)
                return self.send_json({'wedding_id':row['id'],'slug':slug})

            # ── GET /api/super/slugs — list semua slug ──
            if path=='/api/super/slugs':
                rows=c.execute("SELECT id,slug,groom_name,bride_name FROM weddings WHERE slug IS NOT NULL").fetchall()
                return self.send_json(rows_to_list(rows))

            # ── Guest: public wedding info (minimal) ──
            if path=='/api/wedding/public':
                if not wid: return self.send_json({'error':'wedding_id diperlukan'},400)
                w=c.execute("SELECT id,groom_name,bride_name,groom_parents,bride_parents,groom_photo,bride_photo,wedding_date,wedding_city,website_title,features FROM weddings WHERE id=? AND is_active=1",(wid,)).fetchone()
                if not w: return self.send_json({'error':'Tidak ditemukan'},404)
                evs=c.execute("SELECT event_name,event_date,event_time_start,event_time_end,venue_name,venue_address,maps_url FROM events WHERE wedding_id=? AND is_active=1 ORDER BY event_time_start",(wid,)).fetchall()
                d=dict(w); d['events']=rows_to_list(evs)
                return self.send_json(d)

            # ── Public: check username availability (GET) ──
            if path=='/api/auth/check-username':
                uname_chk=qs.get('username',[''])[0].strip()
                if not uname_chk: return self.send_json({'taken':False,'available':True})
                taken=bool(c.execute("SELECT id FROM users WHERE username=?",(uname_chk,)).fetchone())
                return self.send_json({'taken':taken,'username':uname_chk,'available':not taken})

            if not wid: return self.send_json({'error':'wedding_id diperlukan'},400)

            # ── Client endpoints (wedding-scoped) ──
            if path=='/api/wedding':
                r=c.execute("SELECT w.*,p.name package_name,p.label package_label,p.max_gallery,p.max_rsvp FROM weddings w JOIN service_packages p ON w.package_id=p.id WHERE w.id=?",(wid,)).fetchone()
                return self.send_json(dict(r) if r else {})
            if path=='/api/stats': return self.send_json(get_stats(conn,wid))
            if path=='/api/rsvp':
                rows=c.execute("SELECT * FROM rsvp WHERE wedding_id=? ORDER BY created_at DESC",(wid,)).fetchall()
                return self.send_json(rows_to_list(rows))
            if path=='/api/wishes':
                rows=c.execute("SELECT * FROM wishes WHERE wedding_id=? AND is_approved=1 ORDER BY is_pinned DESC,created_at DESC",(wid,)).fetchall()
                return self.send_json(rows_to_list(rows))
            if path=='/api/gallery':
                sid=self.sid()
                rows=c.execute("SELECT * FROM gallery WHERE wedding_id=? AND is_active=1 ORDER BY sort_order",(wid,)).fetchall()
                result=[]
                for r in rows:
                    d=dict(r); liked=c.execute("SELECT 1 FROM photo_likes WHERE gallery_id=? AND session_id=?",(r['id'],sid)).fetchone()
                    d['liked_by_me']=bool(liked); result.append(d)
                return self.send_json(result)
            if path=='/api/events':
                rows=c.execute("SELECT * FROM events WHERE wedding_id=? AND is_active=1 ORDER BY event_time_start",(wid,)).fetchall()
                return self.send_json(rows_to_list(rows))
            if path=='/api/bank-accounts':
                rows=c.execute("SELECT * FROM bank_accounts WHERE wedding_id=? AND is_active=1 ORDER BY sort_order",(wid,)).fetchall()
                return self.send_json(rows_to_list(rows))
            if path=='/api/gift-address':
                r=c.execute("SELECT * FROM gift_address WHERE wedding_id=?",(wid,)).fetchone()
                return self.send_json(dict(r) if r else {})
            if path=='/api/love-story':
                rows=c.execute("SELECT * FROM love_story WHERE wedding_id=? AND is_active=1 ORDER BY sort_order",(wid,)).fetchall()
                return self.send_json(rows_to_list(rows))
            if path=='/api/activity':
                rows=c.execute("SELECT * FROM activity_log WHERE wedding_id=? ORDER BY created_at DESC LIMIT 100",(wid,)).fetchall()
                return self.send_json(rows_to_list(rows))
            self.send_json({'error':'Endpoint tidak ditemukan'},404)

        # ══════════════════════════════════════════════════════
        # POST
        # ══════════════════════════════════════════════════════
        def do_POST(self):
            prs=urlparse(self.path); path=prs.path.rstrip('/'); body=self.rb(); c=conn.cursor()
            wid=self.wid() or body.get('wedding_id')

            # ── Auth: Client login ──
            if path=='/api/auth/login':
                u=c.execute("SELECT * FROM users WHERE username=? AND password_hash=?",(body.get('username',''),hp(body.get('password','')))).fetchone()
                if not u: return self.send_json({'error':'Username atau password salah'},401)
                # Check active status separately for better error messages
                if not u['is_active'] and u['account_status'] not in ('pending','rejected','expired'):
                    return self.send_json({'error':'Akun tidak aktif'},403)
                c.execute("UPDATE users SET last_login=CURRENT_TIMESTAMP WHERE id=?",(u['id'],)); conn.commit()
                ud=dict(u); w=None
                # ── Cek status akun client ──
                if ud['role']=='client':
                    status=ud.get('account_status','active')
                    if status=='pending':
                        return self.send_json({'error':'Akun Anda sedang menunggu persetujuan Super Admin.'},403)
                    if status=='rejected':
                        return self.send_json({'error':'Pendaftaran Anda tidak disetujui. Hubungi Super Admin.'},403)
                    if status=='expired':
                        return self.send_json({'error':'Masa aktif akun Anda telah habis. Hubungi Super Admin.'},403)
                    # Auto-expire by date
                    if ud.get('expires_at'):
                        from datetime import datetime as dt2
                        try:
                            exp=dt2.strptime(str(ud['expires_at']),'%Y-%m-%d %H:%M:%S')
                            if dt2.now()>exp:
                                c.execute("UPDATE users SET account_status='expired',is_active=0 WHERE id=?",(ud['id'],)); conn.commit()
                                return self.send_json({'error':'Masa aktif akun Anda telah habis. Hubungi Super Admin.'},403)
                        except: pass
                if ud['role']=='client':
                    wr=c.execute("SELECT w.*,p.name package_name,p.label package_label,p.max_gallery,p.max_rsvp,p.features pkg_features FROM weddings w JOIN service_packages p ON w.package_id=p.id WHERE w.client_user_id=?",(ud['id'],)).fetchone()
                    w=dict(wr) if wr else None
                return self.send_json({'success':True,'user':{'id':ud['id'],'name':ud['name'],'username':ud['username'],'role':ud['role'],'avatar_data':ud.get('avatar_data'),'account_status':ud.get('account_status','active'),'expires_at':ud.get('expires_at'),'wedding':w}})

            # ── Auth: Guest login ──
            if path=='/api/auth/guest':
                code=str(body.get('code','')).upper()
                row=c.execute("SELECT * FROM invite_codes WHERE code=? AND is_active=1",(code,)).fetchone()
                if not row: return self.send_json({'error':'Kode undangan tidak valid'},401)
                if row['max_uses'] and row['used_count']>=row['max_uses']:
                    return self.send_json({'error':'Kode sudah habis digunakan'},401)
                c.execute("UPDATE invite_codes SET used_count=used_count+1 WHERE code=?",(code,)); conn.commit()
                return self.send_json({'success':True,'wedding_id':row['wedding_id'],'user':{'name':body.get('name',''),'role':'guest'}})

            # ── Auth: Change password ──
            if path=='/api/auth/change-password':
                uid=body.get('user_id'); old=body.get('old_password',''); new=body.get('new_password','')
                if len(new)<6: return self.send_json({'error':'Password minimal 6 karakter'},400)
                u=c.execute("SELECT id FROM users WHERE id=? AND password_hash=?",(uid,hp(old))).fetchone()
                if not u: return self.send_json({'error':'Password lama salah'},401)
                c.execute("UPDATE users SET password_hash=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(hp(new),uid)); conn.commit()
                return self.send_json({'success':True})

            # ══ PUBLIC / SUPER ENDPOINTS (tidak perlu X-Wedding-ID) ══

            # ── Public: Cek ketersediaan username ──
            if path=='/api/auth/check-username':
                from urllib.parse import parse_qs, urlparse as up2
                qs2=parse_qs(up2(self.path).query)
                uname_chk=(qs2.get('username',[None]) if hasattr(qs2,'get') else [''])[0]
                # username juga bisa dari body
                uname_chk=uname_chk or str(body.get('username','')).strip()
                if not uname_chk: return self.send_json({'taken':False})
                taken=bool(c.execute("SELECT id FROM users WHERE username=?",(uname_chk,)).fetchone())
                return self.send_json({'taken':taken,'username':uname_chk,'available':not taken})

            # ── Public: Registrasi client baru ──
            if path in ('/api/auth/register','/api/register'):
                name=str(body.get('name','')).strip()
                uname=str(body.get('username','')).strip()
                pw=str(body.get('password',''))
                if not name or not uname: return self.send_json({'error':'Nama dan username wajib diisi'},400)
                if len(pw)<6: return self.send_json({'error':'Password minimal 6 karakter'},400)
                if c.execute("SELECT id FROM users WHERE username=?",(uname,)).fetchone():
                    return self.send_json({'error':f'Username "{uname}" sudah digunakan'},409)
                email=str(body.get('email','')).strip()
                pkg_name=str(body.get('package','basic')).lower()
                pkg_row=c.execute("SELECT id FROM service_packages WHERE name=?",(pkg_name,)).fetchone()
                pkg_id=pkg_row['id'] if pkg_row else 1
                groom=str(body.get('groom_name','Nama Pria')).strip()
                bride=str(body.get('bride_name','Nama Wanita')).strip()
                g_par=str(body.get('groom_parents','')).strip()
                b_par=str(body.get('bride_parents','')).strip()
                wdate=body.get('wedding_date','2026-01-01')
                w_city=str(body.get('wedding_city','')).strip()
                w_title=str(body.get('website_title','')).strip() or f"{groom} & {bride} Wedding"
                c.execute("INSERT INTO users(name,username,email,password_hash,role,package_id,account_status,is_active) VALUES(?,?,?,?,'client',?,'pending',0)",
                    (name,uname,email,hp(pw),pkg_id))
                uid=c.lastrowid
                wcode=f"WED{uid}{uname[:4].upper()}"
                wslug = make_slug(groom, bride)
                # Pastikan slug unik
                existing = c.execute("SELECT id FROM weddings WHERE slug=?", (wslug,)).fetchone()
                if existing: wslug = f"{wslug}{uid}"
                c.execute("INSERT INTO weddings(client_user_id,package_id,groom_name,bride_name,groom_parents,bride_parents,wedding_date,wedding_city,invite_code,website_title,slug) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (uid,pkg_id,groom,bride,g_par,b_par,wdate,w_city,wcode,w_title,wslug))
                wnew=c.lastrowid
                c.executemany("INSERT INTO events(wedding_id,event_type,event_name,event_date,event_time_start,venue_name) VALUES(?,?,?,?,?,?)",[
                    (wnew,'akad','Akad Nikah',wdate,'08:00','Lokasi Akad'),
                    (wnew,'resepsi','Walimatul Ursy',wdate,'11:00','Lokasi Resepsi'),
                ])
                c.execute("INSERT INTO bank_accounts(wedding_id,bank_name,account_number,account_name,sort_order) VALUES(?,?,?,?,?)",
                    (wnew,'Bank BCA','0000000000',groom,1))
                c.execute("INSERT INTO invite_codes(wedding_id,code,label) VALUES(?,?,?)",(wnew,wcode,'Kode Umum'))
                conn.commit()
                print(f"  [DB] ✦ Registrasi: {name} (@{uname}) wid={wnew} code={wcode}")
                return self.send_json({'success':True,'id':uid,'wedding_id':wnew,'invite_code':wcode,'slug':wslug,'message':f'{name} berhasil mendaftar'})

            # ── Super Admin: tambah client ──
            if path=='/api/super/users':
                name=str(body.get('name','')).strip()
                uname=str(body.get('username','')).strip()
                pw=str(body.get('password','password123'))
                if not name or not uname: return self.send_json({'error':'Nama dan username wajib diisi'},400)
                if len(pw)<6: return self.send_json({'error':'Password minimal 6 karakter'},400)
                if c.execute("SELECT id FROM users WHERE username=?",(uname,)).fetchone():
                    return self.send_json({'error':f'Username "{uname}" sudah digunakan'},409)
                email=str(body.get('email','')).strip()
                # Support both package_id (int) and package (string name)
                pkg_id=body.get('package_id')
                if not pkg_id:
                    pkg_name=str(body.get('package','basic')).lower()
                    pkg_row=c.execute("SELECT id FROM service_packages WHERE name=?",(pkg_name,)).fetchone()
                    pkg_id=pkg_row['id'] if pkg_row else 1
                pkg_id=int(pkg_id)
                groom=str(body.get('groom_name','Nama Pria')).strip()
                bride=str(body.get('bride_name','Nama Wanita')).strip()
                g_par=str(body.get('groom_parents','')).strip()
                b_par=str(body.get('bride_parents','')).strip()
                wdate=body.get('wedding_date','2026-01-01')
                w_city=str(body.get('wedding_city','')).strip()
                w_title=str(body.get('website_title','')).strip() or f"{groom} & {bride} Wedding"
                c.execute("INSERT INTO users(name,username,email,password_hash,role,package_id,account_status,is_active) VALUES(?,?,?,?,'client',?,'pending',0)",
                    (name,uname,email,hp(pw),pkg_id))
                uid=c.lastrowid
                wcode=f"WED{uid}{uname[:4].upper()}"
                wslug = make_slug(groom, bride)
                # Pastikan slug unik
                existing = c.execute("SELECT id FROM weddings WHERE slug=?", (wslug,)).fetchone()
                if existing: wslug = f"{wslug}{uid}"
                c.execute("INSERT INTO weddings(client_user_id,package_id,groom_name,bride_name,groom_parents,bride_parents,wedding_date,wedding_city,invite_code,website_title,slug) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (uid,pkg_id,groom,bride,g_par,b_par,wdate,w_city,wcode,w_title,wslug))
                wnew=c.lastrowid
                c.executemany("INSERT INTO events(wedding_id,event_type,event_name,event_date,event_time_start,venue_name) VALUES(?,?,?,?,?,?)",[
                    (wnew,'akad','Akad Nikah',wdate,'08:00','Lokasi Akad'),
                    (wnew,'resepsi','Walimatul Ursy',wdate,'11:00','Lokasi Resepsi'),
                ])
                c.execute("INSERT INTO bank_accounts(wedding_id,bank_name,account_number,account_name,sort_order) VALUES(?,?,?,?,?)",
                    (wnew,'Bank BCA','0000000000',groom,1))
                c.execute("INSERT INTO invite_codes(wedding_id,code,label) VALUES(?,?,?)",(wnew,wcode,'Kode Umum'))
                conn.commit()
                print(f"  [DB] ✦ Client baru: {name} (@{uname}) wid={wnew} code={wcode}")
                return self.send_json({'success':True,'id':uid,'wedding_id':wnew,'invite_code':wcode,'slug':wslug,'message':f'{name} berhasil ditambahkan'})

            if not wid: return self.send_json({'error':'wedding_id diperlukan'},400)
            wid=int(wid)

            # ── RSVP submit ──
            if path=='/api/rsvp':
                name=str(body.get('guest_name','')).strip()
                if not name: return self.send_json({'error':'Nama wajib diisi'},400)
                attend=body.get('attendance','pending')
                c.execute("INSERT INTO rsvp(wedding_id,guest_name,guest_count,attendance,message) VALUES(?,?,?,?,?)",
                    (wid,name,int(body.get('guest_count',1)),attend,str(body.get('message',''))))
                rid=c.lastrowid
                if body.get('message'):
                    c.execute("INSERT INTO wishes(wedding_id,guest_name,message,rsvp_id) VALUES(?,?,?,?)",(wid,name,body['message'],rid))
                c.execute("INSERT INTO activity_log(wedding_id,action_type,description,entity_type,entity_id,actor_name) VALUES(?,?,?,?,?,?)",
                    (wid,'rsvp_submit',f"{name} mengisi RSVP — {attend}",'rsvp',rid,name))
                conn.commit(); return self.send_json({'success':True,'id':rid})

            # ── Wishes submit ──
            if path=='/api/wishes':
                name=str(body.get('guest_name','')).strip(); msg=str(body.get('message','')).strip()
                if not name or not msg: return self.send_json({'error':'Nama dan pesan wajib diisi'},400)
                c.execute("INSERT INTO wishes(wedding_id,guest_name,message) VALUES(?,?,?)",(wid,name,msg))
                wid2=c.lastrowid; conn.commit(); return self.send_json({'success':True,'id':wid2})

            # ── Gallery like ──
            if path=='/api/gallery/like':
                gid=body.get('gallery_id'); sid=self.sid()
                if not gid: return self.send_json({'error':'gallery_id diperlukan'},400)
                ex=c.execute("SELECT id FROM photo_likes WHERE gallery_id=? AND session_id=?",(gid,sid)).fetchone()
                if ex:
                    c.execute("DELETE FROM photo_likes WHERE gallery_id=? AND session_id=?",(gid,sid))
                    c.execute("UPDATE gallery SET like_count=MAX(0,like_count-1) WHERE id=?",(gid,))
                    conn.commit()
                    n=c.execute("SELECT like_count FROM gallery WHERE id=?",(gid,)).fetchone()[0]
                    return self.send_json({'success':True,'liked':False,'like_count':n})
                c.execute("INSERT INTO photo_likes(gallery_id,wedding_id,session_id,ip_address) VALUES(?,?,?,?)",(gid,wid,sid,self.client_address[0]))
                c.execute("UPDATE gallery SET like_count=like_count+1 WHERE id=?",(gid,))
                conn.commit()
                n=c.execute("SELECT like_count FROM gallery WHERE id=?",(gid,)).fetchone()[0]
                return self.send_json({'success':True,'liked':True,'like_count':n})

            # ── Gallery upload ──
            if path=='/api/gallery':
                title=str(body.get('title','Foto Baru')); file_url=body.get('file_url',''); file_data=body.get('file_data','')
                if not file_url and not file_data: return self.send_json({'error':'URL atau data foto diperlukan'},400)
                mo=c.execute("SELECT COALESCE(MAX(sort_order),0) FROM gallery WHERE wedding_id=?",(wid,)).fetchone()[0]
                c.execute("INSERT INTO gallery(wedding_id,title,file_url,file_data,file_name,file_type,sort_order) VALUES(?,?,?,?,?,?,?)",
                    (wid,title,file_url,file_data,body.get('file_name',title),body.get('file_type','image/jpeg'),mo+1))
                gid=c.lastrowid; conn.commit()
                return self.send_json({'success':True,'id':gid})

            # ── Love Story tambah ──
            if path=='/api/love-story':
                year=body.get('year',0); title=str(body.get('title','')).strip()
                if not year or not title: return self.send_json({'error':'Tahun dan judul wajib diisi'},400)
                mo=c.execute("SELECT COALESCE(MAX(sort_order),0) FROM love_story WHERE wedding_id=?",(wid,)).fetchone()[0]
                c.execute("INSERT INTO love_story(wedding_id,year,month,title,description,sort_order) VALUES(?,?,?,?,?,?)",
                    (wid,int(year),body.get('month',''),title,str(body.get('description','')),mo+1))
                lid=c.lastrowid; conn.commit()
                return self.send_json({'success':True,'id':lid})

            # ── Bank account tambah ──
            if path=='/api/bank-accounts':
                name=str(body.get('bank_name','')).strip()
                num=str(body.get('account_number','')).strip()
                owner=str(body.get('account_name','')).strip()
                if not name or not num or not owner: return self.send_json({'error':'Data bank tidak lengkap'},400)
                mo=c.execute("SELECT COALESCE(MAX(sort_order),0) FROM bank_accounts WHERE wedding_id=?",(wid,)).fetchone()[0]
                c.execute("INSERT INTO bank_accounts(wedding_id,bank_name,account_number,account_name,phone_number,sort_order) VALUES(?,?,?,?,?,?)",
                    (wid,name,num,owner,body.get('phone_number',''),mo+1))
                bid=c.lastrowid; conn.commit()
                return self.send_json({'success':True,'id':bid})

            self.send_json({'error':'Endpoint tidak ditemukan'},404)

        # ══════════════════════════════════════════════════════
        # PUT
        # ══════════════════════════════════════════════════════
        def do_PUT(self):
            prs=urlparse(self.path); parts=prs.path.strip('/').split('/'); body=self.rb(); c=conn.cursor()
            wid_h=self.wid() or body.get('wedding_id')

            if parts==['api','wedding']:
                if not wid_h: return self.send_json({'error':'wedding_id diperlukan'},400)
                wid_h=int(wid_h)
                allowed=['groom_name','bride_name','groom_parents','bride_parents','wedding_date',
                         'wedding_city','invite_code','music_url','website_title','features',
                         'groom_photo','bride_photo','slug']
                sets=[f"{k}=?" for k in body if k in allowed]; vals=[body[k] for k in body if k in allowed]
                if not sets: return self.send_json({'error':'Tidak ada field valid'},400)
                c.execute(f"UPDATE weddings SET {','.join(sets)},updated_at=CURRENT_TIMESTAMP WHERE id=?",vals+[wid_h])
                if 'invite_code' in body:
                    old=c.execute("SELECT code FROM invite_codes WHERE wedding_id=? LIMIT 1",(wid_h,)).fetchone()
                    if old: c.execute("UPDATE invite_codes SET code=? WHERE wedding_id=?",(body['invite_code'],wid_h))
                    else: c.execute("INSERT INTO invite_codes(wedding_id,code,label) VALUES(?,?,?)",(wid_h,body['invite_code'],'Kode Umum'))
                conn.commit()
                return self.send_json({'success':True,'updated':list(body.keys())})

            if len(parts)==3 and parts[1]=='events':
                try: eid=int(parts[2])
                except: return self.send_json({'error':'ID tidak valid'},400)
                allowed=['event_date','event_time_start','event_time_end','event_name','venue_name','venue_address','venue_city','maps_url']
                sets=[f"{k}=?" for k in body if k in allowed]; vals=[body[k] for k in body if k in allowed]
                if sets: c.execute(f"UPDATE events SET {','.join(sets)},updated_at=CURRENT_TIMESTAMP WHERE id=?",vals+[eid])
                conn.commit(); return self.send_json({'success':True})

            if len(parts)==3 and parts[1]=='love-story':
                try: lid=int(parts[2])
                except: return self.send_json({'error':'ID tidak valid'},400)
                allowed=['year','month','title','description','sort_order']
                sets=[f"{k}=?" for k in body if k in allowed]; vals=[body[k] for k in body if k in allowed]
                if sets: c.execute(f"UPDATE love_story SET {','.join(sets)} WHERE id=?",vals+[lid])
                conn.commit(); return self.send_json({'success':True})

            if len(parts)==3 and parts[1]=='bank-accounts':
                try: bid=int(parts[2])
                except: return self.send_json({'error':'ID tidak valid'},400)
                c.execute("UPDATE bank_accounts SET bank_name=?,account_number=?,account_name=?,phone_number=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                    (body.get('bank_name'),body.get('account_number'),body.get('account_name'),body.get('phone_number'),bid))
                conn.commit(); return self.send_json({'success':True})

            if len(parts)==3 and parts[1]=='gallery':
                try: gid=int(parts[2])
                except: return self.send_json({'error':'ID tidak valid'},400)
                allowed=['title','description','sort_order','is_featured','is_active']
                sets=[f"{k}=?" for k in body if k in allowed]; vals=[body[k] for k in body if k in allowed]
                if sets: c.execute(f"UPDATE gallery SET {','.join(sets)} WHERE id=?",vals+[gid])
                conn.commit(); return self.send_json({'success':True})

            if parts==['api','gift-address']:
                if not wid_h: return self.send_json({'error':'wedding_id diperlukan'},400)
                wid_h=int(wid_h)
                ex=c.execute("SELECT id FROM gift_address WHERE wedding_id=?",(wid_h,)).fetchone()
                if ex:
                    c.execute("UPDATE gift_address SET recipient_name=?,street_address=?,city=?,province=?,postal_code=?,phone=?,notes=?,updated_at=CURRENT_TIMESTAMP WHERE wedding_id=?",
                        (body.get('recipient_name',''),body.get('street_address',''),body.get('city',''),
                         body.get('province',''),body.get('postal_code',''),body.get('phone',''),body.get('notes',''),wid_h))
                else:
                    c.execute("INSERT INTO gift_address(wedding_id,recipient_name,street_address,city,province,postal_code,phone,notes) VALUES(?,?,?,?,?,?,?,?)",
                        (wid_h,body.get('recipient_name',''),body.get('street_address',''),body.get('city',''),
                         body.get('province',''),body.get('postal_code',''),body.get('phone',''),body.get('notes','')))
                conn.commit(); return self.send_json({'success':True})

            if parts==['api','profile']:
                uid=body.get('user_id')
                if not uid: return self.send_json({'error':'user_id diperlukan'},400)
                if body.get('name'): c.execute("UPDATE users SET name=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(body['name'],uid))
                if 'avatar_data' in body: c.execute("UPDATE users SET avatar_data=? WHERE id=?",(body['avatar_data'],uid))
                conn.commit(); return self.send_json({'success':True})

            if len(parts)==4 and parts[1]=='super' and parts[2]=='users':
                try: uid=int(parts[3])
                except: return self.send_json({'error':'ID tidak valid'},400)
                action=body.get('action','')
                if action=='approve':
                    from datetime import datetime as dt, timedelta as td
                    expires=dt.now()+td(days=60)
                    exp_str=expires.strftime('%Y-%m-%d %H:%M:%S')
                    c.execute("UPDATE users SET account_status='active',is_active=1,approved_at=CURRENT_TIMESTAMP,expires_at=? WHERE id=?",(exp_str,uid))
                    conn.commit()
                    u2=c.execute("SELECT name,username FROM users WHERE id=?",(uid,)).fetchone()
                    print(f"  [DB] ✦ Client APPROVED: {u2['name']} (@{u2['username']}) expires={exp_str}")
                    return self.send_json({'success':True,'expires_at':exp_str,'message':'Client berhasil disetujui. Akun aktif 60 hari.'})
                elif action=='reject':
                    c.execute("UPDATE users SET account_status='rejected',is_active=0 WHERE id=?",(uid,))
                    conn.commit()
                    return self.send_json({'success':True,'message':'Pendaftaran ditolak.'})
                elif action=='extend':
                    from datetime import datetime as dt, timedelta as td
                    # Extend 60 hari dari sekarang atau dari expires_at
                    row=c.execute("SELECT expires_at FROM users WHERE id=?",(uid,)).fetchone()
                    try: base=dt.strptime(str(row['expires_at']),'%Y-%m-%d %H:%M:%S')
                    except: base=dt.now()
                    if base<dt.now(): base=dt.now()
                    expires=base+td(days=60)
                    exp_str=expires.strftime('%Y-%m-%d %H:%M:%S')
                    c.execute("UPDATE users SET expires_at=?,account_status='active',is_active=1 WHERE id=?",(exp_str,uid))
                    conn.commit()
                    return self.send_json({'success':True,'expires_at':exp_str,'message':'Akun diperpanjang 60 hari.'})
                else:
                    allowed=['name','email','is_active','package_id','account_status','payment_proof']
                    sets=[f"{k}=?" for k in body if k in allowed]; vals=[body[k] for k in body if k in allowed]
                    if sets: c.execute(f"UPDATE users SET {','.join(sets)},updated_at=CURRENT_TIMESTAMP WHERE id=?",vals+[uid])
                    if 'package_id' in body:
                        c.execute("UPDATE weddings SET package_id=? WHERE client_user_id=?",(body['package_id'],uid))
                    conn.commit(); return self.send_json({'success':True})

            if len(parts)==4 and parts[1]=='super' and parts[2]=='packages':
                try: pid=int(parts[3])
                except: return self.send_json({'error':'ID tidak valid'},400)
                allowed=['label','description','max_gallery','max_rsvp','features','price','is_active']
                sets=[f"{k}=?" for k in body if k in allowed]; vals=[body[k] for k in body if k in allowed]
                if sets: c.execute(f"UPDATE service_packages SET {','.join(sets)} WHERE id=?",vals+[pid])
                conn.commit(); return self.send_json({'success':True})

            self.send_json({'error':'Endpoint tidak ditemukan'},404)

        # ══════════════════════════════════════════════════════
        # DELETE
        # ══════════════════════════════════════════════════════
        def do_DELETE(self):
            prs=urlparse(self.path); parts=prs.path.strip('/').split('/'); c=conn.cursor()
            if len(parts)==3:
                res=parts[1]
                try: rid=int(parts[2])
                except: return self.send_json({'error':'ID tidak valid'},400)
                tbl={'rsvp':'rsvp','wishes':'wishes','gallery':'gallery',
                     'events':'events','bank-accounts':'bank_accounts',
                     'love-story':'love_story'}
                if res in tbl:
                    c.execute(f"DELETE FROM {tbl[res]} WHERE id=?",(rid,)); conn.commit()
                    return self.send_json({'success':True,'deleted_id':rid})

            if len(parts)==4 and parts[1]=='super' and parts[2]=='users':
                try: uid=int(parts[3])
                except: return self.send_json({'error':'ID tidak valid'},400)
                u=c.execute("SELECT role FROM users WHERE id=?",(uid,)).fetchone()
                if u and u['role']=='super_admin': return self.send_json({'error':'Tidak bisa hapus Super Admin'},403)
                c.execute("DELETE FROM users WHERE id=?",(uid,)); conn.commit()
                return self.send_json({'success':True,'deleted_id':uid})

            if len(parts)==4 and parts[1]=='super' and parts[2]=='weddings':
                try: wid=int(parts[3])
                except: return self.send_json({'error':'ID tidak valid'},400)
                c.execute("DELETE FROM weddings WHERE id=?",(wid,)); conn.commit()
                return self.send_json({'success':True,'deleted_id':wid})

            self.send_json({'error':'Endpoint tidak ditemukan'},404)

    print(f"\n{'━'*58}")
    railway_url = os.environ.get("RAILWAY_PUBLIC_DOMAIN", f"localhost:{port}")
    print(f"  ✦  Wedding Platform API  ·  https://{railway_url}")
    print(f"{'━'*58}")
    print(f"  Super Admin  : superadmin / super2026")
    print(f"  Client 1     : deni  / deni2026     (Deni & Anisa — Premium)")
    print(f"  Client 2     : bagas / bagas2026    (Bagas & Anisa — Basic)")
    print(f"  Kode tamu 1  : WED2026")
    print(f"  Kode tamu 2  : WED2026B")
    print(f"  Tekan Ctrl+C untuk menghentikan")
    print(f"{'━'*58}\n")
    server=HTTPServer(('0.0.0.0',port),H)
    try: server.serve_forever()
    except KeyboardInterrupt: print("\n  ✦ Server dihentikan.")

if __name__=='__main__':
    force='--reset' in sys.argv
    # Support DB_PATH dari environment (untuk Railway persistent storage)
    db_path = os.environ.get('DB_PATH', DB_PATH)
    conn=create_database(db_path,force=force)
    c=conn.cursor()
    print(f"\n  {'─'*55}")
    for w in c.execute("""SELECT w.id,w.groom_name,w.bride_name,w.invite_code,u.username,p.name package
        FROM weddings w JOIN users u ON w.client_user_id=u.id JOIN service_packages p ON w.package_id=p.id""").fetchall():
        s=get_stats(conn,w['id'])
        print(f"  [{w['id']}] {(w['groom_name']+' & '+w['bride_name'])[:28]:30} @{w['username']:10} [{w['package']:7}] {w['invite_code']}  rsvp:{s['total_rsvp']}")
    print(f"  {'─'*55}\n")
    # Support PORT dari environment (Railway set ini otomatis)
    if '--serve' in sys.argv or os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('PORT'):
        port = int(os.environ.get('PORT', 8000))
        start_server(conn, port=port)
