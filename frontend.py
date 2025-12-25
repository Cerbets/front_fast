import streamlit as st
import requests
import base64
import urllib.parse
from dotenv import load_dotenv
import os

load_dotenv()
tesing_mode= True
st.session_state.cansend = False
BACKEND_URL = os.getenv("BACKEND_URL")
if tesing_mode:
    BACKEND_URL = "http://localhost:8000/"
st.set_page_config(page_title="Cerbet's website", layout="wide")

if 'token' not in st.session_state:
    st.session_state.token = None
if 'user' not in st.session_state:
    st.session_state.user = None


def get_headers():
    """Get authorization headers with token"""
    if st.session_state.token:
        return {"Authorization": f"Bearer {st.session_state.token}"}
    return {}


def profile_image():
    if st.session_state.user and st.session_state.user.get('profile_page'):
        avatar_url = st.session_state.user['profile_page']["url"]
        st.markdown(
            """
            <style>
            .profile-pic {
                display: block;
                margin-left: auto;
                margin-right: auto;
                width: 150px;
                height: 150px;
                border-radius: 50%;
                object-fit: cover;
                border: 2px solid #eee;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        avatar_placeholder.markdown(f'<img src="{avatar_url}" class="profile-pic">', unsafe_allow_html=True)


def login_page():
    st.title("🚀 Welcome to Simple Social")

    email = st.text_input("Email:")
    password = st.text_input("Password:", type="password")

    if email and password:
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Login", type="primary", use_container_width=True):
                login_data = {"username": email, "password": password}
                try:
                    response = requests.post(f"{BACKEND_URL}/auth/jwt/login", data=login_data)
                    if response.status_code == 200:
                        token_data = response.json()
                        st.session_state.token = token_data["access_token"]

                        user_response = requests.get(f"{BACKEND_URL}/users/me", headers=get_headers())
                        if user_response.status_code == 200:
                            st.session_state.user = user_response.json()
                            print(f"DEBUG: Login success for {email}")
                            st.rerun()
                        else:
                            print(
                                f"ERROR: Get user info failed. Status: {user_response.status_code}, Response: {user_response.text}")
                            st.error("Failed to get user info")
                    else:
                        print(f"ERROR: Login failed. Status: {response.status_code}, Response: {response.text}")
                        st.error("Invalid email or password!")
                except Exception as e:
                    print(f"CRITICAL: Connection error during login: {e}")
                    st.error("Could not connect to backend.")

        with col2:
            if st.button("Sign Up", type="secondary", use_container_width=True):
                signup_data = {"email": email, "password": password}
                try:
                    response = requests.post(f"{BACKEND_URL}/auth/register", json=signup_data)
                    if response.status_code == 201:
                        print(f"DEBUG: User {email} registered successfully.")
                        st.success("Account created! Click Login now.")
                    else:
                        print(f"ERROR: Registration failed. Status: {response.status_code}, Response: {response.text}")
                        error_detail = response.json().get("detail", "Registration failed")
                        st.error(f"Registration failed: {error_detail}")
                except Exception as e:
                    print(f"CRITICAL: Connection error during signup: {e}")
                    st.error("Could not connect to backend.")
    else:
        st.info("Enter your email and password above")


def upload_page():
    st.title("📸 Share Something")

    uploaded_file = st.file_uploader("Choose media", type=['png', 'jpg', 'jpeg', 'mp4', 'avi', 'mov', 'mkv', 'webm'])
    caption = st.text_area("Caption:", placeholder="What's on your mind?")

    if uploaded_file and st.button("Share", type="primary"):
        with st.spinner("Uploading..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            data = {"caption": caption}
            try:
                response = requests.post(f"{BACKEND_URL}/upload", files=files, data=data, headers=get_headers())
                if response.status_code == 200:
                    print("DEBUG: Upload successful.")
                    st.success("Posted!")
                else:
                    print(f"ERROR: Upload failed. Status: {response.status_code}, Response: {response.text}")
                    st.error(f"Upload failed! (Error {response.status_code})")
            except Exception as e:
                print(f"CRITICAL: Connection error during upload: {e}")
                st.error("Upload error.")


def profile_page():
    st.title("👤 Profile Settings")
    uploaded_file = st.file_uploader("Choose profile's avatar", type=['png', 'jpg', 'jpeg'])

    if uploaded_file:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.markdown(
                """
                <style>
                .profile-pic {
                    display: block; margin-left: auto; margin-right: auto;
                    width: 150px; height: 150px; border-radius: 50%;
                    object-fit: cover; border: 2px solid #eee;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            bytes_data = uploaded_file.getvalue()
            base64_image = base64.b64encode(bytes_data).decode()
            st.markdown(f'<img src="data:image/png;base64,{base64_image}" class="profile-pic">', unsafe_allow_html=True)

    if uploaded_file and st.button("Share", type="primary", use_container_width=True):
        with st.spinner("Uploading..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
            try:
                response = requests.post(f"{BACKEND_URL}/profile_update", files=files, headers=get_headers())
                if response.status_code == 200:
                    data = response.json()
                    new_avatar_url = data.get("url")
                    print(f"DEBUG: Profile updated. New avatar: {new_avatar_url}")

                    if 'profile_page' not in st.session_state.user or st.session_state.user['profile_page'] is None:
                        st.session_state.user['profile_page'] = {}

                    st.session_state.user['profile_page']['url'] = new_avatar_url
                    st.success("Posted!")
                    profile_image()
                else:
                    print(f"ERROR: Profile update failed. Status: {response.status_code}, Response: {response.text}")
                    st.error("Upload failed!")
            except Exception as e:
                print(f"CRITICAL: Profile update exception: {e}")
                st.error("Error updating profile.")


def feed_page():
    st.title("🏠 Feed")
    try:
        response = requests.get(f"{BACKEND_URL}/feed", headers=get_headers())
        if response.status_code == 200:
            posts = response.json().get("posts", [])
            print(f"DEBUG: Loaded {len(posts)} posts.")

            if not posts:
                st.info("No posts yet! Be the first to share something.")
                return

            for post in posts:
                st.markdown("---")
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"**{post['email']}** • {post['created_at'][:10]}")
                with col2:
                    if post.get('is_owner', False):
                        if st.button("🗑️", key=f"delete_{post['id']}", help="Delete post"):
                            del_resp = requests.delete(f"{BACKEND_URL}/posts/{post['id']}", headers=get_headers())
                            if del_resp.status_code == 200:
                                print(f"DEBUG: Deleted post {post['id']}")
                                st.success("Post deleted!")
                                st.rerun()
                            else:
                                print(f"ERROR: Delete post {post['id']} failed. Status: {del_resp.status_code}")
                                st.error("Failed to delete post!")

                caption = post.get('caption', '')
                if post['file_type'] in ['.jpg', '.jpeg', '.png', '.webm']:
                    uniform_url = create_transformed_url(post['url'], "", caption)
                    st.image(uniform_url, width=300)
                else:
                    uniform_video_url = create_transformed_url(post['url'], "w-400,h-200,cm-pad_resize,bg-blurred")
                    st.video(uniform_video_url)
                    st.caption(caption)
        else:
            print(f"ERROR: Could not load feed. Status: {response.status_code}, Response: {response.text}")
            st.error("Failed to load feed")
    except Exception as e:
        print(f"CRITICAL: Feed exception: {e}")
        st.error("Network error while loading feed.")


def ai_page():
    st.title("🤖 AI Assistant")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Спросите что-нибудь у ИИ...",disabled=st.session_state.cansend):

        with st.chat_message("user", avatar=st.session_state.user['profile_page']["url"],):
            st.markdown(prompt)

        with st.chat_message("assistant"):

            st.session_state.cansend = True

            message_placeholder = st.empty()
            message_placeholder.markdown("Thinking...")

            try:
                payload = {
                    "messages": [
                        {"content":prompt}
                    ]
                }
                response = requests.post(
                    f"{BACKEND_URL}/ai/chat",

                    json=payload,
                    headers=get_headers()
                )

                if response.status_code == 200:
                    full_response = response.json().get("reply", "No response from AI.")
                    print(f"DEBUG: AI Response received successfully.")

                    message_placeholder.markdown(full_response)
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                else:
                    error_msg = f"Error {response.status_code}: {response.text}"
                    print(f"ERROR: AI request failed. {error_msg}")
                    message_placeholder.markdown("⚠️ Sorry, I couldn't process that request.")
                    st.error(error_msg)

            except Exception as e:
                print(f"CRITICAL: AI Page Connection Error: {e}")
                message_placeholder.markdown("❌ Connection error.")
                st.error("Could not reach the AI server.")
            finally:
                print("Труанули")
                st.session_state.cansend  = False
                st.rerun()

    if st.sidebar.button("Clear Chat History"):
        st.session_state.messages = []
        print("DEBUG: Chat history cleared.")
        st.rerun()




def encode_text_for_overlay(text):
    if not text: return ""
    base64_text = base64.b64encode(text.encode('utf-8')).decode('utf-8')
    return urllib.parse.quote(base64_text)


def create_transformed_url(original_url, transformation_params, caption=None):
    if caption:
        encoded_caption = encode_text_for_overlay(caption)
        text_overlay = f"l-text,ie-{encoded_caption},ly-N20,lx-20,fs-100,co-white,bg-000000A0,l-end"
        transformation_params = text_overlay
    if not transformation_params: return original_url
    try:
        parts = original_url.split("/")
        imagekit_id = parts[3]
        file_path = "/".join(parts[4:])
        base_url = "/".join(parts[:4])
        return f"{base_url}/tr:{transformation_params}/{file_path}"
    except:
        return original_url


# --- Главная логика приложения ---
if st.session_state.user is None:
    login_page()
else:

    st.sidebar.title(f"👋 Hi {st.session_state.user.get('email', 'User')}!")
    global avatar_placeholder
    avatar_placeholder = st.sidebar.empty()

    profile_image()

    if st.sidebar.button("Logout"):
        print(f"DEBUG: User logged out.")
        st.session_state.user = None
        st.session_state.token = None
        st.rerun()

    st.sidebar.markdown("---")
    page = st.sidebar.radio("Navigate:", ["🏠 Feed", "📸 Upload", "👤 Profile Settings","🤖 AI"])

    if page == "🏠 Feed":
        feed_page()
    elif page == "👤 Profile Settings":
        profile_page()
    elif page == "🤖 AI":
        ai_page()
    else:
        upload_page()