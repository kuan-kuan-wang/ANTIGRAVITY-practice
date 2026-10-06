import os
import sqlite3
from datetime import date
from functools import wraps
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, jsonify, g
)
from werkzeug.security import check_password_hash
from create_db import init_database, DB_NAME

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "antigravity-order-system-secret-key-2026")

DB_PATH = DB_NAME

# ==========================================
# 資料庫連線管理
# ==========================================
def get_db():
    """取得資料庫連線，設定 Row 工廠與開啟外鍵約束"""
    if "db" not in g:
        # 若資料庫不存在則自動初始化
        if not os.path.exists(DB_PATH):
            print(f"[*] 偵測到資料庫不存在，自動執行初始化: {DB_PATH}")
            init_database(DB_PATH)

        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON;")
    return g.db

@app.teardown_appcontext
def close_db(error):
    """請求結束時關閉資料庫連線"""
    db = g.pop("db", None)
    if db is not None:
        db.close()

# ==========================================
# 權限驗證裝飾器 (Feature 5)
# ==========================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("請先以管理員身分登入系統以進行維護操作！", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# 首頁儀表板與 Health Check
# ==========================================
@app.route("/")
def index():
    """系統首頁與統計儀表板 (保留 Hello, World! 與 Python Flask 相容測試)"""
    db = get_db()
    
    # 統計指標
    c_count = db.execute("SELECT COUNT(*) FROM customer;").fetchone()[0]
    p_count = db.execute("SELECT COUNT(*) FROM product;").fetchone()[0]
    o_count = db.execute("SELECT COUNT(*) FROM orders;").fetchone()[0]
    rev_row = db.execute("SELECT COALESCE(SUM(quantity * unit_price), 0) FROM order_item;").fetchone()
    total_rev = rev_row[0] if rev_row else 0

    stats = {
        "customer_count": c_count,
        "product_count": p_count,
        "order_count": o_count,
        "total_revenue": total_rev
    }

    # 最近訂單
    recent_orders = db.execute("""
        SELECT 
            o.order_id,
            c.name AS customer_name,
            o.order_date,
            o.status,
            COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS total_amount
        FROM orders o
        JOIN customer c ON o.customer_id = c.customer_id
        LEFT JOIN order_item oi ON o.order_id = oi.order_id
        GROUP BY o.order_id
        ORDER BY o.order_date DESC, o.order_id DESC
        LIMIT 5;
    """).fetchall()

    return render_template(
        "index.html",
        stats=stats,
        recent_orders=recent_orders,
        title="Python Flask 訂單管理系統 - Hello, World!"
    )

@app.route("/health")
def health():
    """服務健康檢查端點 (CI/CD 專用)"""
    return jsonify(
        status="healthy",
        environment="Render Cloud" if "RENDER" in os.environ else "Local Development"
    )

