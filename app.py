from flask import Flask, render_template, request, send_file, current_app, redirect, url_for, session, flash, jsonify
import os
import uuid
import sqlite3
import threading
import time
import subprocess
import platform
from datetime import datetime
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from utils.invoice import generate_invoice
import logging
import json 
from datetime import datetime
import webbrowser

# Import our custom configuration and data layers
from config import get_current_config
from database import init_db, get_db_connection

app = Flask(__name__)

###################################################-----copde for my backend terminal

# 1. Setup instant-flushing log file handler
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', '%H:%M:%S')
file_handler = logging.FileHandler('server.log', mode='w', delay=False)
file_handler.setFormatter(log_formatter)

# Apply handler to Flask and the server engine
app.logger.setLevel(logging.INFO)
app.logger.addHandler(file_handler)

werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.setLevel(logging.INFO)
werkzeug_logger.addHandler(file_handler)

###################################################---end code


# Load the dynamic configuration class based on the APP_ENV variable
active_config = get_current_config()
app.config.from_object(active_config)

print(f"[*] System Boot Sequences Initialized in [{app.config['ENV_MODE']}] Mode.")

# Ensure that the SQLite database file and tables are initialized perfectly
init_db()


# ==========================================
# AUTOMATED BROWSER LAUNCH ENGINE
# ==========================================
def launch_local_browser_window(url):
    """
    Silently waits for the Flask server local framework instance to wake up, 
    then initiates an automated browser frame natively on your system desktop screen.
    """
    # Small temporal delay block allowing the socket layer ports to clear and open cleanly
    time.sleep(1.5)
    
    system_os = platform.system().lower()
    
    # Chrome and Edge application window size modifiers
    window_settings = "--window-size=1280,800"
    window_position = "--window-position=0,0"
    
    if system_os == "windows":
        # Standard default local asset installations installation paths for Windows
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        chrome_path_x86 = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        edge_path = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        
        if os.path.exists(chrome_path):
            subprocess.Popen([chrome_path, window_settings, window_position, f"--app={url}"])
        elif os.path.exists(chrome_path_x86):
            subprocess.Popen([chrome_path_x86, window_settings, window_position, f"--app={url}"])
        elif os.path.exists(edge_path):
            subprocess.Popen([edge_path, window_settings, window_position, f"--app={url}"])
        else:
            # Universal fallback option if specialized local directory strings are altered
            import webbrowser
            webbrowser.open(url)
            
    elif system_os == "darwin":  # macOS support rules
        chrome_mac = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if os.path.exists(chrome_mac):
            subprocess.Popen([chrome_mac, window_settings, window_position, f"--app={url}"])
        else:
            import webbrowser
            webbrowser.open(url)
    else:
        # Linux deployment platforms fallback engine
        import webbrowser
        webbrowser.open(url)

# ==========================================
# GLOBAL CONTEXT PROCESSORS
# ==========================================
@app.context_processor
def inject_global_settings():

    conn = None

    try:

        conn = get_db_connection()

        settings_row = conn.execute(
            'SELECT * FROM web_settings LIMIT 1'
        ).fetchone()

        if settings_row:
            return {'site_config': dict(settings_row)}

    except Exception as e:

        print(f"[-] Global Context Processor Warning: {e}")

    finally:

        if conn:
            conn.close()

    # FALLBACK ALWAYS
    return {
        'site_config': {
            'site_name': 'TECH HUB',
            'primary_color': "#62a3f7",
            'secondary_color': "#2e1c10",
            'announcement_text': 'Contact Us for Asistence/Web Configerations',
            'show_announcement': 0,
            'phone_contact': '+256 754 050 790',
            'email_contact': 'humnt2020@gmail.com'
        }
    }

@app.context_processor
def inject_admin_notification_counters():
    """
    Globally injects unread messages and pending orders counters.
    """

    counters = {
        'unread_messages_count': 0,
        'pending_orders_count': 0
    }

    conn = None

    try:

        if 'user_id' in session and session.get('role') == 'admin':

            conn = get_db_connection()
            cursor = conn.cursor()

            unread_row = cursor.execute(
                """
                SELECT COUNT(*)
                FROM customer_messages
                WHERE is_read = 0
                   OR is_read = '0'
                   OR is_read IS NULL
                """
            ).fetchone()

            if unread_row:
                counters['unread_messages_count'] = unread_row[0]

            pending_row = cursor.execute(
                """
                SELECT COUNT(*)
                FROM orders
                WHERE LOWER(order_status) = 'pending'
                """
            ).fetchone()

            if pending_row:
                counters['pending_orders_count'] = pending_row[0]

    except Exception as e:

        print(f"[-] Sidebar counter compilation fault: {e}")

    finally:

        if conn:
            conn.close()

    # IMPORTANT:
    return counters

@app.context_processor
def inject_cart_count():
    conn = None
    try:
        # 1. If user is a logged-in client, aggregate from SQLite DB
        if 'customer_id' in session:
            conn = get_db_connection()
            result = conn.execute('''
                SELECT COALESCE(SUM(quantity), 0) AS total
                FROM cart_items
                WHERE customer_id = ?
            ''', (session['customer_id'],)).fetchone()
            return {'cart_count': result['total'] if result and result['total'] else 0}
        
        # 2. If user is a guest, sum memory array keys out of cookie state
        elif 'guest_cart' in session and isinstance(session['guest_cart'], dict):
            guest_total = sum(int(qty) for qty in session['guest_cart'].values())
            return {'cart_count': guest_total}
            
        return {'cart_count': 0}
    except Exception as e:
        print(f"Cart count context processor exception: {e}")
        return {'cart_count': 0}
    finally:
        if conn:
            conn.close()
            
# ==========================================
# PUBLIC FRONT-FACING WEBSITE ROUTES
# ==========================================
@app.route('/')
def index():
    """Renders the public customer homepage showcasing active sliders, alerts, and products."""
    try:
        conn = get_db_connection()
        # Fetch active products to display on the digital store front
        products = conn.execute('SELECT * FROM products WHERE is_active = 1 ORDER BY name ASC').fetchall()
        hero_slides = conn.execute('SELECT * FROM hero_slides WHERE is_active = 1 ORDER BY position ASC').fetchall()
        
        conn.close()
        return render_template('index.html', products=products, hero_slides=hero_slides)
    except Exception as e:
        print(f"[-] Error loading homepage: {e}")
        return render_template('index.html', products=[])

@app.route('/products')
def products_page():
    """Renders the dedicated marketplace catalog page for home-produced goods."""
    try:
        conn = get_db_connection()
        products = conn.execute('SELECT * FROM products WHERE is_active = 1 ORDER BY name ASC').fetchall()
        conn.close()
        return render_template('products.html', products=products)
    except Exception as e:
        print(f"[-] Error loading products page: {e}")
        return render_template('products.html', products=[])

@app.route('/contact', methods=['GET', 'POST'])
def contact_page():
    """Handles consumer inquiry message submissions via the public web layout."""
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        body = request.form.get('message', '').strip()

        if not name or not email or not body:
            flash("Please complete all required fields.", "error")
            return redirect(url_for('contact_page'))

        try:
            message_id = f"MSG-{uuid.uuid4().hex[:12].upper()}"
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            conn = get_db_connection()
            conn.execute('''
                INSERT INTO customer_messages (message_id, sender_name, sender_email, sender_phone, message_body, is_read, created_at)
                VALUES (?, ?, ?, ?, ?, 0, ?)
            ''', (message_id, name, email, phone, body, created_at))
            
            # If the application is operating locally, append the action packet to our synchronization pipeline
            if app.config['ENV_MODE'] == 'OFFLINE':
                sync_id = f"SYNC-{uuid.uuid4().hex[:12].upper()}"
                payload = f'{{"message_id": "{message_id}", "sender_name": "{name}", "sender_email": "{email}", "sender_phone": "{phone}", "message_body": "{body}", "is_read": 0, "created_at": "{created_at}"}}'
                conn.execute('''
                    INSERT INTO sync_queue (sync_id, target_table, action_type, row_primary_key, payload_json, created_at, is_synced)
                    VALUES (?, 'customer_messages', 'INSERT', ?, ?, ?, 0)
                ''', (sync_id, message_id, payload, created_at))

            conn.commit()
            conn.close()
            flash("Your message has been sent successfully!", "success")
            return redirect(url_for('contact_page'))
        except Exception as e:
            flash(f"An unexpected storage error occurred: {str(e)}", "error")
            return redirect(url_for('contact_page'))

    return render_template('contact.html')

