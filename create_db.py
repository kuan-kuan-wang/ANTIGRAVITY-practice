"""
create_db.py - 初始化 orders.db 資料庫結構與 5 筆繁體中文測試資料
"""

import sqlite3
import os
import sys
from werkzeug.security import generate_password_hash

# 確保在 Windows 環境下命令列輸出中文字元編碼正常
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

DB_NAME = "orders.db"

def init_database(db_path=DB_NAME):
    """建立四張核心資料表與管理員表，並插入 5 筆繁體中文測試資料"""
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"[*] 移除舊的資料庫檔案: {db_path}")

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 啟用 SQLite 外鍵約束
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. customer: 客戶資料表
    cursor.execute("""
    CREATE TABLE customer (
        customer_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        phone TEXT,
        address TEXT,
        created_date TEXT NOT NULL DEFAULT (date('now'))
    );
    """)

    # 2. product: 商品資料表 (單價與庫存不可為負)
    cursor.execute("""
    CREATE TABLE product (
        product_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        price REAL NOT NULL CHECK (price >= 0),
        stock INTEGER NOT NULL CHECK (stock >= 0),
        category TEXT NOT NULL
    );
    """)

    # 3. orders: 訂單資料表
    cursor.execute("""
    CREATE TABLE orders (
        order_id TEXT PRIMARY KEY,
        customer_id TEXT NOT NULL,
        order_date TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('處理中', '已出貨', '已完成', '已取消')),
        salesperson TEXT NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES customer (customer_id)
            ON UPDATE CASCADE
            ON DELETE RESTRICT
    );
    """)

    # 4. order_item: 訂單明細表 (複合主鍵: order_id + product_id, 數量 > 0, 單價 >= 0)
    cursor.execute("""
    CREATE TABLE order_item (
        order_id TEXT NOT NULL,
        product_id TEXT NOT NULL,
        quantity INTEGER NOT NULL CHECK (quantity > 0),
        unit_price REAL NOT NULL CHECK (unit_price >= 0),
        PRIMARY KEY (order_id, product_id),
        FOREIGN KEY (order_id) REFERENCES orders (order_id)
            ON UPDATE CASCADE
            ON DELETE CASCADE,
        FOREIGN KEY (product_id) REFERENCES product (product_id)
            ON UPDATE CASCADE
            ON DELETE RESTRICT
    );
    """)

    # 5. admin_user: 管理員帳號表
    cursor.execute("""
    CREATE TABLE admin_user (
        username TEXT PRIMARY KEY,
        password_hash TEXT NOT NULL,
        display_name TEXT NOT NULL
    );
    """)

    # ==========================
    # 插入測試資料 (繁體中文)
    # ==========================

    # 管理員帳號 (admin / admin123)
    admin_pw_hash = generate_password_hash("admin123")
    cursor.execute("""
    INSERT INTO admin_user (username, password_hash, display_name)
    VALUES ('admin', ?, '系統管理員');
    """, (admin_pw_hash,))

    # 1. customer: 5 筆
    customers = [
        ("C001", "台積電科技股份有限公司", "03-5781688", "新竹市科學園區力行六路8號", "2026-01-15"),
        ("C002", "聯發科技股份有限公司", "03-5670766", "新竹市科學園區篤行一路1號", "2026-01-20"),
        ("C003", "鴻海精密工業股份有限公司", "02-22683466", "新北市土城區自由街2號", "2026-02-10"),
        ("C004", "華碩電腦股份有限公司", "02-28943447", "台北市北投區立德路15號", "2026-02-18"),
        ("C005", "廣達電腦股份有限公司", "03-3272345", "桃園市龜山區文化二路188號", "2026-03-01"),
    ]
    cursor.executemany("""
    INSERT INTO customer (customer_id, name, phone, address, created_date)
    VALUES (?, ?, ?, ?, ?);
    """, customers)

    # 2. product: 5 筆
    products = [
        ("P001", "人體工學高階辦公椅", 8500.0, 45, "辦公家具"),
        ("P002", "機械式電競鍵盤 (青軸)", 2800.0, 120, "電腦周邊"),
        ("P003", "4K 專業曲面顯示器 32吋", 12500.0, 30, "顯示設備"),
        ("P004", "人體工學垂直無線滑鼠", 1680.0, 85, "電腦周邊"),
        ("P005", "無線主動降噪藍牙耳機", 4200.0, 60, "影音周邊"),
    ]
    cursor.executemany("""
    INSERT INTO product (product_id, name, price, stock, category)
    VALUES (?, ?, ?, ?, ?);
    """, products)

    # 3. orders: 5 筆 (狀態包含：已完成、已出貨、處理中、已取消)
    orders_data = [
        ("ORD001", "C001", "2026-09-15", "已完成", "陳大明"),
        ("ORD002", "C002", "2026-09-20", "已出貨", "林美麗"),
        ("ORD003", "C003", "2026-10-01", "處理中", "王小華"),
        ("ORD004", "C004", "2026-10-03", "處理中", "張志豪"),
        ("ORD005", "C005", "2026-10-06", "已取消", "陳大明"),
    ]
    cursor.executemany("""
    INSERT INTO orders (order_id, customer_id, order_date, status, salesperson)
    VALUES (?, ?, ?, ?, ?);
    """, orders_data)

    # 4. order_item:
    # ORD001 包含多項商品 (P001, P002)
    # ORD002 包含多項商品 (P003, P004)
    # unit_price 記錄下單當時單價（例如 P001 當時優惠價 8200，目前定價 8500）
    order_items = [
        ("ORD001", "P001", 2, 8200.0),   # ORD001 項 1 (下單優惠價 8200 vs 現價 8500)
        ("ORD001", "P002", 1, 2800.0),   # ORD001 項 2 (多品項案例)
        ("ORD002", "P003", 1, 11900.0),  # ORD002 項 1 (下單特惠價 11900 vs 現價 12500)
        ("ORD002", "P004", 2, 1680.0),   # ORD002 項 2 (多品項案例)
        ("ORD003", "P004", 3, 1680.0),   # ORD003
        ("ORD004", "P005", 2, 3990.0),   # ORD004 (早鳥價 3990 vs 現價 4200)
        ("ORD005", "P001", 1, 8500.0),   # ORD005
    ]
    cursor.executemany("""
    INSERT INTO order_item (order_id, product_id, quantity, unit_price)
    VALUES (?, ?, ?, ?);
    """, order_items)

    conn.commit()
    conn.close()

    print(f"[OK] 成功建立資料庫 '{db_path}' 並插入測試資料：")
    print(f"    - 管理員帳號: admin (密碼: admin123)")
    print(f"    - customer:   {len(customers)} 筆")
    print(f"    - product:    {len(products)} 筆")
    print(f"    - orders:     {len(orders_data)} 筆")
    print(f"    - order_item: {len(order_items)} 筆")

if __name__ == "__main__":
    init_database()
