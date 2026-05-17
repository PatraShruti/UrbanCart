from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db, init_db
from functools import wraps
import datetime, random, string

app = Flask(__name__)
# Updated secret key for UrbanCart
app.secret_key = 'urbancart-ocean-secret-2026'

with app.app_context():
    init_db()

# ── Helpers ───────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def current_user():
    if 'user_id' not in session:
        return None
    db   = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    db.close()
    return dict(user) if user else None

def gen_code():
    # Updated prefix to UC for UrbanCart
    return 'UC' + ''.join(random.choices(string.digits, k=8))

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/')
def home():
    db         = get_db()
    featured   = db.execute(
        "SELECT p.*,c.name as cat_name FROM products p "
        "JOIN categories c ON p.category_id=c.id "
        "WHERE p.featured=1 ORDER BY p.rating DESC LIMIT 12"
    ).fetchall()
    categories = db.execute("SELECT * FROM categories").fetchall()
    featured   = [dict(p) for p in featured]
    categories = [dict(c) for c in categories]
    db.close()
    return render_template('index.html', user=current_user(),
                           featured=featured, categories=categories)

@app.route('/products')
def products():
    db         = get_db()
    categories = [dict(c) for c in db.execute("SELECT * FROM categories").fetchall()]
    db.close()
    return render_template('products.html', user=current_user(), categories=categories)

@app.route('/product/<int:pid>')
def product_detail(pid):
    db      = get_db()
    product = db.execute(
        "SELECT p.*,c.name as cat_name FROM products p "
        "JOIN categories c ON p.category_id=c.id WHERE p.id=?", (pid,)
    ).fetchone()
    if not product:
        db.close(); return redirect(url_for('products'))
    reviews = db.execute(
        "SELECT r.*,u.username FROM reviews r JOIN users u ON r.user_id=u.id "
        "WHERE r.product_id=? ORDER BY r.created_at DESC", (pid,)
    ).fetchall()
    related = db.execute(
        "SELECT * FROM products WHERE category_id=? AND id!=? ORDER BY rating DESC LIMIT 6",
        (product['category_id'], pid)
    ).fetchall()
    in_wish = False
    if 'user_id' in session:
        in_wish = bool(db.execute(
            "SELECT 1 FROM wishlist WHERE user_id=? AND product_id=?",
            (session['user_id'], pid)
        ).fetchone())
    db.close()
    return render_template('product_detail.html', user=current_user(),
                           product=dict(product),
                           reviews=[dict(r) for r in reviews],
                           related=[dict(r) for r in related],
                           in_wish=in_wish)

@app.route('/cart')
@login_required
def cart_page():
    return render_template('cart.html', user=current_user())

@app.route('/checkout')
@login_required
def checkout():
    db        = get_db()
    cart      = [dict(i) for i in db.execute(
        "SELECT c.qty,p.* FROM cart c JOIN products p ON c.product_id=p.id WHERE c.user_id=?",
        (session['user_id'],)
    ).fetchall()]
    addresses = [dict(a) for a in db.execute(
        "SELECT * FROM addresses WHERE user_id=?", (session['user_id'],)
    ).fetchall()]
    db.close()
    if not cart:
        return redirect(url_for('cart_page'))
    return render_template('checkout.html', user=current_user(), cart=cart, addresses=addresses)

@app.route('/orders')
@login_required
def orders():
    db     = get_db()
    orders = db.execute(
        "SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC",
        (session['user_id'],)
    ).fetchall()
    result = []
    for o in orders:
        items = db.execute(
            "SELECT * FROM order_items WHERE order_id=?", (o['id'],)
        ).fetchall()
        result.append({
            'order': dict(o),
            'items': [dict(i) for i in items]
        })
    db.close()
    return render_template('orders.html', user=current_user(), orders=result)

@app.route('/order/<int:oid>')
@login_required
def order_detail(oid):
    db    = get_db()
    order = db.execute(
        "SELECT * FROM orders WHERE id=? AND user_id=?", (oid, session['user_id'])
    ).fetchone()
    if not order:
        db.close(); return redirect(url_for('orders'))
    items = db.execute("SELECT * FROM order_items WHERE order_id=?", (oid,)).fetchall()
    order = dict(order)
    items = [dict(i) for i in items]
    db.close()
    return render_template('order_detail.html', user=current_user(), order=order, items=items)

@app.route('/wishlist')
@login_required
def wishlist_page():
    db    = get_db()
    items = [dict(i) for i in db.execute(
        "SELECT p.* FROM wishlist w JOIN products p ON w.product_id=p.id WHERE w.user_id=?",
        (session['user_id'],)
    ).fetchall()]
    db.close()
    return render_template('wishlist.html', user=current_user(), items=items)