# ==========================================
# CUSTOMER AUTHENTICATION & PORTAL ROUTES
# ==========================================

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    """Handles new user self-registration with automatic secure profile mapping."""
    if 'user_id' in session:
        return redirect(url_for('user_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('shipping_address', '').strip()

        if not username or not password or not full_name or not email:
            flash("All mandatory registration fields must be completed.", "error")
            return redirect(url_for('signup'))

        try:
            conn = get_db_connection()
            # Verify if user registry details already conflict
            existing_user = conn.execute('SELECT 1 FROM users WHERE username = ? COLLATE NOCASE', (username,)).fetchone()
            existing_email = conn.execute('SELECT 1 FROM customers WHERE email = ? COLLATE NOCASE', (email,)).fetchone()

            if existing_user:
                flash("That username is already taken. Please try another.", "error")
                conn.close()
                return redirect(url_for('signup'))
            if existing_email:
                flash("An account with that email address already exists.", "error")
                conn.close()
                return redirect(url_for('signup'))

            # Generate IDs and encrypt passwords using industry standard cryptographic hashes
            user_id = f"USR-{uuid.uuid4().hex[:12].upper()}"
            customer_id = f"CST-{uuid.uuid4().hex[:12].upper()}"
            pwd_hash = generate_password_hash(password)
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 1. Write to underlying authentication user matrix
            conn.execute('''
                INSERT INTO users (user_id, username, password_hash, role, created_at)
                VALUES (?, ?, ?, 'customer', ?)
            ''', (user_id, username, pwd_hash, created_at))

            # 2. Write to corresponding meta customer profile schema
            conn.execute('''
                INSERT INTO customers (customer_id, user_id, full_name, email, phone, shipping_address, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (customer_id, user_id, full_name, email, phone, address, created_at))

            # SECURED: Offline Sync Architecture Payload Strategy via json.dumps
            if app.config.get('ENV_MODE') == 'OFFLINE':
                sync_id_u = f"SYNC-{uuid.uuid4().hex[:12].upper()}"
                sync_id_c = f"SYNC-{uuid.uuid4().hex[:12].upper()}"
                
                user_payload_dict = {
                    "user_id": user_id, 
                    "username": username, 
                    "password_hash": pwd_hash, 
                    "role": "customer", 
                    "created_at": created_at
                }
                cust_payload_dict = {
                    "customer_id": customer_id, 
                    "user_id": user_id, 
                    "full_name": full_name, 
                    "email": email, 
                    "phone": phone, 
                    "shipping_address": address, 
                    "updated_at": created_at
                }
                
                user_payload = json.dumps(user_payload_dict)
                cust_payload = json.dumps(cust_payload_dict)
                
                conn.execute('''INSERT INTO sync_queue VALUES (?, 'users', 'INSERT', ?, ?, ?, 0)''', (sync_id_u, user_id, user_payload, created_at))
                conn.execute('''INSERT INTO sync_queue VALUES (?, 'customers', 'INSERT', ?, ?, ?, 0)''', (sync_id_c, customer_id, cust_payload, created_at))

            conn.commit()

            # 🔐 AUTO-AUTHENTICATE USER: Establish session parameters immediately
            session['user_id'] = user_id
            session['username'] = username
            session['role'] = 'customer'
            session['customer_id'] = customer_id

            # 🛒 GUEST CART MERGE ENGINE
            if 'guest_cart' in session and session['guest_cart']:
                guest_cart = session['guest_cart']
                try:
                    for prod_id, quantity in guest_cart.items():
                        existing = conn.execute(
                            "SELECT * FROM cart_items WHERE customer_id = ? AND product_id = ?",
                            (customer_id, prod_id)
                        ).fetchone()

                        if existing:
                            # CORRECTED: Target by composite keys instead of missing cart_item_id
                            conn.execute(
                                "UPDATE cart_items SET quantity = quantity + ? WHERE customer_id = ? AND product_id = ?",
                                (quantity, customer_id, prod_id)
                            )
                        else:
                            conn.execute(
                                """
                                INSERT INTO cart_items (customer_id, product_id, quantity, created_at)
                                VALUES (?, ?, ?, ?)
                                """,
                                (customer_id, prod_id, quantity, created_at)
                            )
                    conn.commit()
                    session.pop('guest_cart', None)
                    flash("Welcome! Your temporary items have been saved to your new account.", "info")
                except Exception as e:
                    conn.rollback()
                    print(f"[-] GUEST CART SIGN-UP SYNC FAILURE: {e}")

            conn.close()
            flash(f"Account successfully created! Welcome, {full_name}!", "success")

            # 🔀 DYNAMIC ROUTING FLOW INTERCEPTOR
            next_target = session.pop('next_url', None)
            if next_target:
                return redirect(next_target)

            return redirect(url_for('user_dashboard'))

        except Exception as e:
            flash(f"Registration aborted due to structural database error: {str(e)}", "error")
            return redirect(url_for('signup'))

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Authenticates standard clients and administrators using username, email, or phone number."""
    # 1. Immediate routing bypass if already authenticated
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard', user_id=session.get('user_id')))

    if request.method == 'POST':
        # Accept username, email, or phone number into a single neutral tracking variable
        login_identifier = request.form.get('username', '').strip()  # Keeps 'username' name to match front-end form inputs
        password = request.form.get('password', '').strip()

        conn = get_db_connection()
        try:
            # Multi-parameter look-up scanning parent credentials and student/customer profiles alike
            user_data = conn.execute('''
                SELECT 
                    u.user_id, 
                    u.username, 
                    u.password_hash, 
                    u.role, 
                    c.customer_id, 
                    c.full_name
                FROM users u
                LEFT JOIN customers c ON u.user_id = c.user_id
                WHERE u.username = ? COLLATE NOCASE
                   OR c.email = ? COLLATE NOCASE
                   OR c.phone = ?
            ''', (login_identifier, login_identifier, login_identifier)).fetchone()
            
            # Verify password against the cryptographic database record string
            if user_data and check_password_hash(user_data['password_hash'], password):
                
                # Assign core tracking parameters to persistent user session storage
                session['user_id'] = user_data['user_id']
                session['username'] = user_data['username']
                session['role'] = user_data['role']
                session['customer_id'] = user_data['customer_id']  # Will be None if admin profile
                
                # Determine presentation text profile identity
                if user_data['full_name']:
                    display_name = user_data['full_name']
                    session['user_fullname'] = user_data['full_name']
                else:
                    display_name = user_data['username']
                    session['user_fullname'] = user_data['username']

                # 🛒 GUEST CART MERGE ENGINE
                if user_data['role'] != 'admin' and session['customer_id'] and 'guest_cart' in session:
                    guest_cart = session['guest_cart']
                    try:
                        for prod_id, quantity in guest_cart.items():
                            existing = conn.execute(
                                "SELECT * FROM cart_items WHERE customer_id = ? AND product_id = ?",
                                (session['customer_id'], prod_id)
                            ).fetchone()

                            if existing:
                                conn.execute(
                                    "UPDATE cart_items SET quantity = quantity + ? WHERE customer_id = ? AND product_id = ?",
                                    (quantity, session['customer_id'], prod_id)
                                )
                            else:
                                conn.execute(
                                    """
                                    INSERT INTO cart_items (customer_id, product_id, quantity, created_at)
                                    VALUES (?, ?, ?, ?)
                                    """,
                                    (session['customer_id'], prod_id, quantity, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                                )
                        conn.commit()
                        session.pop('guest_cart', None)
                        flash("Your temporary guest selections have been safely linked to your account!", "info")
                    except Exception as e:
                        conn.rollback()
                        print(f"[-] GUEST CART LOG-IN SYNC FAILURE: {e}")
                
                # Close connection right before handling routing redirections
                conn.close()

                # 🔀 DYNAMIC INTERCEPTED ROUTING FLOW
                if user_data['role'] == 'admin':
                    flash(f"Administrative session initiated. Welcome back, {display_name}!", "success")
                    return redirect(url_for('admin_dashboard'))
                else:
                    flash(f"Logged in successfully. Welcome back, {display_name}!", "success")
                    
                    next_target = session.pop('next_url', None)
                    if next_target:
                        return redirect(next_target)
                        
                    return redirect(url_for('user_dashboard', user_id=user_data['user_id']))
            else:
                flash("Invalid identity credentials or profile password matching keys.", "error")
                
        finally:
            # This safety guard blocks lingering open socket connections if mutations or lookups crash
            try:
                conn.close()
            except (sqlite3.ProgrammingError, NameError, UnboundLocalError):
                pass  # Connection was already closed cleanly above or not initialized

    return render_template('login.html')

@app.route('/dashboard')
def user_dashboard():
    """Customer dashboard showing profile details and ERP-style order history."""

    # ==========================================
    # AUTHENTICATION CHECK
    # ==========================================
    if 'user_id' not in session or session.get('role') != 'customer':
        session.clear()
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        customer_id = session.get('customer_id')

        # ==========================================
        # FETCH CUSTOMER PROFILE
        # ==========================================
        customer_details = conn.execute('''
            SELECT *
            FROM customers
            WHERE customer_id = ?
        ''', (customer_id,)).fetchone()

        # ==========================================
        # FETCH ORDERS (HEADER TABLE)
        # ==========================================
        orders = conn.execute('''
            SELECT *
            FROM orders
            WHERE customer_id = ?
            ORDER BY created_at DESC
        ''', (customer_id,)).fetchall()

        # ==========================================
        # BUILD ERP ORDER STRUCTURE (WITH TYPE-SAFE CONVERSION)
        # ==========================================
        orders_with_items = []

        for order in orders:
            # --------------------------------------
            # FETCH ORDER LINE ITEMS
            # --------------------------------------
            items = conn.execute('''
                SELECT
                    oi.item_id,
                    oi.quantity,
                    oi.unit_price,
                    oi.total_price,
                    p.product_id,
                    p.name,
                    p.image,
                    p.price
                FROM order_items oi
                JOIN products p
                    ON oi.product_id = p.product_id
                WHERE oi.order_id = ?
            ''', (order['order_id'],)).fetchall()

            # --------------------------------------
            # TYPE-SAFE PRICE PARSING & FORMATTING
            # --------------------------------------
            formatted_items = []
            for item in items:
                try:
                    # Strip any accidental text characters like commas/currency symbols, then convert to float
                    raw_unit = str(item['unit_price']).replace(',', '').replace('UGX', '').strip()
                    raw_total = str(item['total_price']).replace(',', '').replace('UGX', '').strip()
                    
                    unit_price_float = float(raw_unit) if raw_unit else 0.0
                    total_price_float = float(raw_total) if raw_total else 0.0
                except (ValueError, TypeError):
                    unit_price_float = 0.0
                    total_price_float = 0.0

                formatted_items.append({
                    'item_id': item['item_id'],
                    'quantity': item['quantity'],
                    'unit_price': "{:,.0f}".format(unit_price_float),
                    'total_price': "{:,.0f}".format(total_price_float),
                    'product_id': item['product_id'],
                    'name': item['name'],
                    'image': item['image'],
                    'price': item['price']
                })

            # Format the order header total amount safely
            try:
                raw_grand_total = str(order['total_amount']).replace(',', '').replace('UGX', '').strip()
                grand_total_float = float(raw_grand_total) if raw_grand_total else 0.0
            except (ValueError, TypeError):
                grand_total_float = 0.0

            formatted_order = {
                'order_id': order['order_id'],
                'customer_id': order['customer_id'],
                'created_at': order['created_at'],
                'order_status': order['order_status'],
                'total_amount': "{:,.0f}".format(grand_total_float)
            }

            # --------------------------------------
            # ATTACH ITEMS TO ORDER
            # --------------------------------------
            orders_with_items.append({
                'order': formatted_order,
                'items': formatted_items
            })

        conn.close()

        # ==========================================
        # RENDER DASHBOARD
        # ==========================================
        return render_template(
            'user/user_dashboard.html',
            orders_with_items=orders_with_items,
            profile=customer_details
        )

    except Exception as e:
        print(f"[-] user dashboard failure event: {e}")
        return "<h3>Profile View Processing Error</h3>", 500

# ==========================================
# CLIENT PROFILE UPDATES & MAINTENANCE DATA PATHS
# ==========================================

@app.route('/dashboard/update_profile', methods=['POST'])
def update_profile():
    """Modifies client structural identifiers inside core ledger tables."""
    if 'user_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login'))

    full_name = request.form.get('full_name', '').strip()
    phone = request.form.get('phone', '').strip()

    if not full_name:
        flash("Full Name structure cannot be completely empty.", "error")
        return redirect(url_for('user_dashboard'))

    try:
        conn = get_db_connection()
        customer_id = session.get('customer_id')
        updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn.execute('''
            UPDATE customers 
            SET full_name = ?, phone = ?, updated_at = ?
            WHERE customer_id = ?
        ''', (full_name, phone, updated_at, customer_id))

        # Offline synchronization sync queue engine hook
        if app.config.get('ENV_MODE') == 'OFFLINE':
            sync_id = f"SYNC-{uuid.uuid4().hex[:12].upper()}"
            payload = f'{{"customer_id": "{customer_id}", "full_name": "{full_name}", "phone": "{phone}", "updated_at": "{updated_at}"}}'
            conn.execute('''
                INSERT INTO sync_queue (sync_id, target_table, action_type, row_primary_key, payload_json, created_at, is_synced)
                VALUES (?, 'customers', 'UPDATE', ?, ?, ?, 0)
            ''', (sync_id, customer_id, payload, updated_at))

        conn.commit()
        conn.close()

        # Update display values across current active cookie session traces
        session['user_fullname'] = full_name
        flash("Profile identification parameters reconfigured cleanly.", "success")
    except Exception as e:
        print(f"[-] Profile compilation mismatch runtime exception: {e}")
        flash("Critical database pipeline error mapping record elements.", "error")

    return redirect(url_for('user_dashboard'))

@app.route('/dashboard/update_address', methods=['POST'])
def update_address():
    """Adjusts primary fulfillment physical addresses for incoming delivery queues."""
    if 'user_id' not in session or session.get('role') != 'customer':
        return redirect(url_for('login'))

    address = request.form.get('shipping_address', '').strip()

    if not address:
        flash("Please declare a readable delivery drops target zone.", "error")
        return redirect(url_for('user_dashboard'))

    try:
        conn = get_db_connection()
        customer_id = session.get('customer_id')
        updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn.execute('''
            UPDATE customers 
            SET shipping_address = ?, updated_at = ?
            WHERE customer_id = ?
        ''', (address, updated_at, customer_id))

        if app.config.get('ENV_MODE') == 'OFFLINE':
            sync_id = f"SYNC-{uuid.uuid4().hex[:12].upper()}"
            payload = f'{{"customer_id": "{customer_id}", "shipping_address": "{address}", "updated_at": "{updated_at}"}}'
            conn.execute('''
                INSERT INTO sync_queue (sync_id, target_table, action_type, row_primary_key, payload_json, created_at, is_synced)
                VALUES (?, 'customers', 'UPDATE', ?, ?, ?, 0)
            ''', (sync_id, customer_id, payload, updated_at))

        conn.commit()
        conn.close()

        session['user_shipping'] = address
        flash("Fulfillment destination tracking updated natively.", "success")
    except Exception as e:
        print(f"[-] Infrastructure address execution failure: {e}")
        flash("Could not write record adjustments onto target storage blocks.", "error")

    return redirect(url_for('user_dashboard'))

@app.route('/dashboard/change_password', methods=['POST'])
def change_password():
    """Overwrites password hashes using checked cryptographic salts safely."""
    if 'user_id' not in session:
        return redirect(url_for('login'))

    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')

    if not current_password or not new_password:
        flash("Password verification frames cannot be left completely empty.", "error")
        return redirect(url_for('user_dashboard'))

    try:
        conn = get_db_connection()
        user_id = session.get('user_id')

        user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()

        if user and check_password_hash(user['password_hash'], current_password):
            new_hash = generate_password_hash(new_password)
            conn.execute('UPDATE users SET password_hash = ? WHERE user_id = ?', (new_hash, user_id))

            if app.config.get('ENV_MODE') == 'OFFLINE':
                sync_id = f"SYNC-{uuid.uuid4().hex[:12].upper()}"
                updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                payload = f'{{"user_id": "{user_id}", "password_hash": "{new_hash}"}}'
                conn.execute('''
                    INSERT INTO sync_queue (sync_id, target_table, action_type, row_primary_key, payload_json, created_at, is_synced)
                    VALUES (?, 'users', 'UPDATE', ?, ?, ?, 0)
                ''', (sync_id, user_id, payload, updated_at))

            conn.commit()
            flash("System cryptographic signature modified successfully.", "success")
        else:
            flash("Invalid current signature keys matching.", "error")

        conn.close()
    except Exception as e:
        print(f"[-] Password tracking system interruption: {e}")
        flash("Internal error processing access keys validation codes.", "error")

    return redirect(url_for('user_dashboard'))

# ==========================================
# SECURE ADMINISTRATIVE ACCESS CONTROL ROUTES
# ==========================================
@app.route('/admin/admin_login', methods=['GET', 'POST'])
def admin_login():
    """Protects operational management backend views through strict credential verification."""
    if 'user_id' in session and session.get('role') == 'admin':
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? COLLATE NOCASE', (username,)).fetchone()
        conn.close()

        if user and user['role'] == 'admin' and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f"Welcome back, Administrative Controller {user['username']}!", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid operational credentials specified.", "error")

    return render_template('admin/admin_login.html')

@app.route('/admin/logout')
def logout():
    """Destroys active administration sessions safely."""
    session.clear()
    flash("You have been signed out successfully.", "success")
    return redirect(url_for('index'))

@app.route('/admin/admin_dashboard')
def admin_dashboard():
    """Displays comprehensive statistics, active sync queues, inventory alerts, and message states."""
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))

    try:
        conn = get_db_connection()
        
        products = conn.execute("SELECT * FROM products").fetchall()
        total_products = conn.execute('SELECT COUNT(*) FROM products').fetchone()[0] or 0
        total_orders = conn.execute('SELECT COUNT(*) FROM orders').fetchone()[0] or 0
        unread_messages = conn.execute('SELECT COUNT(*) FROM customer_messages WHERE is_read = 0').fetchone()[0] or 0
        pending_syncs = conn.execute('SELECT COUNT(*) FROM sync_queue WHERE is_synced = 0').fetchone()[0] or 0
        total_customers = conn.execute('SELECT COUNT(*) FROM customers').fetchone()[0] or 0
        recent_messages = conn.execute('SELECT * FROM customer_messages ORDER BY created_at DESC LIMIT 5').fetchall()
        conn.close()

        return render_template(
            'admin/admin_dashboard.html',
            total_products=total_products,
            total_orders=total_orders,
            unread_messages=unread_messages,
            pending_syncs=pending_syncs,
            total_customers=total_customers,
            recent_messages=recent_messages,
            products=products,
            admin_title='Dashboard',
            admin_subtitle='Manufacturing enterprise overview',
        )
        
    except Exception as e:
        print(f"[-] Dashboard processing failure: {e}")
        return "<h3>Dashboard Execution Failure</h3><p>Ensure your database schema layer matches perfectly.</p>", 500


# Ensure your application upload configurations are mapped out
UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

@app.route('/admin/product/add', methods=['POST'])
def admin_add_product():
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    # -------------------------
    # FORM DATA
    # -------------------------
    product_name = request.form.get('product_name', '').strip()
    category = request.form.get('category', '').strip()
    description = request.form.get('description', '').strip()
    whatsapp_order_text = request.form.get('whatsapp_order_text', '').strip()

    price_raw = request.form.get('price', '0').strip()
    stock_raw = request.form.get('stock_quantity', '0').strip()

    if not product_name or not category or not price_raw or not stock_raw:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    try:
        price = float(price_raw)
        stock_quantity = int(stock_raw)
    except ValueError:
        return jsonify({"status": "error", "message": "Invalid number format"}), 400

    # -------------------------
    # MULTI IMAGE UPLOAD
    # -------------------------
    image_files = request.files.getlist('product_images')
    saved_images = []

    if image_files:
        for file in image_files:
            if file and file.filename != '':
                ext = os.path.splitext(file.filename)[1].lower()
                if ext in ['.jpg', '.jpeg', '.png', '.webp']:
                    filename = f"PROD-{uuid.uuid4().hex[:10].upper()}{ext}"
                    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(upload_path)
                    saved_images.append(filename)

    # Fallback if no image uploaded
    if len(saved_images) == 0:
        saved_images = ['default_product.jpg']

    main_image = saved_images[0]

    # -------------------------
    # IDS + TIME
    # -------------------------
    product_id = f"PRD-{uuid.uuid4().hex[:12].upper()}"
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    updated_at = created_at

    try:
        conn = get_db_connection()

        # -------------------------
        # INSERT PRODUCT (MAIN)
        # -------------------------
        conn.execute('''
            INSERT INTO products (
                product_id,
                name,
                description,
                category,
                price,
                stock_quantity,
                image,
                whatsapp_order_text,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            product_id,
            product_name,
            description,
            category,
            price,
            stock_quantity,
            main_image,
            whatsapp_order_text,
            created_at,
            updated_at
        ))

        # -------------------------
        # INSERT ALL IMAGES
        # -------------------------
        for index, img in enumerate(saved_images):
            conn.execute('''
                INSERT INTO product_images (
                    product_id,
                    image,
                    is_primary,
                    sort_order
                )
                VALUES (?, ?, ?, ?)
            ''', (
                product_id,
                img,
                1 if index == 0 else 0,
                index
            ))

        # -------------------------
        # OFFLINE SYNC (UNCHANGED PAYLOAD)
        # -------------------------
        if app.config['ENV_MODE'] == 'OFFLINE':
            sync_id = f"SYNC-{uuid.uuid4().hex[:12].upper()}"

            # Kept your exact JSON configuration format injection
            payload = f'''{{
                "product_id": "{product_id}",
                "name": "{product_name}",
                "description": "{description}",
                "category": "{category}",
                "price": {price},
                "stock_quantity": {stock_quantity},
                "image": "{main_image}",
                "whatsapp_order_text": "{whatsapp_order_text}",
                "images": {json.dumps(saved_images)},
                "created_at": "{created_at}"
            }}'''

            conn.execute('''
                INSERT INTO sync_queue (
                    sync_id,
                    target_table,
                    action_type,
                    row_primary_key,
                    payload_json,
                    created_at,
                    is_synced
                )
                VALUES (?, 'products', 'INSERT', ?, ?, ?, 0)
            ''', (sync_id, product_id, payload, created_at))

        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "message": "Product created with multi-image gallery support"
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/admin/product/edit/<product_id>', methods=['POST'])
def admin_edit_product(product_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({
            "status": "error",
            "message": "Unauthorized systemic clearance access denied."
        }), 403

    product_name = request.form.get('product_name', '').strip()
    category = request.form.get('category', '').strip()
    description = request.form.get('description', '').strip()
    whatsapp_order_text = request.form.get('whatsapp_order_text', '').strip()

    price_raw = request.form.get('price', '0').strip()
    stock_raw = request.form.get('stock_quantity', '0').strip()

    if not product_name or not category or not price_raw or not stock_raw:
        return jsonify({
            "status": "error",
            "message": "Mandatory update properties cannot remain empty values."
        }), 400

    try:
        price = float(price_raw)
        stock_quantity = int(stock_raw)
    except ValueError:
        return jsonify({
            "status": "error",
            "message": "Supplied pricing metrics do not match strict data types."
        }), 400

    try:
        conn = get_db_connection()

        current_product = conn.execute(
            '''
            SELECT *
            FROM products
            WHERE product_id = ?
            ''',
            (product_id,)
        ).fetchone()

        if not current_product:
            conn.close()
            return jsonify({
                "status": "error",
                "message": "Target inventory key could not be located."
            }), 404

        main_image = current_product['image']

        # =====================================
        # MULTI IMAGE UPLOAD
        # =====================================
        image_files = request.files.getlist('product_images')
        new_images = []

        if image_files:
            for file in image_files:
                if file and file.filename != '':
                    ext = os.path.splitext(file.filename)[1].lower()
                    if ext in ['.jpg', '.jpeg', '.png', '.webp']:
                        filename = f"PROD-{uuid.uuid4().hex[:10].upper()}{ext}"
                        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(upload_path)
                        new_images.append(filename)

        # =====================================
        # UPDATE PRODUCT MAIN THUMBNAIL
        # =====================================
        if len(new_images) > 0:
            main_image = new_images[0]

        updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        conn.execute(
            '''
            UPDATE products
            SET
                name = ?,
                description = ?,
                category = ?,
                price = ?,
                stock_quantity = ?,
                image = ?,
                whatsapp_order_text = ?,
                updated_at = ?
            WHERE product_id = ?
            ''',
            (
                product_name,
                description,
                category,
                price,
                stock_quantity,
                main_image,
                whatsapp_order_text,
                updated_at,
                product_id
            )
        )

        # =====================================
        # SAVE NEW GALLERY IMAGES
        # =====================================
        if len(new_images) > 0:
            # Check current entry count to dynamically calculate correct sort_order safely
            existing_count_row = conn.execute(
                '''
                SELECT COUNT(*)
                FROM product_images
                WHERE product_id = ?
                ''',
                (product_id,)
            ).fetchone()
            existing_count = existing_count_row[0] if existing_count_row else 0

            for index, img in enumerate(new_images):
                conn.execute(
                    '''
                    INSERT INTO product_images (
                        product_id,
                        image,
                        is_primary,
                        sort_order
                    )
                    VALUES (?, ?, ?, ?)
                    ''',
                    (
                        product_id,
                        img,
                        1 if existing_count == 0 and index == 0 else 0,
                        existing_count + index
                    )
                )

        # =====================================
        # OFFLINE SYNC
        # =====================================
        if app.config['ENV_MODE'] == 'OFFLINE':
            sync_id = f"SYNC-{uuid.uuid4().hex[:12].upper()}"

            payload = f'''{{
                "product_id":"{product_id}",
                "name":"{product_name}",
                "description":"{description}",
                "category":"{category}",
                "price":{price},
                "stock_quantity":{stock_quantity},
                "image":"{main_image}"
            }}'''

            conn.execute(
                '''
                INSERT INTO sync_queue (
                    sync_id,
                    target_table,
                    action_type,
                    row_primary_key,
                    payload_json,
                    created_at,
                    is_synced
                )
                VALUES (?, 'products', 'UPDATE', ?, ?, ?, 0)
                ''',
                (
                    sync_id,
                    product_id,
                    payload,
                    updated_at
                )
            )

        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "message": "Product updated successfully with gallery support."
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Modification block sequence fault execution halted: {str(e)}"
        }), 500

@app.route('/admin/product/images/<product_id>', methods=['GET'])
def get_product_images(product_id):
    """
    Fetches extra image attachments mapping parameters for a specific product code execution pipeline.
    """
    try:
        # 1. Connect to your database
        db = get_db_connection() # Or your equivalent database connection mechanism
        
        # 2. Query the image attachments matching this specific product_id
        # Replace 'product_images' and column names with your actual database schema names
        cursor = db.execute(
            "SELECT id, image FROM product_images WHERE product_id = ?", 
            (product_id,)
        )
        images_rows = cursor.fetchall()
        
        # 3. Format into a structured list of dictionaries matching what the JavaScript expects
        images_list = []
        for row in images_rows:
            images_list.append({
                "id": row['id'],
                "image": row['image'] # This matches data.images[x].image in JavaScript
            })
        
        # 4. Send back a clean success response matrix mapping
        return jsonify({
            "status": "success",
            "images": images_list
        }), 200

    except Exception as e:
        print(f"Database query error line failure: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Failed to extract linked media assets catalog records mapping."
        }), 500

