"""
check_db.py - 驗證 orders.db 資料庫內容與結構

功能：
1. 依序讀取並美化印出四張資料表內容：customer、product、orders、order_item
2. 執行多表 JOIN 綜合查詢，驗證：
   - 訂單與明細關聯
   - 包含多項商品的訂單（如 ORD001）
   - 「下單當時單價」與「現行商品定價」的歷史價格保存比對
3. 執行 CHECK 約束與複合主鍵自我檢驗測試，確認資料庫防呆機制生效
"""

import sqlite3
import os
import sys
import unicodedata

# 確保在 Windows 環境下命令列輸出中文字元編碼正常
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

DB_PATH = "orders.db"


def get_display_width(val):
    """計算字串於終端機顯示的實際寬度（處理全形/半形字元差異）"""
    text = str(val)
    width = 0
    for ch in text:
        if unicodedata.east_asian_width(ch) in ('F', 'W'):
            width += 2
        else:
            width += 1
    return width


def pad_text(val, target_width, align='left'):
    """依顯示寬度對齊字串"""
    text = str(val)
    cur_w = get_display_width(text)
    pad_len = max(0, target_width - cur_w)
    if align == 'right':
        return ' ' * pad_len + text
    elif align == 'center':
        left = pad_len // 2
        right = pad_len - left
        return ' ' * left + text + ' ' * right
    else:
        return text + ' ' * pad_len


def print_table(title, headers, rows, col_align=None):
    """美化印出單一資料表"""
    print(f"\n{'=' * 78}")
    print(f"【{title}】 (共 {len(rows)} 筆資料)")
    print(f"{'=' * 78}")

    if not rows:
        print(" (資料表目前無資料)")
        return

    num_cols = len(headers)
    if col_align is None:
        col_align = ['left'] * num_cols

    # 計算各欄位所需最大寬度
    col_widths = [get_display_width(h) for h in headers]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], get_display_width(val))

    # 加上內距邊界
    col_widths = [w + 2 for w in col_widths]

    # 表頭
    header_line = "|" + "|".join(pad_text(f" {h} ", col_widths[i], 'center') for i, h in enumerate(headers)) + "|"
    sep_line = "+" + "+".join("-" * col_widths[i] for i in range(num_cols)) + "+"

    print(sep_line)
    print(header_line)
    print(sep_line)

    for row in rows:
        row_line = "|" + "|".join(pad_text(f" {row[i]} ", col_widths[i], col_align[i]) for i in range(num_cols)) + "|"
        print(row_line)

    print(sep_line)


def inspect_database(db_path=DB_PATH):
    """檢查並輸出資料庫所有表格內容"""
    if not os.path.exists(db_path):
        print(f"[錯誤] 找不到資料庫檔案 '{db_path}'，請先執行 create_db.py 建立！")
        return False

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    # 1. 查詢 customer
    cursor.execute("SELECT customer_id, name, phone, address, created_date FROM customer;")
    customers = cursor.fetchall()
    print_table(
        "1. customer 客戶資料表",
        ["客戶編號 (PK)", "客戶名稱", "電話", "地址", "建檔日期"],
        customers,
        col_align=['center', 'left', 'left', 'left', 'center']
    )

    # 2. 查詢 product
    cursor.execute("SELECT product_id, name, printf('NT$ %,d', CAST(price AS INT)), stock, category FROM product;")
    products = cursor.fetchall()
    print_table(
        "2. product 商品資料表 (CHECK: 單價 >= 0, 庫存 >= 0)",
        ["商品編號 (PK)", "商品名稱", "現行單價", "庫存", "分類"],
        products,
        col_align=['center', 'left', 'right', 'right', 'left']
    )

    # 3. 查詢 orders
    cursor.execute("SELECT order_id, customer_id, order_date, status, salesperson FROM orders;")
    orders = cursor.fetchall()
    print_table(
        "3. orders 訂單資料表",
        ["訂單編號 (PK)", "客戶編號 (FK)", "訂單日期", "狀態", "業務人員"],
        orders,
        col_align=['center', 'center', 'center', 'center', 'left']
    )

    # 4. 查詢 order_item
    cursor.execute("SELECT order_id, product_id, quantity, printf('NT$ %,d', CAST(unit_price AS INT)) FROM order_item;")
    order_items = cursor.fetchall()
    print_table(
        "4. order_item 訂單明細表 (複合主鍵: 訂單+商品, CHECK: 數量 > 0, 單價 >= 0)",
        ["訂單編號 (FK)", "商品編號 (FK)", "數量", "下單當時單價"],
        order_items,
        col_align=['center', 'center', 'right', 'right']
    )

    # 5. 多表 JOIN 綜合明細報表 (驗證多項商品與歷史價格保存)
    cursor.execute("""
    SELECT 
        o.order_id,
        c.name AS customer_name,
        o.order_date,
        o.status,
        p.name AS product_name,
        oi.quantity,
        printf('NT$ %,d', CAST(oi.unit_price AS INT)) AS history_price,
        printf('NT$ %,d', CAST(p.price AS INT)) AS current_price,
        printf('NT$ %,d', CAST((oi.quantity * oi.unit_price) AS INT)) AS subtotal,
        CASE 
            WHEN oi.unit_price < p.price THEN '★ 歷史優惠價 (低於現價)'
            WHEN oi.unit_price > p.price THEN '▲ 歷史高價'
            ELSE '一般售價'
        END AS price_note
    FROM orders o
    JOIN customer c ON o.customer_id = c.customer_id
    LEFT JOIN order_item oi ON o.order_id = oi.order_id
    LEFT JOIN product p ON oi.product_id = p.product_id
    ORDER BY o.order_id, oi.product_id;
    """)
    join_rows = cursor.fetchall()

    # 處理可能沒有明細的訂單（如草稿單）
    formatted_join_rows = []
    for r in join_rows:
        row_list = list(r)
        if row_list[4] is None:
            row_list[4] = "(尚未加入商品)"
            row_list[5] = "-"
            row_list[6] = "-"
            row_list[7] = "-"
            row_list[8] = "-"
            row_list[9] = "草稿/新建立"
        formatted_join_rows.append(row_list)

    print_table(
        "綜合驗證報表：訂單與商品關聯明細 (含多項商品與歷史價格比對)",
        ["訂單編號", "客戶名稱", "訂單日期", "狀態", "購買商品", "數量", "下單單價", "現行定價", "小計", "備註說明"],
        formatted_join_rows,
        col_align=['center', 'left', 'center', 'center', 'left', 'right', 'right', 'right', 'right', 'left']
    )

    # 6. 訂單匯總統計（驗證訂單是否含多項商品）
    cursor.execute("""
    SELECT 
        o.order_id,
        c.name,
        COUNT(oi.product_id) AS item_count,
        COALESCE(printf('NT$ %,d', CAST(SUM(oi.quantity * oi.unit_price) AS INT)), 'NT$ 0') AS total_amount,
        CASE 
            WHEN COUNT(oi.product_id) > 1 THEN '★ 包含多項商品 (符合要求)'
            WHEN COUNT(oi.product_id) = 1 THEN '單一商品'
            ELSE '無品項 (草稿單)'
        END AS case_check
    FROM orders o
    JOIN customer c ON o.customer_id = c.customer_id
    LEFT JOIN order_item oi ON o.order_id = oi.order_id
    GROUP BY o.order_id, c.name
    ORDER BY o.order_id;
    """)
    summary_rows = cursor.fetchall()
    print_table(
        "訂單多品項案例驗證與總額匯總",
        ["訂單編號", "客戶名稱", "商品品項數", "訂單總金額", "多項商品案例判定"],
        summary_rows,
        col_align=['center', 'left', 'right', 'right', 'left']
    )

    conn.close()
    return True