@app.route('/profile')
@login_required
def profile():
    db        = get_db()
    addresses = [dict(a) for a in db.execute("SELECT * FROM addresses WHERE user_id=?", (session['user_id'],)).fetchall()]
    ocount    = db.execute("SELECT COUNT(*) FROM orders WHERE user_id=?", (session['user_id'],)).fetchone()[0]
    db.close()
    return render_template('profile.html', user=current_user(), addresses=addresses, order_count=ocount)

@app.route('/search')
def search():
    return render_template('search.html', user=current_user(), q=request.args.get('q', ''))

@app.route('/login')
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))
    return render_template('login.html', user=None)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ═══════════════════════════════════════════════════════════════════════════════
# AUTH API
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/register', methods=['POST'])
def register():
    d        = request.json
    username = d.get('username', '').strip()
    email    = d.get('email', '').strip().lower()
    password = d.get('password', '')
    if not all([username, email, password]):
        return jsonify({"error": "All fields are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    db = get_db()
    if db.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
        db.close(); return jsonify({"error": "Username already exists! Please choose another."}), 409
    if db.execute("SELECT 1 FROM users WHERE email=?", (email,)).fetchone():
        db.close(); return jsonify({"error": "Email already registered"}), 409
    db.execute("INSERT INTO users(username,email,password_hash) VALUES(?,?,?)",
               (username, email, generate_password_hash(password)))
    db.commit()
    user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    db.close()
    session['user_id']  = user['id']
    session['username'] = user['username']
    return jsonify({"message": "Signup successful!", "username": username})

@app.route('/api/login', methods=['POST'])
def api_login():
    d        = request.json
    login_id = d.get('username', '').strip()
    password = d.get('password', '')
    db   = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE username=? OR email=?", (login_id, login_id.lower())
    ).fetchone()
    db.close()
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({"error": "Invalid username or password"}), 401
    session['user_id']  = user['id']
    session['username'] = user['username']
    return jsonify({"message": "Login successful!", "username": user['username']})

@app.route('/api/me')
def me():
    if 'user_id' in session:
        return jsonify({"logged_in": True, "username": session.get('username')})
    return jsonify({"logged_in": False})

@app.route('/api/profile/update', methods=['POST'])
@login_required
def update_profile():
    d  = request.json
    db = get_db()
    db.execute("UPDATE users SET full_name=?,phone=? WHERE id=?",
               (d.get('full_name', ''), d.get('phone', ''), session['user_id']))
    db.commit(); db.close()
    return jsonify({"message": "Profile updated ✅"})

# ═══════════════════════════════════════════════════════════════════════════════
# PRODUCTS API
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/products')
def api_products():
    db     = get_db()
    cat    = request.args.get('category', '')
    q      = request.args.get('q', '').lower()
    sort   = request.args.get('sort', 'rating')
    max_p  = request.args.get('max_price', 99999, type=float)
    min_r  = request.args.get('min_rating', 0, type=float)
    query  = "SELECT p.*,c.name as cat_name FROM products p JOIN categories c ON p.category_id=c.id WHERE 1=1"
    params = []
    if cat and cat != 'All':
        query += " AND c.name=?"; params.append(cat)
    if q:
        query += " AND (LOWER(p.name) LIKE ? OR LOWER(p.brand) LIKE ?)"
        params += [f'%{q}%', f'%{q}%']
    query += " AND p.price<=?"; params.append(max_p)
    if min_r > 0:
        query += " AND p.rating>=?"; params.append(min_r)
    sort_map = {
        'rating':     'p.rating DESC',
        'price_asc':  'p.price ASC',
        'price_desc': 'p.price DESC',
        'reviews':    'p.reviews DESC',
    }
    query   += f" ORDER BY {sort_map.get(sort, 'p.rating DESC')}"
    products = db.execute(query, params).fetchall()
    db.close()
    return jsonify([dict(p) for p in products])

@app.route('/api/categories')
def api_categories():
    db   = get_db()
    cats = db.execute(
        "SELECT c.*,COUNT(p.id) as cnt FROM categories c "
        "LEFT JOIN products p ON c.id=p.category_id GROUP BY c.id"
    ).fetchall()
    db.close()
    return jsonify([dict(c) for c in cats])

# ═══════════════════════════════════════════════════════════════════════════════
# CART API
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/cart')
def get_cart():
    if 'user_id' not in session:
        return jsonify([])
    db    = get_db()
    items = db.execute(
        "SELECT c.qty,p.id,p.name,p.price,p.mrp,p.emoji,p.img,p.brand,p.stock "
        "FROM cart c JOIN products p ON c.product_id=p.id WHERE c.user_id=?",
        (session['user_id'],)
    ).fetchall()
    db.close()
    return jsonify([dict(i) for i in items])

@app.route('/api/cart/add', methods=['POST'])
def add_to_cart():
    if 'user_id' not in session:
        return jsonify({"error": "Please login to add items to cart!"}), 401
    pid  = request.json.get('product_id')
    qty  = request.json.get('qty', 1)
    db   = get_db()
    prod = db.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    if not prod:
        db.close(); return jsonify({"error": "Product not found"}), 404
    ex   = db.execute(
        "SELECT qty FROM cart WHERE user_id=? AND product_id=?",
        (session['user_id'], pid)
    ).fetchone()
    if ex:
        db.execute("UPDATE cart SET qty=? WHERE user_id=? AND product_id=?",
                   (min(ex['qty'] + qty, prod['stock']), session['user_id'], pid))
    else:
        db.execute("INSERT INTO cart(user_id,product_id,qty) VALUES(?,?,?)",
                   (session['user_id'], pid, min(qty, prod['stock'])))
    db.commit()
    count = db.execute("SELECT SUM(qty) FROM cart WHERE user_id=?",
                       (session['user_id'],)).fetchone()[0] or 0
    db.close()
    return jsonify({"message": f"{prod['name']} added to cart ✅", "cart_count": count})

@app.route('/api/cart/update', methods=['POST'])
def update_cart():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    pid = request.json.get('product_id')
    qty = request.json.get('qty', 1)
    db  = get_db()
    if qty <= 0:
        db.execute("DELETE FROM cart WHERE user_id=? AND product_id=?",
                   (session['user_id'], pid))
    else:
        db.execute("UPDATE cart SET qty=? WHERE user_id=? AND product_id=?",
                   (qty, session['user_id'], pid))
    db.commit()
    count = db.execute("SELECT SUM(qty) FROM cart WHERE user_id=?",
                       (session['user_id'],)).fetchone()[0] or 0
    db.close()
    return jsonify({"message": "Updated", "cart_count": count})

@app.route('/api/cart/remove', methods=['POST'])
def remove_from_cart():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    pid = request.json.get('product_id')
    db  = get_db()
    db.execute("DELETE FROM cart WHERE user_id=? AND product_id=?",
               (session['user_id'], pid))
    db.commit()
    count = db.execute("SELECT SUM(qty) FROM cart WHERE user_id=?",
                       (session['user_id'],)).fetchone()[0] or 0
    db.close()
    return jsonify({"message": "Removed", "cart_count": count})

@app.route('/api/cart/clear', methods=['POST'])
def clear_cart():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    db = get_db()
    db.execute("DELETE FROM cart WHERE user_id=?", (session['user_id'],))
    db.commit(); db.close()
    return jsonify({"message": "Cart cleared"})

# ═══════════════════════════════════════════════════════════════════════════════
# WISHLIST API
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/wishlist/toggle', methods=['POST'])
def toggle_wishlist():
    if 'user_id' not in session:
        return jsonify({"error": "Please login"}), 401
    pid = request.json.get('product_id')
    db  = get_db()
    ex  = db.execute(
        "SELECT 1 FROM wishlist WHERE user_id=? AND product_id=?",
        (session['user_id'], pid)
    ).fetchone()
    if ex:
        db.execute("DELETE FROM wishlist WHERE user_id=? AND product_id=?",
                   (session['user_id'], pid))
        added = False
    else:
        db.execute("INSERT INTO wishlist(user_id,product_id) VALUES(?,?)",
                   (session['user_id'], pid))
        added = True
    db.commit(); db.close()
    return jsonify({"added": added, "message": "Added to wishlist ❤️" if added else "Removed from wishlist"})

@app.route('/api/wishlist/move-to-cart', methods=['POST'])
def move_to_cart():
    if 'user_id' not in session:
        return jsonify({"error": "Not logged in"}), 401
    pid = request.json.get('product_id')
    db  = get_db()
    db.execute("DELETE FROM wishlist WHERE user_id=? AND product_id=?",
               (session['user_id'], pid))
    ex = db.execute("SELECT qty FROM cart WHERE user_id=? AND product_id=?",
                    (session['user_id'], pid)).fetchone()
    if ex:
        db.execute("UPDATE cart SET qty=qty+1 WHERE user_id=? AND product_id=?",
                   (session['user_id'], pid))
    else:
        db.execute("INSERT INTO cart(user_id,product_id,qty) VALUES(?,?,1)",
                   (session['user_id'], pid))
    db.commit(); db.close()
    return jsonify({"message": "Moved to cart 🛒"})

# ═══════════════════════════════════════════════════════════════════════════════
# ADDRESS API
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/address/add', methods=['POST'])
@login_required
def add_address():
    d  = request.json
    db = get_db()
    db.execute(
        "INSERT INTO addresses(user_id,label,full_name,phone,line1,line2,city,state,pincode,is_default) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        (session['user_id'], d.get('label', 'Home'), d['full_name'], d['phone'],
         d['line1'], d.get('line2', ''), d['city'], d['state'], d['pincode'],
         1 if d.get('is_default') else 0)
    )
    db.commit(); db.close()
    return jsonify({"message": "Address saved ✅"})

