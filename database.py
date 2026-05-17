import sqlite3, os, random

# Updated to generate urbancart.db
DB_PATH = os.path.join(os.path.dirname(__file__), 'urbancart.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# Keep original name so nothing breaks
def get_db_connection():
    return get_db()

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT UNIQUE NOT NULL,
        email         TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name     TEXT DEFAULT '',
        phone         TEXT DEFAULT '',
        created_at    TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS addresses (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        label      TEXT DEFAULT 'Home',
        full_name  TEXT NOT NULL,
        phone      TEXT NOT NULL,
        line1      TEXT NOT NULL,
        line2      TEXT DEFAULT '',
        city       TEXT NOT NULL,
        state      TEXT NOT NULL,
        pincode    TEXT NOT NULL,
        is_default INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS categories (
        id   INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        icon TEXT DEFAULT '🛍️',
        img  TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS products (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        description TEXT DEFAULT '',
        price       REAL NOT NULL,
        mrp         REAL NOT NULL,
        category_id INTEGER NOT NULL REFERENCES categories(id),
        brand       TEXT DEFAULT '',
        stock       INTEGER DEFAULT 100,
        rating      REAL DEFAULT 4.0,
        reviews     INTEGER DEFAULT 0,
        img         TEXT DEFAULT '',
        emoji       TEXT DEFAULT '🛍️',
        featured    INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS cart (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        qty        INTEGER DEFAULT 1,
        UNIQUE(user_id, product_id)
    );
    CREATE TABLE IF NOT EXISTS wishlist (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        UNIQUE(user_id, product_id)
    );
    CREATE TABLE IF NOT EXISTS orders (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      INTEGER NOT NULL REFERENCES users(id),
        order_code   TEXT NOT NULL UNIQUE,
        total        REAL NOT NULL,
        status       TEXT DEFAULT 'Confirmed',
        payment      TEXT NOT NULL,
        address_snap TEXT NOT NULL,
        created_at   TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS order_items (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id   INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
        product_id INTEGER NOT NULL,
        name       TEXT NOT NULL,
        price      REAL NOT NULL,
        qty        INTEGER NOT NULL,
        img        TEXT DEFAULT '',
        emoji      TEXT DEFAULT '🛍️'
    );
    CREATE TABLE IF NOT EXISTS reviews (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
        user_id    INTEGER NOT NULL REFERENCES users(id),
        rating     INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
        title      TEXT DEFAULT '',
        body       TEXT DEFAULT '',
        created_at TEXT DEFAULT (datetime('now')),
        UNIQUE(product_id, user_id)
    );
    """)
    conn.commit()

    if c.execute("SELECT COUNT(*) FROM categories").fetchone()[0] > 0:
        conn.close(); return

    # ── Seed categories ───────────────────────────────────────────────────────
    cats = [
        ("Dresses",        "👗", "/static/images/d.jpg"),
        ("Electronics",    "📱", "/static/images/ele.webp"),
        ("Footwear",       "👟", "/static/images/ft.webp"),
        ("Accessories",    "💍", "/static/images/acc.webp"),
        ("Home & Kitchen", "🍳", "/static/images/hm.webp"),
        ("Makeup",         "💄", "/static/images/makeup.webp"),
    ]
    c.executemany("INSERT INTO categories(name,icon,img) VALUES(?,?,?)", cats)
    conn.commit()

    cat_ids = {r['name']: r['id'] for r in c.execute("SELECT * FROM categories")}
    random.seed(42)

    # ── Seed products — exact same names + image filenames from your original ──
    CATEGORY_IMAGES = {
        "Dresses":       ["dress1.jpeg","dress2.jpeg","dress3.jpeg","dress4.jpeg","jeans2.avif","jeans3.jpeg","jeans4.jpeg","jeans5.jpeg","kurti2.avif","kurti4.jpeg","kurti5.jpeg","kurti6.jpeg","lehnga1.jpeg","lehnga2.jpeg","saree1.jpeg","saree2.jpeg","saree3.jpeg","short1.jpeg","short3.jpeg","short4.jpeg"],
        "Electronics":   ["elec1.avif","elec2.webp","elec3.webp","elec4.jpeg","elec5.webp","elec6.jpg","elec7.jpg","elec8.webp","elec9.jpg","elec10.webp","elec11.webp","elec12.png","elec13.png","elec14.png","elec15.jpg","elec16.jpg","elec17.jpg","elec18.jpg","elec19.webp","elec20.avif"],
        "Footwear":      ["footwear1.jpeg","footwear2.jpeg","footwear3.jpeg","footwear4.jpeg","footwear5.jpeg","footwear6.jpeg","footwear7.jpeg","footwear8.jpeg","footwear9.jpeg","footwear10.jpeg","footwear11.jpeg","footwear12.jpeg","footwear13.jpeg","footwear14.jpeg","footwear15.jpeg","footwear16.jpeg","footwear17.jpeg","footwear18.jpeg","footwear19.jpeg","footwear20.jpeg"],
        "Accessories":   ["accessories1.jpeg","accessories2.jpeg","accessories3.jpeg","accessories4.jpeg","accessories5.jpeg","accessories6.jpeg","accessories7.jpeg","accessories8.jpeg","accessories9.jpeg","accessories10.jpeg","accessories11.jpeg","accessories12.jpeg","accessories13.jpeg","accessories14.jpeg","accessories15.jpeg","accessories16.jpeg","accessories17.jpeg","accessories18.jpeg","accessories19.jpeg","accessories20.jpeg"],
        "Home & Kitchen":["Kitchen1.jpeg","Kitchen2.jpeg","Kitchen3.jpeg","Kitchen4.jpeg","Kitchen5.jpeg","Kitchen6.jpeg","Kitchen7.jpeg","Kitchen8.jpeg","Kitchen9.jpeg","Kitchen10.jpeg","Kitchen11.jpeg","Kitchen12.jpeg","Kitchen13.avif","Kitchen14.webp","Kitchen15.webp","Kitchen16.jpg","Kitchen17.webp","Kitchen18.webp","Kitchen19.webp","Kitchen20.webp"],
        "Makeup":        ["makeup1.jpeg","makeup2.jpeg","makeup3.jpeg","makeup4.jpeg","makeup5.jpeg","makeup6.jpeg","makeup7.jpeg","makeup8.jpeg","makeup9.png","makeup10.jpeg","makeup11.jpeg","makeup12.png","makeup13.webp","makeup14.jpeg","makeup15.jpeg","makeup16.jpeg","makeup17.jpeg","makeup18.png","makeup19.jpeg","makeup20.jpeg"],
    }
    CATEGORY_NAMES = {
        "Dresses":       ["Black crop top","White off shoulder crop top","White top","Polka print off shoulder top","Denim Jeans","Ripped Jeans","Slim Fit Jeans","High-Waist Jeans","Printed Kurti","Anarkali Kurti","Cotton Kurti","Designer Kurti","Bridal Lehenga","Wedding Lehenga","Silk Saree","Cotton Saree","Georgette Saree","Floral off shoulder frock","Red and Orange bodycon dress","Single strap bodycon"],
        "Electronics":   ["Bluetooth Headphones","Smartphone","Wireless Earbuds","Mixer Grinder","Air Compressor","Cooler","Fridge","Table Fan","Headphones","Iron","DJ Home Theatre","MacBook","Vivo Smartphone","Oppo Smartphone","Mixer Grinder Pro","Charger","ROG Phone 7","Desert Cooler","Sound Box","Washing Machine"],
        "Footwear":      ["White Flats","Brown Sandals","White Sandals","Brown Sandals","White Heels","High Heels","Flats","White Stoned Sandals","Slip-ons","Sneakers","Sneakers White","Shoes","White Pink Lined Shoes","Training Shoes","Platform Sandals","Ethnic Mojari","Slippers","Wedges","Slipper","Sandals"],
        "Accessories":   ["Jhumka","Sunglasses","Wrist Watch","Scarf","Hairbands","Neck Piece","Cap","Charm Bracelet","Safety Pin","Finger Ring","Umbrella","Handbag","Bag","Pendant","Tie","Trolley","Key Ring","School Bag","Hairband","Earring"],
        "Home & Kitchen":["Lunch Box","Electric Kettle","Cutter","Mixer Grinder","Gas Stove","Toaster","Freeze","Gas Stove","Toaster","Toaster","Hotpot","Bed","Almirah","Chair","Pan","Curtain","Dinner Set","Cloth Hanger","Drawer","Glass Set"],
        "Makeup":        ["Lipstick Kiss Beauty","Matte Lipstick","Lip Liner","Foundation","Lip Gloss","Kajal","Mascara","Eye Shadow","Eyebrow Pencil","Compact Powder","Concealer","Cream Blush","Setting Spray","Makeup Set","Lip Gloss","Primer","Blush","Kajal","Lipstick Set","Eyebrow Pencil"],
    }
    CATEGORY_EMOJIS = {"Dresses":"👗","Electronics":"📱","Footwear":"👟","Accessories":"💍","Home & Kitchen":"🍳","Makeup":"💄"}
    PRICE_RANGES   = {"Dresses":(199,2999),"Electronics":(799,24999),"Footwear":(299,2999),"Accessories":(99,4999),"Home & Kitchen":(299,5999),"Makeup":(99,1999)}

    pid = 1
    for cat_name, names in CATEGORY_NAMES.items():
        imgs = CATEGORY_IMAGES[cat_name]
        lo, hi = PRICE_RANGES[cat_name]
        for i, name in enumerate(names):
            price   = round(random.uniform(lo, hi), 2)
            mrp     = round(price * random.uniform(1.15, 1.5), 2)
            stock   = random.randint(10, 200)
            rating  = round(random.uniform(3.7, 4.9), 1)
            rev_cnt = random.randint(20, 3000)
            img     = f"/static/images/{imgs[i]}"
            emoji   = CATEGORY_EMOJIS[cat_name]
            feat    = 1 if i < 4 else 0
            c.execute("""INSERT INTO products(name,price,mrp,category_id,stock,rating,reviews,img,emoji,featured)
                         VALUES(?,?,?,?,?,?,?,?,?,?)""",
                      (name, price, mrp, cat_ids[cat_name], stock, rating, rev_cnt, img, emoji, feat))
            pid += 1

    conn.commit()
    conn.close()
    print("✅ UrbanCart DB initialised with your original product data")