def verify_constraints(db_path=DB_PATH):
    """驗證 CHECK 約束與複合主鍵是否正常生效"""
    print(f"\n{'=' * 78}")
    print("【資料庫完整性與約束條件 (CHECK / PK / FK) 自我測試】")
    print(f"{'=' * 78}")

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON;")
    cursor = conn.cursor()

    tests = [
        (
            "測試 1：order_item 數量 <= 0 CHECK 約束",
            "INSERT INTO order_item (order_id, product_id, quantity, unit_price) VALUES ('ORD001', 'P004', 0, 100);",
            "quantity > 0 約束成功阻擋 quantity=0"
        ),
        (
            "測試 2：order_item 數量為負數 CHECK 約束",
            "INSERT INTO order_item (order_id, product_id, quantity, unit_price) VALUES ('ORD001', 'P004', -2, 100);",
            "quantity > 0 約束成功阻擋負數數量"
        ),
        (
            "測試 3：order_item 單價為負數 CHECK 約束",
            "INSERT INTO order_item (order_id, product_id, quantity, unit_price) VALUES ('ORD001', 'P004', 1, -500);",
            "unit_price >= 0 約束成功阻擋負數單價"
        ),
        (
            "測試 4：product 單價為負數 CHECK 約束",
            "INSERT INTO product (product_id, name, price, stock, category) VALUES ('P999', '非法商品', -10, 5, '測試');",
            "price >= 0 約束成功阻擋負數商品單價"
        ),
        (
            "測試 5：order_item (order_id, product_id) 複合主鍵重複阻擋",
            "INSERT INTO order_item (order_id, product_id, quantity, unit_price) VALUES ('ORD001', 'P001', 1, 8500);",
            "複合主鍵 (ORD001, P001) 成功阻擋重複插入"
        ),
    ]

    all_passed = True
    for name, sql, expected_msg in tests:
        try:
            cursor.execute(sql)
            conn.commit()
            print(f"[FAIL] {name}: 期望拋出 IntegrityError 但成功插入（約束未生效）！")
            all_passed = False
        except sqlite3.IntegrityError as e:
            print(f"[PASS] {name} -> 成功攔截: {expected_msg} ({type(e).__name__})")

    conn.rollback()
    conn.close()

    if all_passed:
        print("\n[OK] 所有 CHECK 約束與複合主鍵保護機制皆通過驗證！")
    else:
        print("\n[WARN] 部分約束測試未通過，請檢查 DDL 定義！")


if __name__ == "__main__":
    print("\n" + "=" * 78)
    print("      orders.db SQLite 資料庫內容檢視與驗證程式 (check_db.py)")
    print("=" * 78)
    if inspect_database():
        verify_constraints()