@app.route('/api/address/delete', methods=['POST'])
@login_required
def delete_address():
    db = get_db()
    db.execute("DELETE FROM addresses WHERE id=? AND user_id=?",
               (request.json.get('id'), session['user_id']))
    db.commit(); db.close()
    return jsonify({"message": "Deleted"})

# ═══════════════════════════════════════════════════════════════════════════════
# CHECKOUT / ORDER API
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/checkout', methods=['POST'])
@login_required
def do_checkout():
    db   = get_db()
    cart = db.execute(
        "SELECT c.qty,p.id,p.name,p.price,p.emoji,p.img,p.stock "
        "FROM cart c JOIN products p ON c.product_id=p.id WHERE c.user_id=?",
        (session['user_id'],)
    ).fetchall()
    if not cart:
        db.close(); return jsonify({"error": "Cart is empty"}), 400
    d       = request.json
    payment = d.get('payment', '')
    addr    = d.get('address_snap', '')
    if not payment or not addr:
        db.close(); return jsonify({"error": "Please select address and payment method"}), 400
    subtotal = sum(float(i['price']) * i['qty'] for i in cart)
    shipping = 0 if subtotal >= 499 else 40
    total    = round(subtotal + shipping, 2)
    code     = gen_code()
    db.execute(
        "INSERT INTO orders(user_id,order_code,total,payment,address_snap) VALUES(?,?,?,?,?)",
        (session['user_id'], code, total, payment, addr)
    )
    oid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    for i in cart:
        db.execute(
            "INSERT INTO order_items(order_id,product_id,name,price,qty,img,emoji) VALUES(?,?,?,?,?,?,?)",
            (oid, i['id'], i['name'], i['price'], i['qty'], i['img'], i['emoji'])
        )
        db.execute("UPDATE products SET stock=MAX(0,stock-?) WHERE id=?", (i['qty'], i['id']))
    db.execute("DELETE FROM cart WHERE user_id=?", (session['user_id'],))
    db.commit(); db.close()
    # Updated response message to UrbanCart
    return jsonify({"message": "✅ Order Confirmed! Thank you for shopping with UrbanCart.",
                    "order_id": oid, "order_code": code, "total": total})

