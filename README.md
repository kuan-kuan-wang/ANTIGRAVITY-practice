# ANTIGRAVITY-practice (Flask 單頁式 Web 應用程式)

這是一個使用 Python Flask 框架建構的單頁式 Web 應用程式，具備 GitHub Actions CI/CD 自動化測試與 Render 雲端部署能力。

## 專案結構

```
ANTIGRAVITY練習/
├── .github/
│   └── workflows/
│       └── cicd.yml     # GitHub Actions CI/CD 流程設定
├── tests/
│   └── test_app.py      # 自動化單元測試
├── templates/
│   └── index.html       # 前端頁面範本
├── app.py               # Flask 後端主程式
├── requirements.txt     # Python 相依套件清單 (Flask, gunicorn, pytest)
├── render.yaml          # Render 雲端部署設定 (Blueprint)
└── .gitignore           # Git 忽略檔案清單
```

## 快速啟動 (本地端)

1. **安裝相依套件**：
   ```bash
   pip install -r requirements.txt
   ```

2. **執行應用程式**：
   ```bash
   python app.py
   ```

3. **在瀏覽器中預覽**：
   開啟瀏覽器並前往 [http://127.0.0.1:5000](http://127.0.0.1:5000)

4. **執行測試**：
   ```bash
   python -m pytest
   ```

## CI/CD 流程說明

每次推送到 `main` 分支時，GitHub Actions 會自動執行：
1. **CI 測試階段**：自動配置 Python 3.11 環境、安裝套件、編譯檢查與執行 `pytest` 單元測試。
2. **CD 部署階段**：測試成功後，自動觸發 Render 的 Deploy Hook 完成即時部署。