@app.route('/admin/product/delete/<product_id>', methods=['POST'])
def admin_delete_product(product_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"status": "error", "message": "Insufficient access privileges."}), 403

    try:
        conn = get_db_connection()
        item_check = conn.execute('SELECT 1 FROM products WHERE product_id = ?', (product_id,)).fetchone()
        if not item_check:
            conn.close()
            return jsonify({"status": "error", "message": "Item identifier mismatch or already removed."}), 404

        conn.execute('DELETE FROM products WHERE product_id = ?', (product_id,))

        if app.config['ENV_MODE'] == 'OFFLINE':
            sync_id = f"SYNC-{uuid.uuid4().hex[:12].upper()}"
            deleted_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            payload = f'{{"product_id": "{product_id}"}}'
            
            conn.execute('''
                INSERT INTO sync_queue (sync_id, target_table, action_type, row_primary_key, payload_json, created_at, is_synced)
                VALUES (?, 'products', 'DELETE', ?, ?, ?, 0)
            ''', (sync_id, product_id, payload, deleted_at))

        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Target entry removed entirely from localized tables."})
    except Exception as e:
        return jsonify({"status": "error", "message": f"Cascade drop error constraint: {str(e)}"}), 500

@app.route('/admin/product/image/delete/<int:image_id>', methods=['POST'])
def delete_product_image(image_id):
    """
    Permanently unlinks and purges a specific product image asset.
    """
    try:
        db = get_db_connection()
        
        # 1. Fetch the filename before deleting the record so we can clean up the file system
        cursor = db.execute("SELECT image FROM product_images WHERE id = ?", (image_id,))
        row = cursor.fetchone()
        
        if not row:
            return jsonify({
                "status": "error",
                "message": "Target asset record not found in data ledger."
            }), 404
            
        # Support both tuple index or row factory naming types safely
        filename = row['image'] if hasattr(row, 'keys') else row[0]
        
        # 2. Erase record from the database mapping table
        db.execute("DELETE FROM product_images WHERE id = ?", (image_id,))
        db.commit()
        
        # 3. Clean up the physical file from your static uploads folder safely
        if filename:
            file_path = os.path.join(current_app.root_path, 'static', 'uploads', filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                
        return jsonify({
            "status": "success",
            "message": "Asset dropped successfully."
        }), 200

    except Exception as e:
        print(f"Media asset erasure pipeline fault: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Internal structural compilation or database state execution fault."
        }), 500

