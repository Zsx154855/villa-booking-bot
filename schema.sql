-- =====================================================
-- Taimili Villa Booking System - Database Schema
-- SQLite Database for Production Deployment
-- =====================================================

-- 别墅表
CREATE TABLE IF NOT EXISTS villas (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    region TEXT NOT NULL,
    room_type TEXT,
    price_per_night REAL NOT NULL,
    bedrooms INTEGER DEFAULT 0,
    bathrooms INTEGER DEFAULT 0,
    max_guests INTEGER DEFAULT 0,
    amenities TEXT,  -- JSON array stored as text
    images TEXT,     -- JSON array stored as text
    description TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 预订表
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    booking_id TEXT UNIQUE NOT NULL,
    user_id TEXT NOT NULL,
    villa_id TEXT NOT NULL,
    villa_name TEXT,
    villa_region TEXT,
    checkin TEXT NOT NULL,
    checkout TEXT NOT NULL,
    guests INTEGER DEFAULT 1,
    contact_name TEXT,
    contact_phone TEXT,
    contact_note TEXT,
    price_per_night REAL DEFAULT 0,
    total_price REAL DEFAULT 0,
    status TEXT DEFAULT 'pending',  -- pending/confirmed/cancelled/completed
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (villa_id) REFERENCES villas(id)
);

-- 用户表（可选，用于用户偏好管理）
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id TEXT UNIQUE NOT NULL,
    username TEXT,
    preferred_language TEXT DEFAULT 'zh',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    last_seen TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 索引：提升查询性能
CREATE INDEX IF NOT EXISTS idx_villas_region ON villas(region);
CREATE INDEX IF NOT EXISTS idx_villas_active ON villas(is_active);
CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id);
CREATE INDEX IF NOT EXISTS idx_bookings_villa ON bookings(villa_id);
CREATE INDEX IF NOT EXISTS idx_bookings_dates ON bookings(checkin, checkout);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);

-- 视图：活跃预订统计
CREATE VIEW IF NOT EXISTS v_active_bookings AS
SELECT b.*, v.name as villa_name, v.region as villa_region
FROM bookings b
LEFT JOIN villas v ON b.villa_id = v.id
WHERE b.status IN ('pending', 'confirmed');

-- 视图：别墅预订统计
CREATE VIEW IF NOT EXISTS v_villa_stats AS
SELECT 
    v.id,
    v.name,
    v.region,
    COUNT(b.id) as total_bookings,
    SUM(CASE WHEN b.status = 'completed' THEN 1 ELSE 0 END) as completed_bookings
FROM villas v
LEFT JOIN bookings b ON v.id = b.villa_id
GROUP BY v.id;
