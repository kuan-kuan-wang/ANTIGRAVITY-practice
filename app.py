from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html", title="Hello, World!", message="歡迎來到 Python Flask 單頁式網站！")

if __name__ == "__main__":
    # debug=True 會在程式碼修改時自動重啟伺服器，並提供詳細除錯訊息
    app.run(host="127.0.0.1", port=5000, debug=True)
