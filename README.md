# ANTIGRAVITY-practice (Flask 訂單管理系統)

這是一個使用 **Python Flask**、**SQLite** 與 **Bootstrap 5** 建構的全功能訂單管理系統，具備 GitHub Actions CI/CD 自動化測試與 Render 雲端部署能力。

---

## 🌟 系統核心功能

1. **資料庫關聯設計 (`orders.db`)**：
   - `customer`：客戶編號 (PK)、名稱、電話、地址、建檔日期
   - `product`：商品編號 (PK)、名稱、單價、庫存、分類（CHECK 約束：單價與庫存不可為負）
   - `orders`：訂單編號 (PK)、客戶編號 (FK)、訂單日期、狀態、業務人員
   - `order_item`：訂單編號 (FK)、商品編號 (FK)、數量、單價（複合主鍵：訂單編號 + 商品編號，CHECK 約束：數量 > 0、單價 >= 0）
2. **管理員權限保護**：
   - 內建管理員帳號驗證與 Session 機制，登入後可維護客戶、商品與訂單。
3. **多品項商品下單**：
   - 新增訂單採客戶下拉選單。
   - 支援一次勾選多項商品並自訂各品項數量，內建即時前端試算。
4. **歷史單價快照保護**：
   - `order_item` 儲存下單當時的成交單價。後續商品改價或特價調整，既有歷史訂單單價與金額完全不受影響。
5. **訂單狀態即時更新**：
   - 訂單列表頁面支援直接切換「處理中 / 已出貨 / 已完成 / 已取消」，即時更新狀態與標籤色彩。
6. **專屬頁面與出貨單 QRCode**：
   - 每張訂單具備獨立網址 `/order/<訂單編號>`，呈現出貨單格式並動態生成 QRCode，支援一鍵友善列印。

---

## 🚀 快速啟動 (本地端)

### 1. 安裝相依套件
```bash
pip install -r requirements.txt
```

### 2. 資料庫初始化與驗證 (選用)
資料庫已預載 5 筆繁體中文測試資料，亦可隨時執行重建或驗證：
```bash
# 重建資料庫並注入測試資料
python create_db.py

# 驗證資料庫內容與約束條件
python check_db.py
```

### 3. 啟動應用程式
```bash
python app.py
```

### 4. 開啟瀏覽器檢視
開啟瀏覽器前往 [http://127.0.0.1:5000](http://127.0.0.1:5000)

* **預設管理員帳號**：`admin`
* **預設管理員密碼**：`admin123`

### 5. 執行自動化測試
```bash
python -m pytest
```

---

## 📁 專案結構

```text
ANTIGRAVITY練習/
├── .github/
│   └── workflows/
│       └── cicd.yml           # GitHub Actions CI/CD 流程設定
├── static/
│   └── js/
│       └── qrcode.min.js      # 出貨單 QRCode 離線前端函式庫
├── templates/
│   ├── base.html              # Bootstrap 5 通用母版
│   ├── index.html             # 首頁儀表板與統計
│   ├── login.html             # 管理員登入
│   ├── customers.html         # 客戶管理 (CRUD)
│   ├── products.html          # 商品管理 (CRUD)
│   ├── orders.html            # 訂單管理與狀態即時更新
│   ├── order_new.html         # 新增訂單 (多選與下拉)
│   └── order_detail.html      # 專屬出貨單與 QRCode
├── tests/
│   ├── test_app.py            # 基礎路由單元測試
│   └── test_order_system.py   # 訂單系統完整功能測試
├── app.py                     # Flask 後端主程式
├── create_db.py               # 資料庫建立與測試資料寫入腳本
├── check_db.py                # 資料庫格式化檢驗腳本
├── orders.db                  # SQLite 資料庫檔案
├── requirements.txt           # Python 相依套件清單
├── render.yaml                # Render 雲端部署設定
└── .gitignore                 # Git 忽略清單
```

---

## 🔄 CI/CD 流程說明

每次推送到 `main` 分支時，GitHub Actions 會自動執行：
1. **CI 測試階段**：自動配置 Python 3.11 環境、安裝套件、檢查語法編譯與執行 `pytest` 測試（8 項測試）。
2. **CD 部署階段**：測試成功後，自動觸發 Render Deploy Hook 完成即時部署。