@app.route('/admin/settings/update', methods=['POST'])
def update_site_settings():
    """
    Safely intercepts site config form variables from the high-density panel,
    updating dynamic enterprise parameters directly inside the master schemas.
    """
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Operational Refused: Administrative token validation failure.", "error")
        return redirect(url_for('login'))
        
    site_name = request.form.get('site_name', '').strip()
    primary_color = request.form.get('primary_color', '').strip()
    secondary_color = request.form.get('secondary_color', '').strip()
    email_contact = request.form.get('email_contact', '').strip()
    announcement_text = request.form.get('announcement_text', '').strip()
    
    # Checkbox logic: if present in form payload, set true (1), else false (0)
    show_announcement = 1 if request.form.get('show_announcement') == '1' else 0

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify if an execution configuration row exists to update, otherwise insert anew
        config_exists = cursor.execute("SELECT 1 FROM site_config LIMIT 1").fetchone()
        
        if config_exists:
            cursor.execute('''
                UPDATE site_config 
                SET site_name = ?, primary_color = ?, secondary_color = ?, 
                    email_contact = ?, announcement_text = ?, show_announcement = ?
            ''', (site_name, primary_color, secondary_color, email_contact, announcement_text, show_announcement))
        else:
            cursor.execute('''
                INSERT INTO site_config (site_id, site_name, primary_color, secondary_color, email_contact, announcement_text, show_announcement)
                VALUES (1, ?, ?, ?, ?, ?, ?)
            ''', (site_name, primary_color, secondary_color, email_contact, announcement_text, show_announcement))
            
        conn.commit()
        conn.close()
        flash("System control settings committed and applied successfully.", "success")
    except Exception as e:
        print(f"[CRITICAL CONFIG FAULT] Failed to update parameters: {e}")
        flash("Database operational fault encountered while committing settings changes.", "error")
        
    return redirect(url_for('admin_dashboard'))

# Target storage directories configuration map
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/admin/hero-slides')
def admin_hero_slides():
    """Renders the Hero Slider CMS manager interface dashboard."""
    if 'role' not in session or session.get('role') != 'admin':
        flash("Unauthorized system access vector.", "error")
        return redirect(url_for('index'))

    # Open data context channels via framework manager helpers
    conn = get_db_connection()
    
    # Fetch all slides in sequentially order to match dashboard positioning expectations
    hero_slides = conn.execute('SELECT * FROM hero_slides ORDER BY position ASC').fetchall()
    conn.close()
    
    # Renders the management page passing data attributes accurately matching your loop engines
    return render_template('admin/admin_hero_slides.html', hero_slides=hero_slides)

