import streamlit as st
import openai
import os
import json
import tkinter as tk
from tkinter import filedialog
from datetime import datetime
import tempfile
import base64
from pathlib import Path
from dotenv import load_dotenv
import markdown
import webbrowser

# 環境変数のロード（.envファイルから）
load_dotenv()

# ページ設定
st.set_page_config(page_title="技術アドバイザーBot", page_icon="👨‍💻", layout="wide")

# API設定
# 環境変数からAPIキーを取得（.envファイルまたはシステム環境変数から）
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# APIキーが環境変数にない場合は直接入力してもらう
if not OPENAI_API_KEY:
    # セッション状態にAPIキーが保存されていればそれを使用
    if "api_key" in st.session_state and st.session_state.api_key:
        OPENAI_API_KEY = st.session_state.api_key
    else:
        # サイドバーでAPIキーの入力を促す
        with st.sidebar:
            st.write("## OpenAI APIキー設定")
            api_key = st.text_input(
                "OpenAI APIキーを入力してください:", type="password"
            )
            if api_key:
                st.session_state.api_key = api_key
                OPENAI_API_KEY = api_key
                st.success("APIキーが設定されました！")

                # APIキーを.envファイルに保存するオプション
                save_to_env = st.checkbox("APIキーを.envファイルに保存する")
                if save_to_env:
                    try:
                        with open(".env", "w") as f:
                            f.write(f"OPENAI_API_KEY={api_key}")
                        st.success(".envファイルにAPIキーを保存しました。")
                    except Exception as e:
                        st.error(f".envファイルへの保存に失敗しました: {str(e)}")
            else:
                st.warning(
                    "APIキーを入力してください。キーはあなたのコンピュータにのみ保存され、サーバーには送信されません。"
                )
                # APIキーがない場合は早期リターン
                st.stop()

# OpenAI APIの設定
openai.api_key = OPENAI_API_KEY

# システムプロンプト定義
SYSTEM_PROMPT = """
あなたはDjango、Vue.js、Python、HTML、CSSの専門家で、優れた知識と説明能力を持っています。
新人エンジニアにステップバイステップで丁寧にレッスンを提供してください。
質問に対して、評価の高い技術記事や公式記事を参考に教えてください。

生徒に指導する際は、以下の構造で回答してください：
1. 題名（マークダウンの # で表現）
2. 見出し（マークダウンの ## で表現）
3. サブ見出し（マークダウンの ### で表現）
4. システム構成図（必要な場合）
5. コードサンプル（各行に詳細なコメントを必ず記載）

生徒の要望に合わせてDjango、Vue.js、Python、HTML、CSSの開発の助言、スキル上達のためのアドバイスを行ってください。
あなたの役割は生徒の開発スピードと生産性を上げ、技術学習の速度を向上させることです。

以下のような技術と関係のないトピックについては、「申し訳ありませんが、技術的な質問に集中させていただいています。Django、Vue.js、Python、HTML、CSSについての質問があればお答えします。」と回答してください：
* 旅行
* 料理
* 芸能人
* 映画
* 科学
* 歴史
"""

# CSSスタイル
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        color: #4527A0;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #5E35B1;
        margin-bottom: 1rem;
    }
    .stTextInput>div>div>input {
        background-color: #f0f2f6;
    }
    .stChat {
        border-radius: 10px;
        padding: 20px;
    }
    .user-bubble {
        background-color: #E3F2FD;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
    }
    .bot-bubble {
        background-color: #F3E5F5;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
    }
    .chat-time {
        color: #9E9E9E;
        font-size: 0.75rem;
        text-align: right;
    }
    .code-block {
        background-color: #263238;
        color: #ECEFF1;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .sidebar .sidebar-content {
        background-color: #f8f9fa;
    }
    .export-section {
        background-color: #E8EAF6;
        padding: 15px;
        border-radius: 10px;
        margin-top: 20px;
    }
    .tech-tag {
        display: inline-block;
        background-color: #5C6BC0;
        color: white;
        padding: 3px 8px;
        border-radius: 10px;
        margin-right: 5px;
        font-size: 0.8rem;
    }
