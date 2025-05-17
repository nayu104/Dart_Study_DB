from flask import Flask, redirect, request
import psycopg2
import os
from dotenv import load_dotenv #envファイル読み込み用
import requests 

load_dotenv()#.envファイル読み込み

#環境変数の取得,ここでいうクライアントはここのアプリケーションのこと
CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")       # GitHub OAuthアプリのID
CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET") # GitHub OAuthアプリの秘密鍵
DB_URL = os.getenv("DB_URL")                    # クラウドDBへ接続するためのURL（接続情報）


app = Flask(__name__)

@app.route("/")
def index():
    return "Flask起動中"

@app.route("")

@app.route("/login/github")
def github_login():
    github_login_url = f"https://github.com/login/oauth/authorize?client_id={CLIENT_ID}"
    return redirect(github_login_url)#redirectはそのURLに飛ばすための関数


#本人確認書類＆チケット引き換え
@app.route("/callback/github")
def github_callback():
    code = request.args.get("code")#ユーザーが許可するとGitHubから一時codeが返ってくる

    token_res = requests.post(
        "https://github.com/login/oauth/access_token",
        headers={"Accept":"application/json"},#githubさんに「jsonで返して」とパワハラしてる。まあ辞書型で記述したいからねえ
        data={#GitHubに送る確認書類
            "client_id": CLIENT_ID,#GitHub OAuth AppのID（名前）
            "client_secret":CLIENT_SECRET,#GitHub OAuth Appの秘密鍵（サイン）
            "code": code,#一時code
        }
    )

    token_json = token_res.json()#json形式にする
    access_token = token_json.get("access_token")#確認書類の受け取り窓口

    #GitHubのAPIを叩いて、ユーザー情報を取得する
    user_res = requests.get(
    "https://api.github.com/user",#logn=name,id,avatar_urlなど入ってる
        headers={"Authorization":f"Bearer {access_token}"} # ← GitHubが「こうして」と決めた書き方、というか標準的な記述
    )
    user_data = user_res.json()#ここでlogin=nameとかもらってる
    print(user_data)#エラー解析

    if "id" not in user_data:
        print("⚠ GitHub API 認証失敗: ", user_data)
        return "GitHub 認証に失敗しました", 401

    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        conn.close()
        print("〇DB接続OK")
    except Exception as e:
        print("✖DB接続失敗:", e)

    
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO users (github_id,user_name,avatar_url)
        VALUES(%s,%s,%s)
        ON CONFLICT (github_id) DO UPDATE
        SET user_name = EXCLUDED.user_name,
        avatar_url = EXCLUDED.avatar_url
    """,(
        user_data["id"],
        user_data["login"],
        user_data["avatar_url"]
    ))

    from urllib.parse import urlencode#URLに文字列を安全に含ませるためのモジュール
    flutter_url = "techcircle://login_success" 
    query = urlencode({
        "id": user_data["id"],
        "name": user_data["login"],
        "avatar": user_data["avatar_url"]
    })
    return redirect(f"{flutter_url}?{query}")#追加データ（クエリパラメーター）をURLに付与

if __name__ == "__main__":
    app.run(debug=True)