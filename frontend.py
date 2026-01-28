import streamlit as st
import requests
import base64
import urllib.parse
from dotenv import load_dotenv
import os
import json
import time
import websocket
import threading
load_dotenv()
from streamlit.runtime.scriptrunner import add_script_run_ctx,get_script_run_ctx
import streamlit.components.v1 as components
testing_mode = False
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
if testing_mode:
    BACKEND_URL = "http://localhost:8000"

st.set_page_config(page_title="Cerbet's Community", layout="wide")

if 'token' not in st.session_state:
    st.session_state.token = None
if 'user' not in st.session_state:
    st.session_state.user = None
if 'cansend' not in st.session_state:
    st.session_state.cansend = False



def get_headers():
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}


def create_transformed_url(original_url, transformation_params, caption=None):
    if caption:
        encoded_caption = base64.b64encode(caption.encode('utf-8')).decode('utf-8')
        encoded_caption = urllib.parse.quote(encoded_caption)
        transformation_params = f"l-text,ie-{encoded_caption},ly-N20,lx-20,fs-100,co-white,bg-000000A0,l-end"
    if not transformation_params: return original_url
    try:
        parts = original_url.split("/")
        base_url = "/".join(parts[:4])
        file_path = "/".join(parts[4:])
        return f"{base_url}/tr:{transformation_params}/{file_path}"
    except:
        return original_url



def login_page():
    st.title("🚀 Welcome to Cerbet's Community")
    email = st.text_input("Email:")
    password = st.text_input("Password:", type="password")

    col1, col2 = st.columns(2)
    if email and password:
        with col1:
            if st.button("Login", type="primary", use_container_width=True):
                try:

                    response = requests.post(f"{BACKEND_URL}/auth/login", data={"username": email, "password": password})

                    if response.status_code == 200:

                        token_data = response.json()

                        st.session_state.token = token_data["access_token"]

                        st.session_state.user = {"email": email, "id": token_data["id"],
                                                 "profile_page": token_data["profile_page"]}

                        st.rerun()

                except Exception as e:

                    print(f"CRITICAL: Connection error during login: {e}")

                st.error("Could not connect to backend.")
        with col2:
            if st.button("Sign Up", use_container_width=True):
                try:
                    resp = requests.post(f"{BACKEND_URL}/auth/register", json={"email": email, "password": password})
                    if resp.status_code == 201:
                        st.success("Account created! Check email.")
                    else:
                        st.error("Registration failed")
                except:
                    st.error("Backend connection error")