</style>
""",
    unsafe_allow_html=True,
)

# セッション状態の初期化
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "last_save_path" not in st.session_state:
    st.session_state.last_save_path = os.path.expanduser("~")


# チャット履歴やドキュメントをファイルに保存する関数（Tkinterダイアログ使用）
def save_to_file(content, default_filename, file_type="json"):
    """
    Tkinterを使用してファイル保存ダイアログを表示し、指定した場所にファイルを保存する関数

    Parameters:
    content (str): 保存するコンテンツ
    default_filename (str): デフォルトのファイル名
    file_type (str): ファイルの種類（json, md, html, txtなど）

    Returns:
    tuple: (成功したかどうか, 結果メッセージ)
    """
    try:
        # 一時ファイルにコンテンツを保存
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_type}") as tmp:
            tmp.write(content.encode("utf-8"))
            tmp_path = tmp.name

        # Tkinterのルートウィンドウを作成
        try:
            root = tk.Tk()
            root.withdraw()
        except:
            try:
                root = tk.Toplevel()
                root.withdraw()
            except:
                return False, "ファイルダイアログの表示に失敗しました。"

        # 前回の保存場所を初期ディレクトリとして使用
        initial_dir = st.session_state.last_save_path

        # ファイルの種類に応じたフィルターを設定
        filetypes = []
        if file_type == "json":
            filetypes = [("JSON ファイル", "*.json"), ("すべてのファイル", "*.*")]
        elif file_type == "md":
            filetypes = [("Markdown ファイル", "*.md"), ("すべてのファイル", "*.*")]
        elif file_type == "html":
            filetypes = [("HTML ファイル", "*.html"), ("すべてのファイル", "*.*")]
        elif file_type == "txt":
            filetypes = [("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")]

        # ファイル保存ダイアログを表示
        file_path = filedialog.asksaveasfilename(
            initialdir=initial_dir,
            initialfile=default_filename,
            defaultextension=f".{file_type}",
            filetypes=filetypes,
            title="ファイルを保存",
        )

        try:
            root.destroy()
        except:
            pass

        if file_path:
            # 保存先パスを記憶
            st.session_state.last_save_path = os.path.dirname(file_path)

            # 一時ファイルから保存先にコピー
            with open(tmp_path, "rb") as src_file:
                with open(file_path, "wb") as dst_file:
                    dst_file.write(src_file.read())

            # 一時ファイルを削除
            os.unlink(tmp_path)

            return True, file_path
        else:
            # 一時ファイルを削除
            os.unlink(tmp_path)
            return False, "ファイル保存がキャンセルされました。"

    except Exception as e:
        return False, f"エラーが発生しました: {str(e)}"


# チャット履歴をJSONとして保存する関数
def save_chat_history():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_filename = f"tech_chat_history_{timestamp}.json"

    # システムメッセージを除外
    chat_data = (
        st.session_state.messages[1:] if len(st.session_state.messages) > 1 else []
    )

    # JSONに変換
    json_content = json.dumps(chat_data, ensure_ascii=False, indent=2)

    # ファイル保存ダイアログを表示
    success, result = save_to_file(json_content, default_filename, "json")

    return success, result


# チャット履歴を読み込む関数
def load_chat_history(file):
    try:
        content = file.read().decode("utf-8")
        chat_data = json.loads(content)

        # システムメッセージを保持
        system_message = st.session_state.messages[0]
        st.session_state.messages = [system_message] + chat_data

        # チャット履歴も更新
        st.session_state.chat_history = []
        for msg in chat_data:
            if msg["role"] == "user":
                st.session_state.chat_history.append(("user", msg["content"]))
            elif msg["role"] == "assistant":
                st.session_state.chat_history.append(("assistant", msg["content"]))

        return True, "チャット履歴を読み込みました"
    except Exception as e:
        return False, f"エラー: {str(e)}"


# 最新の回答をドキュメントとして保存する関数
def save_latest_answer_as_document(format_type):
    if not st.session_state.chat_history:
        return False, "保存する回答がありません。"

    # 最新の回答を取得
    latest_answer = None
    for role, content in reversed(st.session_state.chat_history):
        if role == "assistant":
            latest_answer = content
            break

    if not latest_answer:
        return False, "保存する回答がありません。"

    # タイトルを抽出（マークダウンの# で始まる行）
    title = "技術ドキュメント"
    for line in latest_answer.split("\n"):
        if line.startswith("# "):
            title = line.replace("# ", "").strip()
            break

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_filename = f"{title.replace(' ', '_')}_{timestamp}"

    # フォーマットに応じて保存
    if format_type == "markdown":
        default_filename += ".md"
        return save_to_file(latest_answer, default_filename, "md")
    elif format_type == "html":
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; color: #333; }}
                h1 {{ color: #4527A0; border-bottom: 2px solid #4527A0; padding-bottom: 10px; }}
                h2 {{ color: #5E35B1; margin-top: 30px; }}
                h3 {{ color: #7E57C2; }}
                pre {{ background-color: #f5f5f5; padding: 15px; border-radius: 5px; overflow-x: auto; }}
                code {{ font-family: Consolas, Monaco, 'Andale Mono', monospace; }}
                .note {{ background-color: #E8EAF6; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .warning {{ background-color: #FFF8E1; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #FFC107; }}
                .code-comment {{ color: #6A8759; }}
                .timestamp {{ color: #9E9E9E; font-size: 0.8rem; text-align: right; margin-top: 50px; }}
            </style>
        </head>
        <body>
            {markdown.markdown(latest_answer)}
            <div class="timestamp">作成日時: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}</div>
        </body>
        </html>
        """
        default_filename += ".html"
        return save_to_file(html_content, default_filename, "html")
    elif format_type == "text":
        default_filename += ".txt"
        return save_to_file(latest_answer, default_filename, "txt")
    else:
        return False, "未対応のフォーマット形式です。"