# ==========================================
# 管理員登入與登出 (Feature 5 & 10)
# ==========================================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        db = get_db()
        admin = db.execute("SELECT * FROM admin_user WHERE username = ?;", (username,)).fetchone()

        if admin and check_password_hash(admin["password_hash"], password):
            session["user"] = admin["username"]
            session["display_name"] = admin["display_name"]
            flash(f"歡迎回來，{admin['display_name']}！", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("orders_list"))
        else:
            flash("帳號或密碼錯誤，請重新輸入！(預設 admin / admin123)", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("您已安全登出系統。", "info")
    return redirect(url_for("login"))

# ==========================================
# 客戶管理 (Feature 5: 維護客戶)
# ==========================================
@app.route("/customers")
@login_required
def customers_list():
    db = get_db()
    customers = db.execute("SELECT * FROM customer ORDER BY customer_id;").fetchall()
    return render_template("customers.html", customers=customers)

@app.route("/customers/add", methods=["POST"])
@login_required
def customer_add():
    cid = request.form.get("customer_id", "").strip()
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()

    if not cid or not name:
        flash("客戶編號與名稱為必填欄位！", "danger")
        return redirect(url_for("customers_list"))

    db = get_db()
    try:
        db.execute(
            "INSERT INTO customer (customer_id, name, phone, address, created_date) VALUES (?, ?, ?, ?, ?);",
            (cid, name, phone, address, date.today().isoformat())
        )
        db.commit()
        flash(f"成功新增客戶「{name}」({cid})！", "success")
    except sqlite3.IntegrityError:
        flash(f"新增失敗：客戶編號「{cid}」已存在，請使用不同編號。", "danger")

    return redirect(url_for("customers_list"))

@app.route("/customers/edit/<customer_id>", methods=["POST"])
@login_required
def customer_edit(customer_id):
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    address = request.form.get("address", "").strip()

    if not name:
        flash("客戶名稱不得為空！", "danger")
        return redirect(url_for("customers_list"))

    db = get_db()
    db.execute(
        "UPDATE customer SET name = ?, phone = ?, address = ? WHERE customer_id = ?;",
        (name, phone, address, customer_id)
    )
    db.commit()
    flash(f"客戶「{name}」({customer_id}) 資料已更新！", "success")
    return redirect(url_for("customers_list"))

@app.route("/customers/delete/<customer_id>", methods=["POST"])
@login_required
def customer_delete(customer_id):
    db = get_db()
    try:
        db.execute("DELETE FROM customer WHERE customer_id = ?;", (customer_id,))
        db.commit()
        flash(f"已刪除客戶 {customer_id}！", "info")
    except sqlite3.IntegrityError:
        flash(f"無法刪除客戶 {customer_id}：此客戶已有歷史訂單關聯，受外鍵完整性約束保護。", "danger")
    return redirect(url_for("customers_list"))

# ==========================================
# 商品管理 (Feature 5 & 7: 維護商品與改價不影響歷史)
# ==========================================
@app.route("/products")
@login_required
def products_list():
    db = get_db()
    products = db.execute("SELECT * FROM product ORDER BY product_id;").fetchall()
    return render_template("products.html", products=products)

@app.route("/products/add", methods=["POST"])
@login_required
def product_add():
    pid = request.form.get("product_id", "").strip()
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    price_str = request.form.get("price", "0").strip()
    stock_str = request.form.get("stock", "0").strip()

    try:
        price = float(price_str)
        stock = int(stock_str)
        if price < 0 or stock < 0:
            raise ValueError("單價與庫存不可為負數")
    except ValueError as e:
        flash(f"輸入數值有誤：{e}", "danger")
        return redirect(url_for("products_list"))

    db = get_db()
    try:
        db.execute(
            "INSERT INTO product (product_id, name, price, stock, category) VALUES (?, ?, ?, ?, ?);",
            (pid, name, price, stock, category)
        )
        db.commit()
        flash(f"成功新增商品「{name}」({pid})！", "success")
    except sqlite3.IntegrityError:
        flash(f"新增失敗：商品編號「{pid}」已存在或違反約束條件。", "danger")

    return redirect(url_for("products_list"))

@app.route("/products/edit/<product_id>", methods=["POST"])
@login_required
def product_edit(product_id):
    name = request.form.get("name", "").strip()
    category = request.form.get("category", "").strip()
    price_str = request.form.get("price", "0").strip()
    stock_str = request.form.get("stock", "0").strip()

    try:
        price = float(price_str)
        stock = int(stock_str)
        if price < 0 or stock < 0:
            raise ValueError("單價與庫存不可為負數")
    except ValueError as e:
        flash(f"輸入數值有誤：{e}", "danger")
        return redirect(url_for("products_list"))

    db = get_db()
    # 更新商品定價 (只變更 product 表，不影響既有 order_item 的 unit_price 快照！)
    db.execute(
        "UPDATE product SET name = ?, price = ?, stock = ?, category = ? WHERE product_id = ?;",
        (name, price, stock, category, product_id)
    )
    db.commit()
    flash(f"商品「{name}」({product_id}) 現行定價與資訊已更新！歷史訂單單價安全保留不變。", "success")
    return redirect(url_for("products_list"))

@app.route("/products/delete/<product_id>", methods=["POST"])
@login_required
def product_delete(product_id):
    db = get_db()
    try:
        db.execute("DELETE FROM product WHERE product_id = ?;", (product_id,))
        db.commit()
        flash(f"已刪除商品 {product_id}！", "info")
    except sqlite3.IntegrityError:
        flash(f"無法刪除商品 {product_id}：該商品已存在於既有訂單明細中，受外鍵完整性約束保護。", "danger")
    return redirect(url_for("products_list"))

# ==========================================
# 訂單管理 (Feature 5, 6, 7, 8, 9)
# ==========================================
@app.route("/orders")
@login_required
def orders_list():
    """訂單列表與直接狀態更新 (Feature 8)"""
    db = get_db()
    orders = db.execute("""
        SELECT 
            o.order_id,
            o.customer_id,
            c.name AS customer_name,
            c.phone AS customer_phone,
            c.address AS customer_address,
            o.order_date,
            o.status,
            o.salesperson,
            COUNT(oi.product_id) AS item_count,
            COALESCE(SUM(oi.quantity * oi.unit_price), 0) AS total_amount
        FROM orders o
        JOIN customer c ON o.customer_id = c.customer_id
        LEFT JOIN order_item oi ON o.order_id = oi.order_id
        GROUP BY o.order_id
        ORDER BY o.order_date DESC, o.order_id DESC;
    """).fetchall()

    return render_template("orders.html", orders=orders)

@app.route("/orders/status/<order_id>", methods=["POST"])
@login_required
def order_update_status(order_id):
    """在訂單列表直接更新狀態 (Feature 8)"""
    new_status = request.form.get("status", "").strip()
    valid_statuses = ["處理中", "已出貨", "已完成", "已取消"]
    if new_status not in valid_statuses:
        flash("不支援的訂單狀態！", "danger")
        return redirect(url_for("orders_list"))

    db = get_db()
    db.execute("UPDATE orders SET status = ? WHERE order_id = ?;", (new_status, order_id))
    db.commit()
    flash(f"訂單 {order_id} 狀態已直接更新為「{new_status}」！", "success")
    return redirect(url_for("orders_list"))

@app.route("/orders/new", methods=["GET", "POST"])
@login_required
def order_new():
    """
    新增訂單 (Feature 6 & 7):
    - 客戶用下拉選單
    - 商品一次勾選多項並填數量
    - 儲存下單當時的單價 (快照)
    """
    db = get_db()

    if request.method == "POST":
        order_id = request.form.get("order_id", "").strip()
        customer_id = request.form.get("customer_id", "").strip()
        order_date = request.form.get("order_date", "").strip()
        salesperson = request.form.get("salesperson", "").strip()
        status = request.form.get("status", "處理中").strip()

        # 取得勾選之多項商品
        selected_products = request.form.getlist("selected_products")

        if not order_id or not customer_id or not order_date:
            flash("訂單編號、客戶與訂單日期為必填項！", "danger")
            return redirect(url_for("order_new"))

        if not selected_products:
            flash("請至少勾選一項商品以建立訂單明細！", "danger")
            return redirect(url_for("order_new"))

        # 檢驗選取商品的購買數量與庫存
        order_items_to_insert = []
        for pid in selected_products:
            qty_str = request.form.get(f"qty_{pid}", "1").strip()
            try:
                qty = int(qty_str)
                if qty <= 0:
                    raise ValueError("購買數量必須大於 0")
            except ValueError:
                flash(f"商品 {pid} 數量無效，必須為大於 0 之正整數！", "danger")
                return redirect(url_for("order_new"))

            # 查詢商品當前定價與庫存 (下單快照點)
            prod = db.execute("SELECT * FROM product WHERE product_id = ?;", (pid,)).fetchone()
            if not prod:
                flash(f"商品 {pid} 不存在！", "danger")
                return redirect(url_for("order_new"))

            if prod["stock"] < qty:
                flash(f"商品「{prod['name']}」庫存不足（現有庫存 {prod['stock']} 件，欲購買 {qty} 件）！", "danger")
                return redirect(url_for("order_new"))

            # 保存「下單當時的單價」 (Feature 7)
            order_items_to_insert.append({
                "product_id": pid,
                "quantity": qty,
                "unit_price": prod["price"]
            })

        # 寫入資料庫 (交易 Transaction 處理)
        try:
            # 1. 寫入 orders 主表
            db.execute("""
                INSERT INTO orders (order_id, customer_id, order_date, status, salesperson)
                VALUES (?, ?, ?, ?, ?);
            """, (order_id, customer_id, order_date, status, salesperson))

            # 2. 寫入 order_item 明細表並同步扣減庫存
            for item in order_items_to_insert:
                db.execute("""
                    INSERT INTO order_item (order_id, product_id, quantity, unit_price)
                    VALUES (?, ?, ?, ?);
                """, (order_id, item["product_id"], item["quantity"], item["unit_price"]))

                db.execute("""
                    UPDATE product SET stock = stock - ? WHERE product_id = ?;
                """, (item["quantity"], item["product_id"]))

            db.commit()
            flash(f"銷售訂單 {order_id} 建立成功！已鎖定當時商品單價並產生出貨單。", "success")
            # 建立完成後直接導向該訂單專屬出貨單頁面 (Feature 9)
            return redirect(url_for("order_detail", order_id=order_id))

        except sqlite3.IntegrityError as e:
            db.rollback()
            flash(f"訂單建立失敗：訂單編號「{order_id}」可能已重複，或約束驗證未通過 ({e})！", "danger")
            return redirect(url_for("order_new"))

    # GET 請求：準備表單所需資料
    customers = db.execute("SELECT customer_id, name, phone FROM customer ORDER BY customer_id;").fetchall()
    products = db.execute("SELECT * FROM product ORDER BY product_id;").fetchall()

    # 自動預測下一組訂單編號 (例如 ORD006)
    last_order = db.execute("SELECT order_id FROM orders ORDER BY order_id DESC LIMIT 1;").fetchone()
    next_order_id = "ORD006"
    if last_order:
        last_id_str = last_order["order_id"]
        if last_id_str.startswith("ORD"):
            try:
                num = int(last_id_str[3:]) + 1
                next_order_id = f"ORD{num:03d}"
            except ValueError:
                next_order_id = "ORD006"

    return render_template(
        "order_new.html",
        customers=customers,
        products=products,
        today=date.today().isoformat(),
        next_order_id=next_order_id
    )

@app.route("/orders/delete/<order_id>", methods=["POST"])
@login_required
def order_delete(order_id):
    db = get_db()
    # 刪除訂單（因設定 ON DELETE CASCADE，order_item 會自動連帶刪除）
    db.execute("DELETE FROM orders WHERE order_id = ?;", (order_id,))
    db.commit()
    flash(f"已刪除訂單 {order_id}！", "info")
    return redirect(url_for("orders_list"))

# ==========================================
# 專屬訂單頁面與出貨單 QRCode (Feature 9)
# ==========================================
@app.route("/order/<order_id>")
def order_detail(order_id):
    """
    每張訂單的專屬頁面 /order/<訂單編號>，展示出貨單並產生 QRCode。
    (任何人透過出貨單 QRCode 掃描皆可檢視出貨單內容)
    """
    db = get_db()
    order = db.execute("SELECT * FROM orders WHERE order_id = ?;", (order_id,)).fetchone()
    if not order:
        flash(f"查無訂單編號 {order_id}！", "danger")
        return redirect(url_for("orders_list"))

    customer = db.execute("SELECT * FROM customer WHERE customer_id = ?;", (order["customer_id"],)).fetchone()

    # 查詢訂單明細，同時撈取商品目前定價，展示歷史價格比對 (Feature 7)
    items = db.execute("""
        SELECT 
            oi.product_id,
            p.name AS product_name,
            p.category,
            oi.quantity,
            oi.unit_price,
            p.price AS current_price
        FROM order_item oi
        JOIN product p ON oi.product_id = p.product_id
        WHERE oi.order_id = ?
        ORDER BY oi.product_id;
    """, (order_id,)).fetchall()

    total_amount = sum(item["unit_price"] * item["quantity"] for item in items)
    total_quantity = sum(item["quantity"] for item in items)

    return render_template(
        "order_detail.html",
        order=order,
        customer=customer,
        items=items,
        total_amount=total_amount,
        total_quantity=total_quantity
    )

# ==========================================
# 應用程式啟動點
# ==========================================
if __name__ == "__main__":
    # 確保資料庫在伺服器啟動前已建立
    if not os.path.exists(DB_PATH):
        init_database(DB_PATH)

    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1")
    print(f"\n==================================================")
    print(f"  Python Flask 訂單管理系統已啟動！")
    print(f"  本地預覽網址: http://127.0.0.1:{port}")
    print(f"  預設管理員帳號: admin")
    print(f"  預設管理員密碼: admin123")
    print(f"==================================================\n")
    app.run(host="0.0.0.0", port=port, debug=debug)