# ═══════════════════════════════════════════════════════════════════════════════
# REVIEWS API
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/review/add', methods=['POST'])
@login_required
def add_review():
    d   = request.json
    pid = d.get('product_id')
    db  = get_db()
    try:
        db.execute(
            "INSERT INTO reviews(product_id,user_id,rating,title,body) VALUES(?,?,?,?,?)",
            (pid, session['user_id'], d.get('rating', 5), d.get('title', ''), d.get('body', ''))
        )
        avg = db.execute("SELECT AVG(rating) FROM reviews WHERE product_id=?", (pid,)).fetchone()[0]
        cnt = db.execute("SELECT COUNT(*) FROM reviews WHERE product_id=?", (pid,)).fetchone()[0]
        db.execute("UPDATE products SET rating=?,reviews=? WHERE id=?", (round(avg, 1), cnt, pid))
        db.commit(); db.close()
        return jsonify({"message": "Review submitted ✅"})
    except Exception:
        db.close(); return jsonify({"error": "You've already reviewed this product"}), 409

@app.route('/api/orders')
@login_required
def get_orders_api():
    db     = get_db()
    orders = db.execute(
        "SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC",
        (session['user_id'],)
    ).fetchall()
    result = []
    for o in orders:
        items = db.execute("SELECT * FROM order_items WHERE order_id=?", (o['id'],)).fetchall()
        result.append({'order': dict(o), 'items': [dict(i) for i in items]})
    db.close()
    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)