def feed_page():
    st.title("🏠 Global Feed")
    try:
        resp = requests.get(f"{BACKEND_URL}/feed", headers=get_headers())
        if resp.status_code == 200:
            posts = resp.json().get("posts", [])
            for post in posts:
                with st.container(border=True):
                    c1, c2 = st.columns([0.9, 0.1])
                    c1.markdown(f"**{post['email']}** • {post['created_at'][:10]}")
                    if post.get('is_owner'):
                        if c2.button("🗑️", key=f"del_post_{post['id']}"):
                            requests.delete(f"{BACKEND_URL}/posts/{post['id']}", headers=get_headers())
                            st.rerun()

                    url = post['url'].lower()
                    if any(url.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                        st.image(create_transformed_url(post['url'], "", post.get('caption')), use_container_width=True)
                    elif any(url.endswith(ext) for ext in ['.mp4', '.webm']):
                        st.video(post['url'])
                    if post.get('caption'): st.write(post['caption'])
    except:
        st.error("Failed to load feed")


def chat_page():
    st.title("💬 Community Chat")

    if "needs_rerun" not in st.session_state:
        st.session_state.needs_rerun = False

    @st.fragment(run_every="1s")
    def sync_trigger():
        if st.session_state.needs_rerun:
            st.toast("🔄 message received via WEBSOCKET")
            st.session_state.needs_rerun = False
            time.sleep(0.5)

            st.rerun()

    sync_trigger()

    def on_message(ws, message):
        st.session_state.needs_rerun = True

    if "ws_connected" not in st.session_state:
        ws_url = BACKEND_URL.replace("https", "ws") + "/ws"
        ctx = get_script_run_ctx()

        def run_ws(ctx):
            add_script_run_ctx(threading.current_thread(), ctx)
            ws = websocket.WebSocketApp(
                ws_url,
                on_message=on_message,
                on_open=lambda ws: print("🚀 [WS] Соединение установлено!"),
                on_error=lambda ws, err: print(f"🧨 [WS] Ошибка: {err}"),
                on_close=lambda ws, status, msg: print(f"🔌 [WS] Закрыто: {msg}"),
            )
            ws.run_forever(ping_interval=20, ping_timeout=10)

        thread = threading.Thread(target=run_ws, args=(ctx,), daemon=True)
        thread.start()
        st.session_state.ws_connected = True

    try:
        resp = requests.get(f"{BACKEND_URL}/messages/", headers=get_headers())
        messages = resp.json().get("messages", []) if resp.status_code == 200 else []
        messages.reverse()
    except Exception as e:
        st.error(f"Connection error: {e}")
        messages = []

    chat_container = st.container(height=500)
    with chat_container:
        for msg in messages:
            is_me = msg.get("is_owner", False)
            with st.chat_message("user" if is_me else "assistant"):
                col1, col2 = st.columns([0.92, 0.08])
                with col1:
                    time_str = msg['created_at'][11:16]
                    st.markdown(f"**{msg['email']}** <small>{time_str}</small>", unsafe_allow_html=True)
                    st.write(msg['content'])
                with col2:
                    if is_me:
                        if st.button("❌", key=f"msg_{msg['id']}"):
                            requests.delete(f"{BACKEND_URL}/messages/",
                                            json={"message_id": msg['id']},
                                            headers=get_headers())
                            st.rerun()

    if prompt := st.chat_input("Type anything please..."):
        try:
            resp = requests.post(f"{BACKEND_URL}/messages/",
                                 json={"content": prompt},
                                 headers=get_headers())
            if resp.status_code == 200:
                st.toast(f"🔄 message sent")
            else:
                st.error(f"Ошибка: {resp.status_code}")
        except Exception as e:
            st.error(f"Failed to send: {e}")


def profile_page():
    st.title("👤 Profile Settings")
    if st.session_state.user.get('profile_page'):
        st.image(st.session_state.user['profile_page'], width=150)

    uploaded_file = st.file_uploader("Change Avatar", type=['jpg', 'png', 'jpeg'])
    if uploaded_file and st.button("Update Avatar"):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        resp = requests.post(f"{BACKEND_URL}/profile_update", files=files, headers=get_headers())
        if resp.status_code == 200:
            st.session_state.user['profile_page'] = resp.json().get("url")
            st.success("Updated!")
            st.rerun()


def ai_page():
    st.title("🤖 AI Assistant")
    if "ai_history" not in st.session_state: st.session_state.ai_history = []

    for m in st.session_state.ai_history:
        with st.chat_message(m["role"]): st.markdown(m["content"])

    if prompt := st.chat_input("Ask AI...", disabled=st.session_state.cansend):
        st.session_state.ai_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            st.session_state.cansend = True
            try:
                resp = requests.post(f"{BACKEND_URL}/ai/chat", json={"messages": [{"content": prompt}]},
                                     headers=get_headers())
                if resp.status_code == 200:
                    reply = resp.json().get("reply")
                    st.markdown(reply)
                    st.session_state.ai_history.append({"role": "assistant", "content": reply})
            except:
                st.error("AI unreachable")
            st.session_state.cansend = False
            st.rerun()



if st.session_state.user is None:
    login_page()

    query_params = st.query_params
    if "email" in query_params and "code" in query_params:

        email = query_params["email"]

        print("Here")

        code = query_params["code"]

        with st.spinner("Activating your account..."):

            try:

                response = requests.get(

                    f"{BACKEND_URL}/auth/verify",

                    params={"email": email, "code": code}

                )

                if response.status_code == 200:

                    st.success("Succesfully activated!Please Login now")

                    st.session_state["verified"] = True

                    st.query_params.clear()

                else:

                    st.error(f"Error:: {response.json().get('detail')}")

            except Exception as e:

                    st.error(f"Couldn't connect to backend: {e}")

                    st.query_params.clear()

                    login_page()

else:
    # Sidebar
    st.sidebar.title(f"👋 {st.session_state.user['email']}")
    if st.session_state.user.get('profile_page'):
        st.sidebar.image(st.session_state.user['profile_page'], width=100)

    if st.sidebar.button("Logout"):
        st.session_state.user = None
        st.session_state.token = None
        st.rerun()

    st.sidebar.markdown("---")
    page = st.sidebar.radio("Go to:", ["🏠 Feed", "💬 Community Chat", "📸 Upload", "👤 Profile", "🤖 AI"])


    if page == "🏠 Feed":
        feed_page()
    elif page == "💬 Community Chat":

        chat_page()
    elif page == "📸 Upload":
        st.title("📸 Upload")
        f = st.file_uploader("Media")
        c = st.text_area("Caption")
        if f and st.button("Post"):
            files = {"file": (f.name, f.getvalue(), f.type)}
            requests.post(f"{BACKEND_URL}/upload", files=files, data={"caption": c}, headers=get_headers())
            st.success("Done!")
    elif page == "👤 Profile":
        profile_page()
    elif page == "🤖 AI":
        ai_page()

        # python -m streamlit run frontend.py
