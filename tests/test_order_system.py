import pytest
import sqlite3
from app import app, get_db

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret-key"
    with app.test_client() as client:
        yield client

def login_as_admin(client):
    return client.post("/login", data={
        "username": "admin",
        "password": "admin123"
    }, follow_redirects=True)

def test_admin_login_and_logout(client):
    # 測試正確帳密登入
    res = login_as_admin(client)
    assert res.status_code == 200
    assert "歡迎回來".encode("utf-8") in res.data or "系統管理員".encode("utf-8") in res.data

    # 測試登出
    res_logout = client.get("/logout", follow_redirects=True)
    assert res_logout.status_code == 200
    assert "您已安全登出系統".encode("utf-8") in res_logout.data

def test_unauthorized_access(client):
    # 未登入存取受保護端點應被導向登入頁
    res = client.get("/customers", follow_redirects=True)
    assert res.status_code == 200
    assert "管理員登入".encode("utf-8") in res.data

def test_customer_crud(client):
    login_as_admin(client)
    
    # 測試新增客戶
    res_add = client.post("/customers/add", data={
        "customer_id": "C999",
        "name": "測試客戶科技",
        "phone": "0912-345678",
        "address": "新竹市科學園區研發一路1號"
    }, follow_redirects=True)
    assert res_add.status_code == 200
    assert "測試客戶科技".encode("utf-8") in res_add.data

    # 測試編輯客戶
    res_edit = client.post("/customers/edit/C999", data={
        "name": "測試客戶科技(已更新)",
        "phone": "0988-765432",
        "address": "新竹市東區光復路二段100號"
    }, follow_redirects=True)
    assert res_edit.status_code == 200
    assert "測試客戶科技(已更新)".encode("utf-8") in res_edit.data

    # 測試刪除客戶
    res_del = client.post("/customers/delete/C999", follow_redirects=True)
    assert res_del.status_code == 200
    assert "已刪除客戶 C999".encode("utf-8") in res_del.data

def test_product_crud_and_price_protection(client):
    login_as_admin(client)

    # 測試新增商品
    res_add = client.post("/products/add", data={
        "product_id": "P999",
        "name": "多功能測試儀表",
        "category": "測試器材",
        "price": "5000",
        "stock": "20"
    }, follow_redirects=True)
    assert res_add.status_code == 200
    assert "多功能測試儀表".encode("utf-8") in res_add.data

    # 測試多項商品下單 (Requirement 6 & 7)
    res_order = client.post("/orders/new", data={
        "order_id": "ORD999",
        "customer_id": "C001",
        "order_date": "2026-10-06",
        "salesperson": "測試業務",
        "status": "處理中",
        "selected_products": ["P999"],
        "qty_P999": "2"
    }, follow_redirects=True)
    assert res_order.status_code == 200
    assert "ORD999".encode("utf-8") in res_order.data

    # 測試商品改價 (Requirement 7: 商品改價不影響歷史訂單)
    client.post("/products/edit/P999", data={
        "name": "多功能測試儀表",
        "category": "測試器材",
        "price": "9999",  # 定價調漲為 9999
        "stock": "18"
    }, follow_redirects=True)

    # 檢查專屬訂單頁面中的下單單價依然為 5000 (歷史單價保存)
    res_detail = client.get("/order/ORD999")
    assert res_detail.status_code == 200
    assert "5,000".encode("utf-8") in res_detail.data
    assert "10,000".encode("utf-8") in res_detail.data  # 2 * 5000 = 10000

    # 清理測試訂單與商品
    client.post("/orders/delete/ORD999", follow_redirects=True)
    client.post("/products/delete/P999", follow_redirects=True)

def test_order_status_direct_update(client):
    login_as_admin(client)
    # 測試列表直接更新訂單狀態 (Requirement 8)
    res = client.post("/orders/status/ORD003", data={
        "status": "已出貨"
    }, follow_redirects=True)
    assert res.status_code == 200
    assert "狀態已直接更新為「已出貨」".encode("utf-8") in res.data

def test_order_detail_page_and_qrcode(client):
    # 測試專屬頁面 /order/<訂單編號> (Requirement 9)
    res = client.get("/order/ORD001")
    assert res.status_code == 200
    assert "出貨單".encode("utf-8") in res.data
    assert "ORD001".encode("utf-8") in res.data
    assert "qrcode".encode("utf-8") in res.data
    assert "台積電科技".encode("utf-8") in res.data
