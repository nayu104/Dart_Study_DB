from flask import Flask, redirect
import psycopg2
import os
from dotenv import load_dotenv #envファイル読み込み用

load_dotenv()#.envファイル読み込み

#環境変数の取得,ここでいうクライアントはここのアプリケーションのこと
CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")       # GitHub OAuthアプリのID
CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET") # GitHub OAuthアプリの秘密鍵
DB_URL = os.getenv("DB_URL")                    # クラウドDBへ接続するためのURL（接続情報）


app = Flask(__name__)

@app.route("/login/github")
def github_login():
    github_login_url = f"https://github.com/login/oauth/authorize?client_id={CLIENT_ID}"
    return redirect(github_login_url)


#本人確認書類＆チケット引き換え
@app.route("/callback/github")
def github_callback():
    code = request.args.get("code")#Gユーザーが許可するとGitHubから一時codeが返ってくる

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
        headers={"Authorization":f"Bearer{access_token}"} # ← GitHubが「こうして」と決めた書き方、というか標準的な記述
    )
    user_data = user_res.json()#ここでlogin=nameとかもらってる

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

    return f"""
    ようこそ {user_data['login']} さん！<br>
    あなたのGitHub IDは {user_data['id']} です。<br>
    <img src="{user_data['avatar_url']}" width="100">
    """



if __name__ == "__main__":
    app.run(debug=True)
