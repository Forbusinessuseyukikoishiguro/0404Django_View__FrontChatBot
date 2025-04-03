import streamlit as st
from openai import OpenAI
import os

# ページ設定
st.set_page_config(page_title="技術アドバイザー", page_icon="👨‍💻")

# APIクライアントの初期化
client = None
api_key = os.environ.get("OPENAI_API_KEY")

if not api_key:
    api_key = st.text_input("OpenAI APIキーを入力してください:", type="password")
    if not api_key:
        st.warning("APIキーが必要です")
        st.stop()

client = OpenAI(api_key=api_key)

# システムプロンプト
SYSTEM_PROMPT = """
あなたはDjango、Vue.js、Python、HTML、CSSの専門家です。
新人エンジニアに丁寧に技術を教えてください。
"""

# セッション状態の初期化
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

# UIの設定
st.title("技術アドバイザー")
st.subheader("Django / Vue.js / Python / HTML / CSS")

# チャット履歴の表示
for message in st.session_state.messages[1:]:  # システムメッセージをスキップ
    if message["role"] == "user":
        st.write(f"👨‍💻 **あなた**: {message['content']}")
    else:
        st.write(f"🤖 **アドバイザー**: {message['content']}")

# ユーザー入力
with st.form("chat_form", clear_on_submit=True):
    user_input = st.text_area("質問を入力してください:", height=100)
    submitted = st.form_submit_button("送信")

    if submitted and user_input:
        # ユーザーの質問を追加
        st.session_state.messages.append({"role": "user", "content": user_input})

        # APIレスポンスを取得
        with st.spinner("回答を生成中..."):
            try:
                # 新しいOpenAI API構文
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo", messages=st.session_state.messages
                )

                # 応答を保存（新APIでは構造が変わっています）
                bot_message = {
                    "role": "assistant",
                    "content": response.choices[0].message.content,
                }
                st.session_state.messages.append(bot_message)

                # ページを再読み込み
                st.rerun()
            except Exception as e:
                st.error(f"エラーが発生しました: {str(e)}")