# APIを使ってレスポンスを生成する関数
def generate_response(messages):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo", messages=messages, temperature=0.7, max_tokens=2000
        )
        return response.choices[0].message["content"]
    except Exception as e:
        return f"エラーが発生しました: {str(e)}"


# サイドバー
with st.sidebar:
    st.markdown("## 技術アドバイザーBot")
    st.markdown("Django、Vue.js、Python、HTML、CSSについて質問してください。")

    # チャット履歴の保存と読み込み
    st.markdown("## チャット履歴")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("履歴を保存"):
            success, result = save_chat_history()
            if success:
                st.success(f"保存しました: {result}")
            else:
                st.error(f"保存に失敗: {result}")

    with col2:
        if st.button("履歴をクリア"):
            st.session_state.messages = [
                st.session_state.messages[0]
            ]  # システムメッセージのみ残す
            st.session_state.chat_history = []
            st.success("履歴をクリアしました")

    uploaded_file = st.file_uploader("履歴を読み込む", type=["json"])
    if uploaded_file is not None:
        success, message = load_chat_history(uploaded_file)
        if success:
            st.success(message)
        else:
            st.error(message)

    # ドキュメント保存セクション
    st.markdown("## ドキュメント保存")
    st.markdown("最新の回答をドキュメントとして保存します。")

    format_type = st.radio(
        "保存形式を選択:",
        ["Markdown", "HTML", "プレーンテキスト"],
        index=0,
        key="format_type",
    )

    format_map = {"Markdown": "markdown", "HTML": "html", "プレーンテキスト": "text"}

    if st.button("回答をドキュメントとして保存"):
        format_value = format_map[format_type]
        success, result = save_latest_answer_as_document(format_value)
        if success:
            st.success(f"保存しました: {result}")
        else:
            st.error(result)

    # 技術リソースのリンク
    st.markdown("## 技術リソース")
    st.markdown(
        """
    - [Django 公式ドキュメント](https://docs.djangoproject.com/)
    - [Vue.js 公式ガイド](https://vuejs.org/guide/introduction.html)
    - [Python 公式ドキュメント](https://docs.python.org/)
    - [MDN Web Docs (HTML/CSS)](https://developer.mozilla.org/ja/)
    - [CSS-Tricks](https://css-tricks.com/)
    - [Django REST Framework](https://www.django-rest-framework.org/)
    """
    )

# メインエリア
st.markdown("<h1 class='main-header'>技術アドバイザー</h1>", unsafe_allow_html=True)
st.markdown(
    "<p class='sub-header'>Django / Vue.js / Python / HTML / CSS</p>",
    unsafe_allow_html=True,
)
st.markdown(
    "<div style='text-align:center;'>新人エンジニアの学習と開発をサポートします</div>",
    unsafe_allow_html=True,
)

# 技術タグの表示
st.markdown(
    """
<div style='text-align:center; margin: 20px 0;'>
<span class='tech-tag'>Django</span>
<span class='tech-tag'>Vue.js</span>
<span class='tech-tag'>Python</span>
<span class='tech-tag'>HTML</span>
<span class='tech-tag'>CSS</span>
</div>
""",
    unsafe_allow_html=True,
)

# チャット履歴の表示
for role, content in st.session_state.chat_history:
    if role == "user":
        st.markdown(
            f"<div class='user-bubble'>👨‍💻 <b>あなた:</b><br>{content}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='bot-bubble'>👨‍🏫 <b>技術アドバイザー:</b><br>{content}</div>",
            unsafe_allow_html=True,
        )

# 質問の入力
user_input = st.text_area("質問を入力してください:", height=100)

# 送信ボタン
if st.button("送信"):
    if user_input:
        # ユーザーの質問をチャット履歴に追加
        st.session_state.chat_history.append(("user", user_input))

        # APIにリクエストを送信するためのメッセージを準備
        st.session_state.messages.append({"role": "user", "content": user_input})

        # レスポンスを生成
        with st.spinner("回答を生成中..."):
            bot_response = generate_response(st.session_state.messages)

        # ボットの回答をチャット履歴とメッセージ履歴に追加
        st.session_state.chat_history.append(("assistant", bot_response))
        st.session_state.messages.append({"role": "assistant", "content": bot_response})

        # 表示を更新するためリロード
        st.experimental_rerun()

# フッター
st.markdown(
    """
<div style='text-align:center; margin-top:30px; padding:20px; border-top:1px solid #eee;'>
<p>このチャットボットはStreamlitとOpenAI APIを使用して構築されています。</p>
<p>回答はMarkdown形式で構造化され、任意の場所にドキュメントとして保存できます。</p>
</div>
""",
    unsafe_allow_html=True,
)
# app.py
