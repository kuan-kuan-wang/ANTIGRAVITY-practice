import os
from flask import Flask, render_template, jsonify

app = Flask(__name__)

@app.route("/")
def index():
    is_cloud = "RENDER" in os.environ
    return render_template(
        "index.html",
        title="Hello, World!",
        message="歡迎來到 Python Flask 單頁式網站！",
        is_cloud=is_cloud
    )

@app.route("/health")
def health():
    return jsonify(
        status="healthy",
        environment="Render Cloud" if "RENDER" in os.environ else "Local Development"
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "True").lower() in ("true", "1")
    app.run(host="0.0.0.0", port=port, debug=debug)
