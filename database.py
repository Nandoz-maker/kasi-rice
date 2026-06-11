import sqlite3
import uuid
from datetime import datetime
from werkzeug.security import generate_password_hash

DB_PATH = 'business_cms.db'


def get_db_connection():
    conn = sqlite3.connect(
        DB_PATH,
        timeout=30,
        check_same_thread=False,
        isolation_level=None
    )

    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA temp_store = MEMORY")

    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # ==========================================
    # 1. USERS TABLE
    # ==========================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'customer',
            created_at TEXT NOT NULL
        )
    ''')

    # ==========================================
    # 2. CUSTOMERS TABLE
    # ==========================================
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS customers (
        customer_id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,

        -- BASIC PROFILE
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        profile_image TEXT,

        -- ADDRESS SYSTEM
        shipping_address TEXT,
        city TEXT,
        district TEXT,
        country TEXT DEFAULT 'Uganda',
        postal_code TEXT,

        -- ACCOUNT CONTROL
        account_status TEXT DEFAULT 'Active', 
        email_verified INTEGER DEFAULT 0,
        phone_verified INTEGER DEFAULT 0,

        -- ACTIVITY TRACKING
        last_login TEXT,
        updated_at TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,

        -- SECURITY
        password_changed_at TEXT,
        two_fa_enabled INTEGER DEFAULT 0,

        FOREIGN KEY (user_id)
            REFERENCES users (user_id)
            ON DELETE CASCADE
    )
    ''')

    # ==========================================
    # 3. WEB SETTINGS TABLE (EXPANDED FOR KASI RICE)
    # ==========================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS web_settings (
            settings_id TEXT PRIMARY KEY CHECK (settings_id = 'SYSTEM_CONF'),

            site_name TEXT DEFAULT 'Kasi Rice',

            -- Dynamic Branding System
            primary_color TEXT DEFAULT '#16a34a',   -- Farm Organic Green
            secondary_color TEXT DEFAULT '#ea580c', -- Harvest Orange

            phone_contact TEXT DEFAULT '+256 700 000000',
            email_contact TEXT DEFAULT 'info@kasirice.com',

            announcement_text TEXT DEFAULT 'Welcome to Kasi Rice! Premium organic grains direct from our gardens to your table.',
            show_announcement INTEGER DEFAULT 1,

            -- About Copy Integration Elements
            about_title TEXT DEFAULT 'Kasi Rice — From Our Gardens to Your Table',
            about_subtitle TEXT DEFAULT 'Cultivating premium, organic grains with care, milling to perfection, and delivering directly to your kitchen.',
            about_vision TEXT DEFAULT 'To be East Africa''s most dependable name in local rice production, transforming agricultural standards by serving whole, farm-fresh grains directly from sustainable local gardens to global households.',
            about_mission TEXT DEFAULT 'To eliminate complex, expensive supply chains by growing premium rice locally, implementing high-standard clean sorting and precision milling, and delivering affordable, wholesome food options directly to retail and wholesale buyers.',
            about_motto TEXT DEFAULT 'Naturally Grown. Expertly Cleaned. Exceptionally Plentiful.',
            about_description TEXT DEFAULT 'At Kasi Rice, we don''t just trade agricultural commodities—we own the process from the ground up. By planting, cultivating, and nurturing our own crops in our personal farm gardens, we monitor the biological integrity of every seed. This end-to-end farm ownership allows us to guarantee premium grade whole grains, stunning natural aroma, and top-tier milling yields that external brokers simply cannot match.',

            -- Statistical Counter Benchmarks
            stats_employees INTEGER DEFAULT 35,
            stats_capacity INTEGER DEFAULT 2500,
            stats_years INTEGER DEFAULT 4,

            updated_at TEXT NOT NULL
        )
    ''')

    # ==========================================
    # 4. PRODUCTS TABLE
    # ==========================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            sku TEXT UNIQUE,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            stock_quantity INTEGER DEFAULT 0,
            low_stock_alert INTEGER DEFAULT 5,

            image_filename TEXT,
            whatsapp_order_text TEXT,
            is_active INTEGER DEFAULT 1,
            category TEXT,
            updated_at TEXT NOT NULL
        )
    ''')

    # ==========================================
    # 5. PRODUCT IMAGES TABLE
    # ==========================================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS product_images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id TEXT NOT NULL,
        image TEXT NOT NULL,
        is_primary INTEGER DEFAULT 0,
        sort_order INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(product_id)
            REFERENCES products(product_id)
            ON DELETE CASCADE
    )
    """)

    # ==========================================
    # 6. TEAM MEMBERS TABLE (NEW Multi-Row Support)
    # ==========================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS team_members (
            member_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            role TEXT NOT NULL,
            image TEXT DEFAULT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ==========================================
    # 7. HERO SLIDES TABLE
    # ==========================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS hero_slides (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slide_id TEXT,
            title TEXT NOT NULL,
            subtitle TEXT,
            image_path TEXT,
            badge_text TEXT,

            button_text TEXT DEFAULT 'Explore Now',
            button_link TEXT DEFAULT '#',

            background_image TEXT NOT NULL,

            overlay_color TEXT DEFAULT 'rgba(0,0,0,0.4)',

            position INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1
        )
    ''')

    # ==========================================
    # 8. CUSTOMER MESSAGES (Aligned to Forms)
    # ==========================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customer_messages (
            message_id TEXT PRIMARY KEY,
            sender_name TEXT NOT NULL,
            sender_email TEXT NOT NULL,
            sender_phone TEXT,
            message_body TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    ''')

    # ==========================================
    # 9. ORDERS TABLE (HEADER)
    # ==========================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            total_amount REAL DEFAULT 0,
            order_status TEXT DEFAULT 'Pending',
            payment_method TEXT DEFAULT 'cash_on_delivery',
            payment_status TEXT DEFAULT 'Unpaid',
            transaction_reference TEXT,
            created_at TEXT NOT NULL,

            FOREIGN KEY (customer_id)
                REFERENCES customers (customer_id)
                ON DELETE RESTRICT
        )
    ''')

    # ==========================================
    # 10. ORDER ITEMS TABLE (DETAILS)
    # ==========================================
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS order_items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id TEXT NOT NULL,
        product_id TEXT NOT NULL,
        product_name TEXT NOT NULL,
        product_price REAL NOT NULL,
        unit_price REAL NOT NULL,
        quantity INTEGER NOT NULL,
        total_price REAL NOT NULL,
        created_at TEXT NOT NULL,

        FOREIGN KEY (order_id)
            REFERENCES orders (order_id)
            ON DELETE CASCADE,
        FOREIGN KEY (product_id)
            REFERENCES products (product_id)
            ON DELETE RESTRICT
    )
    ''')

    # ==========================================
    # 11. CART ITEMS TABLE
    # ==========================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cart_items (
            cart_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id TEXT NOT NULL,
            product_id TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,

            FOREIGN KEY (customer_id)
                REFERENCES customers (customer_id)
                ON DELETE CASCADE,
            FOREIGN KEY (product_id)
                REFERENCES products (product_id)
                ON DELETE CASCADE
        )
    ''')

    # ==========================================
    # 12. PAYMENTS TABLE
    # ==========================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            payment_id TEXT PRIMARY KEY,
            order_id TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_method TEXT,
            payment_status TEXT DEFAULT 'Pending',
            transaction_ref TEXT,
            created_at TEXT NOT NULL,

            FOREIGN KEY (order_id)
                REFERENCES orders (order_id)
                ON DELETE CASCADE
        )
    ''')

    # ==========================================
    # 13. SYNC QUEUE TABLE
    # ==========================================
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sync_queue (
            sync_id TEXT PRIMARY KEY,
            target_table TEXT NOT NULL,
            action_type TEXT NOT NULL,
            row_primary_key TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_synced INTEGER DEFAULT 0
        )
    ''')

    # ==========================================
    # INDEXES (PERFORMANCE)
    # ==========================================
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cart_customer ON cart_items(customer_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_cart_product ON cart_items(product_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sync_queue_status ON sync_queue(is_synced)')

    # ==========================================
    # DEFAULT SEED DATA INJECTION
    # ==========================================
    timestamp_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Core Global Configurations Seed
    settings_exist = cursor.execute("SELECT 1 FROM web_settings WHERE settings_id = 'SYSTEM_CONF'").fetchone()
    if not settings_exist:
        cursor.execute('''
            INSERT INTO web_settings (settings_id, site_name, primary_color, secondary_color, updated_at)
            VALUES ('SYSTEM_CONF', 'Kasi Rice', '#16a34a', '#ea580c', ?)
        ''', (timestamp_now,))

    # Administration Profiling Seed
    admin_exists = cursor.execute("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1").fetchone()
    if not admin_exists:
        print("[*] Creating default admin account...")
        user_id = f"USR-{uuid.uuid4().hex[:12].upper()}"
        password_hash = generate_password_hash("admin123")

        cursor.execute('''
            INSERT INTO users (user_id, username, password_hash, role, created_at)
            VALUES (?, 'admin', ?, 'admin', ?)
        ''', (user_id, password_hash, timestamp_now))
        print("[+] Default admin created. Username: admin | Password: admin123")
    else:
        print("[*] Admin already exists. Skipping seed.")

    conn.commit()
    conn.close()
    print("[✓] Database initialization complete.")

if __name__ == '__main__':
    init_db()