@app.route('/admin/hero-slides/create', methods=['POST'])
def create_hero_slide():

    # ==========================================
    # ADMIN SECURITY CHECK
    # ==========================================
    if 'role' not in session or session.get('role') != 'admin':
        flash("Unauthorized system access vector.", "error")
        return redirect(url_for('index'))

    try:

        # ==========================================
        # FORM DATA
        # ==========================================
        title = request.form.get('title', '').strip()
        subtitle = request.form.get('subtitle', '').strip()
        badge_text = request.form.get('badge', '').strip()
        button_text = request.form.get('button_text', '').strip()
        button_link = request.form.get('button_link', '').strip()
        overlay_color = request.form.get('overlay_color', '').strip()

        image = request.files.get('background_image')

        # ==========================================
        # IMAGE PROCESSING
        # ==========================================
        filename = "default-banner.jpg"

        if image and image.filename != '':

            # Ensure upload folder exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

            # Generate safe unique filename
            ext = image.filename.split('.')[-1].lower()

            filename = f"HERO_{uuid.uuid4().hex[:10].upper()}.{ext}"

            # Save image
            image.save(
                os.path.join(
                    app.config['UPLOAD_FOLDER'],
                    filename
                )
            )

        # ==========================================
        # DATABASE INSERT
        # ==========================================
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO hero_slides
            (
                title,
                subtitle,
                badge_text,
                button_text,
                button_link,
                overlay_color,
                background_image
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            title,
            subtitle,
            badge_text,
            button_text,
            button_link,
            overlay_color,
            filename
        ))

        conn.commit()
        conn.close()

        flash(
            "Hero slide created successfully!",
            "success"
        )

    except Exception as e:

        import traceback
        traceback.print_exc()

        try:
            conn.rollback()
        except:
            pass

        flash(
            f"Failed to create hero slide: {str(e)}",
            "error"
        )

    return redirect(url_for('admin_hero_slides'))

@app.route('/admin/hero-slides/edit', methods=['POST'])
def edit_hero_slide():
    """Processes entry content modifications, tracks asset files transitions and applies modifications."""
    if 'role' not in session or session.get('role') != 'admin':
        flash("Unauthorized system access vector.", "error")
        return redirect(url_for('index'))

    slide_id = request.form.get('slide_id')
    title = request.form.get('title', '').strip() or "Updated Promotion Title"
    subtitle = request.form.get('subtitle', '').strip() or "Updated asset description parameters."
    badge_text = request.form.get('badge', '').strip() or "FEATURED"
    button_text = request.form.get('button_text', '').strip() or "Browse Catalog"
    button_link = request.form.get('button_link', '').strip() or "/admin/inventory"
    overlay_color = request.form.get('overlay_color', '').strip() or "rgba(15, 23, 42, 0.6)"

    image = request.files.get('background_image')

    conn = get_db_connection()
    cursor = conn.cursor()

    # Dynamic Column Structure Discovery Check to prevent schema layout crashes
    cursor.execute("PRAGMA table_info(hero_slides)")
    columns = [row[1] for row in cursor.fetchall()]
    img_col = "background_image"

    try:
        if image and image.filename != '':
            # Handle incoming updated replacement banner slide wallpaper safely
            ext = image.filename.split('.')[-1].lower()
            filename = f"HERO_{uuid.uuid4().hex[:10].upper()}.{ext}"
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            query = f"""
                UPDATE hero_slides 
                SET title=?, subtitle=?, badge_text=?, button_text=?, button_link=?, overlay_color=?, {img_col}=?
                WHERE slide_id=?
            """
            cursor.execute(query, (title, subtitle, badge_text, button_text, button_link, overlay_color, filename, slide_id))
        else:
            # Maintain current saved image path if no file substitution occurred
            query = f"""
                UPDATE hero_slides 
                SET title=?, subtitle=?, badge_text=?, button_text=?, button_link=?, overlay_color=?
                WHERE slide_id=?
            """
            cursor.execute(query, (title, subtitle, badge_text, button_text, button_link, overlay_color, slide_id))

        conn.commit()
        flash('Hero slide modifications compiled successfully!', 'success')
    except sqlite3.Error as err:
        conn.rollback()
        flash(f'System failed to update hero slide: {err}', 'error')
    finally:
        conn.close()

    return redirect(url_for('admin_hero_slides'))

@app.route('/admin/hero-slides/delete/<string:slide_id>')
def delete_hero_slide(slide_id):
    """Deletes historical slide database rows permanently based on their unique tracking identifier keys."""
    if 'role' not in session or session.get('role') != 'admin':
        flash("Unauthorized system access vector.", "error")
        return redirect(url_for('index'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("DELETE FROM hero_slides WHERE slide_id = ?", (slide_id,))
        conn.commit()
        flash('Selected promotional storefront hero slide purged successfully.', 'success')
    except sqlite3.Error as err:
        conn.rollback()
        flash(f'Purge routine stopped by transactional tracking layers: {err}', 'error')
    finally:
        conn.close()

    return redirect(url_for('admin_hero_slides'))

@app.route('/admin/inventory')
def admin_inventory():

    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row

        products = conn.execute("""
            SELECT * 
            FROM products 
            WHERE is_active = 1 
            ORDER BY product_id DESC
        """).fetchall()

        conn.close()

    except Exception as e:
        print(f"[-] Inventory Load Error: {e}")
        products = []  # SAFE FALLBACK

    return render_template(
        "admin/admin_inventory.html",
        products=products,
        admin_title="Inventory Management",
        admin_subtitle="Manufacturing stock control system"
    )

@app.route('/admin/orders')
def admin_orders():

    try:
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row  # IMPORTANT: ensures dict-like rows

        # ==========================================
        # FETCH ALL ORDERS
        # ==========================================
        orders = conn.execute('''
            SELECT
                o.*,
                c.full_name,
                c.phone,
                c.email
            FROM orders o
            LEFT JOIN customers c
                ON o.customer_id = c.customer_id
            ORDER BY o.created_at DESC
        ''').fetchall()

        orders_with_items = []

        # ==========================================
        # ATTACH ITEMS TO EACH ORDER
        # ==========================================
        for order in orders:

            items = conn.execute('''
                SELECT
                    oi.item_id,
                    oi.quantity,
                    oi.unit_price,
                    oi.total_price,
                    p.product_id,
                    p.name AS product_name,
                    p.image AS image_filename,
                    p.price
                FROM order_items oi
                JOIN products p
                    ON oi.product_id = p.product_id
                WHERE oi.order_id = ?
            ''', (order['order_id'],)).fetchall()

            from types import SimpleNamespace

            orders_with_items.append(SimpleNamespace(
                order=order,
                items=items
            ))
            
        # ==========================================
        # STATISTICS
        # ==========================================
        total_orders = conn.execute(
            "SELECT COUNT(*) FROM orders"
        ).fetchone()[0]

        pending_orders = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE order_status = 'Pending'"
        ).fetchone()[0]

        completed_orders = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE order_status = 'Delivered'"
        ).fetchone()[0]

        total_revenue = conn.execute('''
            SELECT COALESCE(SUM(total_amount), 0)
            FROM orders
            WHERE payment_status = 'Paid'
        ''').fetchone()[0]

        conn.close()

        # ==========================================
        # RENDER TEMPLATE
        # ==========================================
        return render_template(
            'admin/admin_orders.html',

            orders_with_items=orders_with_items,

            total_orders=total_orders,
            pending_orders=pending_orders,
            completed_orders=completed_orders,
            total_revenue=total_revenue,

            admin_title="Orders",
            admin_subtitle="Customer order management system"
        )

    except Exception as e:
        print(f"[ORDER DASHBOARD ERROR]: {e}")
        return f"System Error Loading Orders: {e}"



######################## CART ROUTES ##################


@app.route('/cart/add', methods=['POST'])
def add_to_cart():

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    product_id = request.form.get('product_id')

    try:
        qty = int(request.form.get('qty', 1))
    except:
        qty = 1

    if not product_id:

        return jsonify({
            'status': 'error',
            'message': 'Missing product'
        }), 400

    # =====================================================
    # LOGGED-IN USER
    # =====================================================

    if 'customer_id' in session:

        customer_id = session['customer_id']

        conn = get_db_connection()

        try:

            existing = conn.execute("""
                SELECT *
                FROM cart_items
                WHERE customer_id = ?
                AND product_id = ?
            """, (customer_id, product_id)).fetchone()

            if existing:

                conn.execute("""
                    UPDATE cart_items
                    SET quantity = quantity + ?
                    WHERE cart_item_id = ?
                """, (
                    qty,
                    existing['cart_item_id']
                ))

            else:

                conn.execute("""
                    INSERT INTO cart_items
                    (
                        customer_id,
                        product_id,
                        quantity,
                        created_at
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    customer_id,
                    product_id,
                    qty,
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))

            conn.commit()

            total = conn.execute("""
                SELECT COALESCE(SUM(quantity), 0) AS total
                FROM cart_items
                WHERE customer_id = ?
            """, (customer_id,)).fetchone()['total']

            conn.close()

            return jsonify({
                'status': 'success',
                'message': 'Product added to cart!',
                'new_count': total,
                'checkout_url': url_for('checkout')
            })

        except Exception as e:

            conn.rollback()
            conn.close()

            print(e)

            return jsonify({
                'status': 'error',
                'message': 'Database cart failure.'
            })

    # =====================================================
    # GUEST USER
    # =====================================================

    else:

        if 'guest_cart' not in session:
            session['guest_cart'] = {}

        guest_cart = session['guest_cart']

        guest_cart[product_id] = guest_cart.get(product_id, 0) + qty

        session['guest_cart'] = guest_cart
        session.modified = True

        total = sum(int(v) for v in guest_cart.values())

        # IMPORTANT:
        session['next_url'] = url_for('checkout')

        return jsonify({
            'status': 'success',
            'message': 'Product added to cart!',
            'new_count': total,
            'redirect_signup': True,
            'signup_url': url_for('signup')
        })

@app.route('/cart')
def view_cart():
    cart_items = []
    total = 0
    
    # User logged in: pull details from DB tables
    if 'customer_id' in session:
        conn = get_db_connection()
        # Ensure row factory is enabled in your connection layout to access columns by string names
        db_items = conn.execute("""
            SELECT c.cart_item_id, p.product_id, p.name, p.price, p.image, c.quantity 
            FROM cart_items c
            JOIN products p ON c.product_id = p.product_id
            WHERE c.customer_id = ?
        """, (session['customer_id'],)).fetchall()
        
        for item in db_items:
            subtotal = item['price'] * item['quantity']
            total += subtotal
            cart_items.append({
                'cart_item_id': item['cart_item_id'],
                'product_id': item['product_id'],
                'name': item['name'],
                'price': item['price'],
                'image': item['image'],
                'quantity': item['quantity'],
                'total': subtotal
            })
        conn.close()
        
    # User is guest: read structural identifiers out of session object
    else:
        guest_cart = session.get('guest_cart', {})
        if guest_cart:
            conn = get_db_connection()
            for prod_id, quantity in guest_cart.items():
                product = conn.execute("SELECT * FROM products WHERE product_id = ?", (prod_id,)).fetchone()
                if product:
                    subtotal = product['price'] * quantity
                    total += subtotal
                    cart_items.append({
                        'cart_item_id': prod_id, # Using product_id as reference for removals
                        'product_id': product['product_id'],
                        'name': product['name'],
                        'price': product['price'],
                        'image': product['image'],
                        'quantity': quantity,
                        'total': subtotal
                    })
            conn.close()

    return render_template('cart.html', cart=cart_items, total=total)

@app.route('/cart/remove/<item_id>', methods=['POST', 'GET'])
def remove_from_cart(item_id):

    is_ajax = (
        request.headers.get('X-Requested-With')
        == 'XMLHttpRequest'
    )

    # ==========================================
    # LOGGED-IN USER
    # ==========================================

    if 'customer_id' in session:

        customer_id = session['customer_id']

        conn = get_db_connection()

        try:

            # VERIFY OWNERSHIP
            existing = conn.execute("""
                SELECT *
                FROM cart_items
                WHERE cart_item_id = ?
                AND customer_id = ?
            """, (
                item_id,
                customer_id
            )).fetchone()

            if not existing:

                conn.close()

                if is_ajax:
                    return jsonify({
                        'status': 'error',
                        'message': 'Cart item not found.'
                    }), 404

                flash(
                    'Cart item not found.',
                    'error'
                )

                return redirect(
                    url_for('view_cart')
                )

            # DELETE ITEM
            conn.execute("""
                DELETE FROM cart_items
                WHERE cart_item_id = ?
                AND customer_id = ?
            """, (
                item_id,
                customer_id
            ))

            conn.commit()

            # RECALCULATE CART COUNT
            total = conn.execute("""
                SELECT COALESCE(SUM(quantity),0)
                AS total
                FROM cart_items
                WHERE customer_id = ?
            """, (
                customer_id,
            )).fetchone()['total']

            conn.close()

            if is_ajax:

                return jsonify({
                    'status': 'success',
                    'message': 'Item removed from cart.',
                    'new_count': total
                })

            flash(
                'Item removed successfully.',
                'success'
            )

            return redirect(url_for('view_cart'))

        except Exception as e:

            conn.rollback()
            conn.close()

            print(f"Cart Remove Error: {e}")

            if is_ajax:

                return jsonify({
                    'status': 'error',
                    'message': 'Failed to remove item.'
                }), 500

            flash(
                'Failed to remove item.',
                'error'
            )

            return redirect(url_for('view_cart'))

    # ==========================================
    # GUEST USER
    # ==========================================

    else:

        guest_cart = session.get(
            'guest_cart',
            {}
        )

        # IMPORTANT:
        # Guest cart keys are usually PRODUCT IDs
        if str(item_id) not in guest_cart:

            if is_ajax:

                return jsonify({
                    'status': 'error',
                    'message': 'Cart item not found.'
                }), 404

            flash(
                'Cart item not found.',
                'error'
            )

            return redirect(url_for('view_cart'))

        # REMOVE ITEM
        del guest_cart[str(item_id)]

        session['guest_cart'] = guest_cart
        session.modified = True

        total = sum(
            int(v)
            for v in guest_cart.values()
        )

        if is_ajax:

            return jsonify({
                'status': 'success',
                'message': 'Item removed from cart.',
                'new_count': total
            })

        flash(
            'Item removed successfully.',
            'success'
        )

        return redirect(url_for('view_cart'))

@app.route('/cart/update', methods=['POST'])
def update_cart():

    is_ajax = (
        request.headers.get('X-Requested-With')
        == 'XMLHttpRequest'
    )

    # ==========================================
    # SAFE INPUT EXTRACTION (FIXED FOR MULTIPLE ITEMS)
    # ==========================================

    item_ids = request.form.getlist('item_id[]')
    qtys = request.form.getlist('qty[]')

    # ==========================================
    # LOGGED-IN USER
    # ==========================================

    if 'customer_id' in session:

        customer_id = session['customer_id']
        conn = get_db_connection()

        try:

            # LOOP THROUGH ALL CART ITEMS
            for item_id, qty in zip(item_ids, qtys):

                # SAFE QTY CONVERSION
                try:
                    qty = int(qty)
                except:
                    qty = 1

                if qty < 1:
                    qty = 1

                # SECURITY VALIDATION
                existing = conn.execute("""
                    SELECT *
                    FROM cart_items
                    WHERE cart_item_id = ?
                    AND customer_id = ?
                """, (
                    item_id,
                    customer_id
                )).fetchone()

                if not existing:
                    continue  # skip invalid items instead of failing whole request

                # UPDATE QUANTITY
                conn.execute("""
                    UPDATE cart_items
                    SET quantity = ?
                    WHERE cart_item_id = ?
                """, (
                    qty,
                    item_id
                ))

            conn.commit()

            # RECALCULATE CART COUNT
            total = conn.execute("""
                SELECT COALESCE(SUM(quantity),0)
                AS total
                FROM cart_items
                WHERE customer_id = ?
            """, (
                customer_id,
            )).fetchone()['total']

            conn.close()

            if is_ajax:

                return jsonify({
                    'status': 'success',
                    'message': 'Cart updated.',
                    'new_count': total
                })

            flash(
                'Cart updated successfully.',
                'success'
            )

            return redirect(url_for('view_cart'))

        except Exception as e:

            conn.rollback()
            conn.close()

            print(f"Cart Update Error: {e}")

            if is_ajax:

                return jsonify({
                    'status': 'error',
                    'message': 'Failed to update cart.'
                }), 500

            flash(
                'Failed to update cart.',
                'error'
            )

            return redirect(url_for('view_cart'))

    # ==========================================
    # GUEST USER
    # ==========================================

    else:

        guest_cart = session.get('guest_cart', {})

        # FIXED: convert list updates properly
        for item_id, qty in zip(item_ids, qtys):

            try:
                qty = int(qty)
            except:
                qty = 1

            if qty < 1:
                qty = 1

            if item_id not in guest_cart:
                continue

            guest_cart[item_id] = qty

        session['guest_cart'] = guest_cart
        session.modified = True

        total = sum(
            int(v)
            for v in guest_cart.values()
        )

        if is_ajax:

            return jsonify({
                'status': 'success',
                'message': 'Cart updated.',
                'new_count': total
            })

        flash(
            'Cart updated successfully.',
            'success'
        )

        return redirect(url_for('view_cart'))

########################################################END


######################## CKECKOUT ROUTES ##################

# Import your unified payment gateway handler class
from payments import YoUgandaProvider

# Instantiate gateway configurations globally
payment_gateway = YoUgandaProvider(username="sandbox_user", password="secret_password", sandbox_mode=True)

import re
import secrets  # Standard library module to generate clean, random tokens

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    # ---- 1. GET REQUEST: DATA EXTRACTION & MANIFEST DISPLAY ----
    if request.method == 'GET':
        conn = get_db_connection()
        checkout_items = []
        total_amount = 0

        # If logged in, fetch from database cart_items table using your original query
        if 'customer_id' in session:
            customer_id = session['customer_id']
            items_raw = conn.execute('''
                SELECT 
                    c.product_id,
                    c.quantity,
                    p.name,
                    p.price,
                    p.stock_quantity
                FROM cart_items c
                JOIN products p ON c.product_id = p.product_id
                WHERE c.customer_id = ?
            ''', (customer_id,)).fetchall()
            
            checkout_items = [{
                'product_id': item['product_id'],
                'quantity': item['quantity'],
                'name': item['name'],
                'price': item['price'],
                'stock_quantity': item['stock_quantity']
            } for item in items_raw]
        
        # If true anonymous guest, extract from temporary session array stack
        else:
            guest_cart = session.get('guest_cart', {})
            if guest_cart:
                placeholders = ','.join(['?'] * len(guest_cart))
                products_raw = conn.execute(f'''
                    SELECT product_id, name, price, stock_quantity 
                    FROM products 
                    WHERE product_id IN ({placeholders})
                ''', list(guest_cart.keys())).fetchall()

                for p in products_raw:
                    pid = str(p['product_id'])
                    qty = int(guest_cart[pid])
                    checkout_items.append({
                        'product_id': p['product_id'],
                        'quantity': qty,
                        'name': p['name'],
                        'price': p['price'],
                        'stock_quantity': p['stock_quantity']
                    })

        conn.close()

        if not checkout_items:
            flash("Your shopping cart is currently empty.", "error")
            return redirect(url_for('view_cart'))

        total_amount = sum(item['quantity'] * item['price'] for item in checkout_items)
        
        return render_template(
            'checkout.html', 
            checkout_items=checkout_items, 
            total_amount=total_amount
        )

    # ---- 2. POST REQUEST: TRANSACTIONAL ACCOUNT CREATION & CHECKOUT ATOMIC MATRIX ----
    if request.method == 'POST':
        conn = get_db_connection()
        
        try:
            # PHASE A: Dual-table account provisioning if dealing with an anonymous guest
            if 'customer_id' not in session:
                full_name = request.form.get('full_name')
                email = request.form.get('email')
                phone = request.form.get('phone')
                password = request.form.get('password')
                shipping_address = request.form.get('shipping_address')

                # Changed validation: username is no longer expected from form; full_name is mandatory
                if not (full_name and email and phone and password):
                    flash("All mandatory registration profile elements (Full Name, Email, Phone, and Password) must be completed.", "error")
                    conn.close()
                    return redirect(url_for('checkout'))

                # Expanded conflict check: Ensure neither Email nor Phone number already exists
                existing_profile = conn.execute('''
                    SELECT customer_id FROM customers WHERE email = ? OR phone = ?
                ''', (email, phone)).fetchone()
                
                if existing_profile:
                    flash("An active user profile already matches this email address or phone number. Please login.", "error")
                    conn.close()
                    return redirect(url_for('checkout'))

                # --- AUTO-GENERATE USERNAME FROM FULL NAME ---
                # Clean full name down to lowercase alphanumeric string
                base_username = re.sub(r'[^a-zA-Z0-9]', '', full_name).lower()
                if not base_username:
                    base_username = "user"
                # Append 4 random digits to make it uniquely identifying
                generated_username = f"{base_username}{secrets.randbelow(9000) + 1000}"

                # Universal current time parameters
                timestamp_now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # 1. Generate core primary keys matching your structural system prefixes
                new_user_id = f"USR-{uuid.uuid4().hex[:12].upper()}"
                new_customer_id = f"CST-{uuid.uuid4().hex[:12].upper()}"

                # 2. Hash password sequence matching your users table column (password_hash)
                hashed_pw = generate_password_hash(password)

                # 3. Create Row entry into parent 'users' table using the newly generated username
                conn.execute('''
                    INSERT INTO users (user_id, username, password_hash, role, created_at)
                    VALUES (?, ?, ?, 'customer', ?)
                ''', (new_user_id, generated_username, hashed_pw, timestamp_now))

                # 4. Create Row entry into child 'customers' table containing mandatory full_name
                conn.execute('''
                    INSERT INTO customers (
                        customer_id, user_id, full_name, email, phone, 
                        shipping_address, updated_at, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (new_customer_id, new_user_id, full_name, email, phone, 
                      shipping_address, timestamp_now, timestamp_now))
                
                # Push values immediately into active application session tracking
                session['customer_id'] = new_customer_id
                session['user_id'] = new_user_id
                session['username'] = generated_username
                session['user_fullname'] = full_name
                session['role'] = 'customer'

                # Migrate items from session['guest_cart'] straight into database cart_items table
                guest_cart = session.get('guest_cart', {})
                for pid, qty in guest_cart.items():
                    conn.execute('''
                        INSERT INTO cart_items (customer_id, product_id, quantity, created_at)
                        VALUES (?, ?, ?, ?)
                    ''', (new_customer_id, pid, qty, timestamp_now))
                
                # Wipe temporary session guest cart cleanly
                session.pop('guest_cart', None)

            # PHASE B: Process Order Settlement Pipeline
            customer_id = session['customer_id']

            # 1. Fetch live updated cart configurations from database
            cart_items = conn.execute('''
                SELECT 
                    c.product_id,
                    c.quantity,
                    p.name,
                    p.price,
                    p.stock_quantity
                FROM cart_items c
                JOIN products p ON c.product_id = p.product_id
                WHERE c.customer_id = ?
            ''', (customer_id,)).fetchall()

            if not cart_items:
                conn.close()
                flash("Your shopping cart data track could not be verified.", "error")
                return redirect(url_for('view_cart'))

            # 2. Critical Stock Verification Step
            for item in cart_items:
                if item['quantity'] > item['stock_quantity']:
                    flash(f"Insufficient stock available for '{item['name']}'. Only {item['stock_quantity']} left. Please adjust your quantity.", "error")
                    conn.close()
                    return redirect(url_for('view_cart'))

            # 3. Calculate total
            total_amount = sum(item['quantity'] * item['price'] for item in cart_items)

            # 4. Extract Payment Specifications from Front-End Sub-form
            payment_method = request.form.get('payment_method')  # 'mobile_money', 'cash_on_delivery', 'visa'
            payment_status = 'Unpaid'
            order_status = 'Pending'
            gateway_reference = None

            # Generate Unique Identifiers for tracking ahead of external API compilation
            order_id = f"ORD-{uuid.uuid4().hex[:10].upper()}"
            created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Execute context payment calls before modifying local inventories
            if payment_method == 'mobile_money':
                momo_phone = request.form.get('momo_phone')
                api_result = payment_gateway.initiate_mobile_money_pull(momo_phone, total_amount, order_id)
                
                if api_result['status'] == 'success':
                    payment_status = 'Pending PIN Entry'
                    gateway_reference = api_result['transaction_reference']
                else:
                    flash(f"Mobile Money automation failed: {api_result['message']}", "error")
                    conn.close()
                    return redirect(url_for('checkout'))

            elif payment_method == 'visa':
                card_name = request.form.get('card_name')
                card_number = request.form.get('card_number').replace(" ", "")
                card_expiry = request.form.get('card_expiry')
                card_cvv = request.form.get('card_cvv')
                
                api_result = payment_gateway.process_visa_charge(
                    card_name, card_number, card_expiry, card_cvv, total_amount, order_id
                )
                
                if api_result['status'] == 'success':
                    payment_status = 'Paid via Visa'
                    order_status = 'Processing'
                    gateway_reference = api_result['transaction_reference']
                else:
                    flash(f"Payment Authorization Declined: {api_result['message']}", "error")
                    conn.close()
                    return redirect(url_for('checkout'))
            
            else:  # cash_on_delivery
                payment_status = 'Pay on Delivery'
                order_status = 'Pending'

            # 5. Create order header row entry
            conn.execute('''
                INSERT INTO orders (
                    order_id, customer_id, total_amount,
                    order_status, payment_status, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (order_id, customer_id, total_amount, order_status, payment_status, created_at))

            # 6. Create order items rows
            for item in cart_items:
                product_id = item['product_id']
                qty = item['quantity']
                price = item['price']
                sub_total = qty * price

                conn.execute('''
                    INSERT INTO order_items (
                        order_id, product_name, product_price, quantity, unit_price, total_price, created_at, product_id
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (order_id, item['name'], price, qty, price, sub_total, created_at, product_id))

                conn.execute('''
                    UPDATE products
                    SET stock_quantity = stock_quantity - ?
                    WHERE product_id = ?
                ''', (qty, product_id))

            # 7. Clear account database-backed cart safely
            conn.execute('DELETE FROM cart_items WHERE customer_id = ?', (customer_id,))

            # Finalize unified transaction scope allocations atomically
            conn.commit()
            conn.close()

            # Display contextual confirmation notices
            if payment_method == 'mobile_money':
                flash("Order recorded! Please verify the instant prompt sent to your phone to authorize settlement.", "success")
            elif payment_method == 'visa':
                flash("Visa card charged successfully. Your order is now being processed!", "success")
            else:
                flash("Order created successfully! Prepare payment obligations upon delivery localization setup.", "success")
                
            # Grab user_id out of the active session context before executing redirect string compilation
            user_id = session.get('user_id')
            
            # Direct authorized session path cleanly to user dashboard panel route
            return redirect(url_for('user_dashboard', user_id=user_id))

        except Exception as e:
            if conn:
                conn.rollback()
                conn.close()
            print(f"[-] CHECKOUT ROUTE TRANSACTION EXCEPTION FAILURE: {e}")
            flash("An error occurred while finalizing your checkout transaction. Please try again.", "error")
            return redirect(url_for('view_cart'))

######################## ORDERS ROUTES ##################

@app.route('/order/success/<order_id>')
def order_success(order_id):

    return render_template("order_success.html", order_id=order_id)






@app.route('/admin/messages')
def admin_messages():
    """
    Renders the dedicated standalone workspace feed for customer messages log streams.
    """
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Access Denied: Administrative token required.", "error")
        return redirect(url_for('login'))
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Pull messages log sorted by recency tracking parameters
        recent_messages = cursor.execute('SELECT * FROM customer_messages ORDER BY created_at DESC').fetchall()
                
        conn.close()
        
        # point this string context to the actual name of your messages template file
        return render_template(
            'admin/admin_messages.html', 
            recent_messages=recent_messages,
        )
    except Exception as e:
        print(f"[-] Customer messages compilation block fault: {e}")
        return "<h3>Internal Matrix Storage Error</h3>", 500

@app.route('/admin/messages/mark-read/<message_id>', methods=['POST'])
def admin_mark_message_read(message_id):
    if 'user_id' not in session or session.get('role') != 'admin':
        return jsonify({"status": "error", "message": "Clearance missing."}), 403
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE customer_messages SET is_read = 1 WHERE message_id = ?', (message_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "State synchronized."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/product/<product_id>')
def product_detail(product_id):
    try:
        conn = get_db_connection()

        # -------------------------------
        # 1. FETCH PRODUCT
        # -------------------------------
        product = conn.execute(
            "SELECT * FROM products WHERE product_id = ? AND is_active = 1",
            (product_id,)
        ).fetchone()

        if product is None:
            conn.close()
            return "Product not found", 404

        # -------------------------------
        # 2. FETCH GALLERY IMAGES
        # -------------------------------
        images = conn.execute(
            """
            SELECT * FROM product_images
            WHERE product_id = ?
            ORDER BY is_primary DESC, sort_order ASC, id ASC
            """,
            (product_id,)
        ).fetchall()

        # Convert to simple list for Jinja
        image_list = [img['image'] for img in images] if images else []

        # -------------------------------
        # 3. FALLBACK SAFETY (ENSURE IMAGE ALWAYS EXISTS)
        # -------------------------------
        if not image_list:
            if product['image']:
                image_list = [product['image']]
            else:
                image_list = ['default_product.jpg']

        # -------------------------------
        # 4. CART COUNT LOGIC (UNCHANGED BUT CLEANED)
        # -------------------------------
        cart_count = 0
        user_id = session.get('user_id')

        if user_id:
            customer = conn.execute(
                "SELECT customer_id FROM customers WHERE user_id = ?",
                (user_id,)
            ).fetchone()

            if customer:
                result = conn.execute(
                    "SELECT SUM(quantity) as total FROM cart_items WHERE customer_id = ?",
                    (customer['customer_id'],)
                ).fetchone()

                if result and result['total'] is not None:
                    cart_count = int(result['total'])

        else:
            if 'guest_cart' in session and isinstance(session['guest_cart'], dict):
                cart_count = sum(int(qty) for qty in session['guest_cart'].values())
            elif 'cart' in session and isinstance(session['cart'], dict):
                cart_count = sum(int(qty) for qty in session['cart'].values())

        conn.close()

        # -------------------------------
        # 5. RENDER TEMPLATE
        # -------------------------------
        return render_template(
            "product_detail.html",
            product=product,
            images=image_list,              # NEW
            cart_count=cart_count
        )

    except Exception as e:
        print(f"[-] Product detail error context log trace: {e}")
        return "System error loading product", 500

@app.route('/admin/orders/update-status/<order_id>', methods=['POST'])
def update_order_status(order_id):

    if 'user_id' not in session:
        return jsonify({
            "status": "error",
            "message": "Unauthorized"
        })

    try:
        # =========================
        # SUPPORT BOTH FORM + JSON
        # =========================

        if request.is_json:
            data = request.get_json()
            new_status = data.get("status")
        else:
            new_status = request.form.get("status")

        allowed = [
            "Pending",
            "Processing",
            "Shipped",
            "Delivered",
            "Cancelled"
        ]

        if new_status not in allowed:
            return jsonify({
                "status": "error",
                "message": "Invalid status"
            })

        conn = get_db_connection()

        conn.execute("""
            UPDATE orders
            SET order_status = ?
            WHERE order_id = ?
        """, (new_status, order_id))

        conn.commit()
        conn.close()

        # =========================
        # RESPONSE TYPE DECISION
        # =========================

        # If AJAX request (modal)
        if request.is_json:
            return jsonify({"status": "success"})

        # If old form request
        return redirect(url_for('admin_orders'))

    except Exception as e:
        print(e)

        if request.is_json:
            return jsonify({
                "status": "error",
                "message": str(e)
            })

        return redirect(url_for('admin_orders'))

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    """
    Renders corporate control nodes on GET requests and updates web_settings rows
    on POST requests, logging transaction states inside the Offline Sync Queue matrix.
    """
    # Enforce administrative state tracking security parameters
    if 'user_id' not in session or session.get('role') != 'admin':
        flash("Operation Denied: Valid administrative token not detected.", "error")
        return redirect(url_for('login'))

    settings_id = 'SYSTEM_CONF'

    if request.method == 'POST':
        # 1. Capture and sanitize incoming field records
        site_name = request.form.get('site_name', 'Kasi Rice').strip()
        primary_color = request.form.get('primary_color', '#16a34a').strip()
        secondary_color = request.form.get('secondary_color', '#ea580c').strip()
        email_contact = request.form.get('email_contact', '').strip()
        phone_contact = request.form.get('phone_contact', '').strip()
        announcement_text = request.form.get('announcement_text', '').strip()
        
        # Checkbox switch resolution logic
        show_announcement = 1 if request.form.get('show_announcement') == '1' else 0

        # Extract About section blocks
        about_title = request.form.get('about_title', '').strip()
        about_subtitle = request.form.get('about_subtitle', '').strip()
        about_vision = request.form.get('about_vision', '').strip()
        about_mission = request.form.get('about_mission', '').strip()
        about_motto = request.form.get('about_motto', '').strip()
        about_description = request.form.get('about_description', '').strip()

        # Extract Milestone Dashboard counters safely as numeric digits
        try:
            stats_employees = int(request.form.get('stats_employees', 35))
            stats_capacity = int(request.form.get('stats_capacity', 2500))
            stats_years = int(request.form.get('stats_years', 4))
        except ValueError:
            stats_employees, stats_capacity, stats_years = 35, 2500, 4

        updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Check if row profile exists to branch tracking execution rules
            exists = cursor.execute("SELECT 1 FROM web_settings WHERE settings_id = ?", (settings_id,)).fetchone()

            if exists:
                cursor.execute('''
                    UPDATE web_settings 
                    SET site_name = ?, primary_color = ?, secondary_color = ?, 
                        email_contact = ?, phone_contact = ?, announcement_text = ?, show_announcement = ?,
                        about_title = ?, about_subtitle = ?, about_vision = ?, about_mission = ?, 
                        about_motto = ?, about_description = ?, stats_employees = ?, stats_capacity = ?, 
                        stats_years = ?, updated_at = ?
                    WHERE settings_id = ?
                ''', (site_name, primary_color, secondary_color, email_contact, phone_contact, 
                      announcement_text, show_announcement, about_title, about_subtitle, 
                      about_vision, about_mission, about_motto, about_description, 
                      stats_employees, stats_capacity, stats_years, updated_at, settings_id))
                action_type = 'UPDATE'
            else:
                cursor.execute('''
                    INSERT INTO web_settings (
                        settings_id, site_name, primary_color, secondary_color, email_contact, phone_contact, 
                        announcement_text, show_announcement, about_title, about_subtitle, about_vision, 
                        about_mission, about_motto, about_description, stats_employees, stats_capacity, 
                        stats_years, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (settings_id, site_name, primary_color, secondary_color, email_contact, phone_contact, 
                      announcement_text, show_announcement, about_title, about_subtitle, about_vision, 
                      about_mission, about_motto, about_description, stats_employees, stats_capacity, 
                      stats_years, updated_at))
                action_type = 'INSERT'

            # =======================================================
            # OFFLINE SYSTEM DISCOVERY SYNCHRONIZATION HOOK
            # =======================================================
            if current_app.config.get('ENV_MODE') == 'OFFLINE':
                sync_id = f"SYNC-{uuid.uuid4().hex[:12].upper()}"
                
                payload = {
                    "settings_id": settings_id,
                    "site_name": site_name,
                    "primary_color": primary_color,
                    "secondary_color": secondary_color,
                    "email_contact": email_contact,
                    "phone_contact": phone_contact,
                    "announcement_text": announcement_text,
                    "show_announcement": show_announcement,
                    "about_title": about_title,
                    "about_subtitle": about_subtitle,
                    "about_vision": about_vision,
                    "about_mission": about_mission,
                    "about_motto": about_motto,
                    "about_description": about_description,
                    "stats_employees": stats_employees,
                    "stats_capacity": stats_capacity,
                    "stats_years": stats_years
                }
                
                cursor.execute('''
                    INSERT INTO sync_queue (sync_id, target_table, action_type, row_primary_key, payload_json, created_at, is_synced)
                    VALUES (?, 'web_settings', ?, ?, ?, ?, 0)
                ''', (sync_id, action_type, settings_id, json.dumps(payload), updated_at))

            conn.commit()
            conn.close()
            flash("System adjustments saved and broadcasted successfully.", "success")
            return redirect(url_for('admin_dashboard'))

        except Exception as e:
            app.logger.error(f"Settings writing failed: {str(e)}")
            flash("Database operational write exception encountered.", "error")

    # GET Workflow handling: Extract current table configurations
    conn = get_db_connection()
    current_settings = conn.execute("SELECT * FROM web_settings WHERE settings_id = ?", (settings_id,)).fetchone()
    conn.close()

    return render_template('admin/admin_settings.html', current_settings=current_settings)



@app.route('/admin/admin_customers')
def admin_customers():

    return render_template(
        'admin/admin_customers.html',

        admin_title='customers',
        admin_subtitle='Manufacturing enterprise overview'

    )

#===========================================
#ROUTE FOR ABOUT PAGE TO BE CONVERTED TO CMS
#===========================================

@app.route('/about')
def about_page():

    about_data = {
        "title": "Kasi Rice — From Our Gardens to Your Table",
        "subtitle": "Cultivating premium, organic grains with care, milling to perfection, and delivering directly to your kitchen.",
        "vision": "To be East Africa's most dependable name in local rice production, transforming agricultural standards by serving whole, farm-fresh grains directly from sustainable local gardens to global households.",
        "mission": "To eliminate complex, expensive supply chains by growing premium rice locally, implementing high-standard clean sorting and precision milling, and delivering affordable, wholesome food options directly to retail and wholesale buyers.",
        "motto": "Naturally Grown. Expertly Cleaned. Exceptionally Plentiful.",
        "description": "At Kasi Rice, we don't just trade agricultural commodities—we own the process from the ground up. By planting, cultivating, and nurturing our own crops in our personal farm gardens, we monitor the biological integrity of every seed. This end-to-end farm ownership allows us to guarantee premium grade whole grains, stunning natural aroma, and top-tier milling yields that external brokers simply cannot match."
    }

    stats = {
        "employees": 120,
        "capacity": 5000,
        "years": 10
    }

    team_members = [
        {"name": "John Engineer", "role": "Production Lead", "image": None},
        {"name": "Sarah Kamya", "role": "Quality Officer", "image": None},
        {"name": "David Ouma", "role": "Operations Manager", "image": None},
        {"name": "Grace N", "role": "Industrial Technician", "image": None},
    ]

    return render_template(
        'aboutus.html',
        about=about_data,
        stats=stats,
        team_members=team_members
    )

@app.route('/admin/invoice/<order_id>')
def download_invoice(order_id):
    try:
        file_path = generate_invoice(order_id)
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        return f"Error generating invoice: {str(e)}"
    
# ==========================================
# SYSTEM ERROR LOGGING & CONTROL HOOKS
# ==========================================
@app.errorhandler(404)
def handle_404_errors(e):

    print(f"[*] 404 Not Found: {request.url}")

    # Detect API / AJAX request
    if request.path.startswith('/admin') or request.is_json:
        return {
            "status": "error",
            "message": "Resource not found"
        }, 404

    # Normal browser request
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('user_dashboard'))

    return render_template(
        "admin/error.html",
        error_message="Page not found"
    ), 404

@app.errorhandler(500)
def handle_500_errors(e):

    print(f"[CRITICAL ERROR]: {e}")

    try:
        conn = get_db_connection()
        conn.rollback()
        conn.close()
    except:
        pass

    # Detect API / AJAX request
    if request.path.startswith('/admin') or request.is_json:
        return {
            "status": "error",
            "message": "Internal server error. Please try again."
        }, 500

    flash("Something went wrong. Please try again.", "error")

    return render_template(
        "admin/error.html",
        error_message="Internal server error occurred safely."
    ), 500


###########################################
#           MY TERMINAL CONNECTION   #######-----copde for my backend terminal
###########################################3


@app.route('/error')
def cause_error():
    try:
        1 / 0
    except Exception:
        app.logger.error("A sample error traceback was captured!", exc_info=True)
    return "Logged an error."

###############                 #################
#           END TERMINAL CONNECTION
#################################################

if __name__ == '__main__':
    import socket
    
    # Build configuration target link addresses
    target_server_url = "http://127.0.0.1:5000/"
    
    # Automatically extract the local machine network IP for easy WiFi LAN discovery
    try:
        # Create a temporary socket to determine the preferred local network interface IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_lan_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_lan_ip = "0.0.0.0"

    print("\n" + "="*70)
    print(" 🚀 AUTOMATED LOCAL NETWORK ENGINE & WIFI DISCOVERY BOUND")
    print("="*70)
    print(f" [*] Local Machine Desktop Link: {target_server_url}")
    if local_lan_ip != "0.0.0.0":
        print(f" [📱] Mobile/Tablet WiFi Link:  http://{local_lan_ip}:5000/")
    else:
        print(f" [📱] Mobile/Tablet WiFi Link:  http://<your-computer-local-ip>:5000/")
    print(" [*] Network Notice: Ensure your mobile device is connected to the SAME WiFi/LAN network.")
    print("="*70 + "\n")
    
    # Fire up the automated browser thread ONLY if operating locally in OFFLINE mode
    if app.config.get('ENV_MODE') == 'OFFLINE':
        print("[*] Local environment node verified. Initializing secure window threading link...")
        browser_thread = threading.Thread(target=launch_local_browser_window, args=(target_server_url,))
        browser_thread.daemon = True
        browser_thread.start()

    # Launch the application process
    app.run( host="0.0.0.0", port=5000, debug=False, use_reloader=False)