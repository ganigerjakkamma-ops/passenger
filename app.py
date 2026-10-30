import os
from datetime import datetime, timezone
from urllib.parse import urlparse

import bcrypt
import streamlit as st
from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError, PyMongoError

# -------------------- CONFIG --------------------
st.set_page_config(
    page_title="Blog Application",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
)
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI", "").strip()

st.markdown("""
<style>
.stApp { background: #f3f8ff; color: #172b4d; }
[data-testid="stSidebar"] { background: #e2efff; }
.hero {
  background: linear-gradient(120deg, #1266b3, #75baff);
  padding: 2rem 1.5rem; border-radius: 18px; text-align: center;
  margin-bottom: 1.2rem;
}
.hero h1, .hero p { color: white !important; }
div[data-testid="stMetric"] {
  background: white; padding: 14px; border-radius: 12px;
  border: 1px solid #d5e5f7;
}
div.stButton > button {
  border-radius: 9px; border: 0; font-weight: 600;
}
.small-muted { color: #60758d; font-size: .9rem; }
</style>
""", unsafe_allow_html=True)

CATEGORIES = [
    "Technology", "Education", "Travel", "Food",
    "Lifestyle", "Business", "Health", "Other"
]

# -------------------- DATABASE --------------------
@st.cache_resource
def get_database(uri: str):
    client = MongoClient(uri, serverSelectionTimeoutMS=8000)
    client.admin.command("ping")
    database = client["blog_application"]
    database.users.create_index([("username", ASCENDING)], unique=True)
    database.users.create_index([("email", ASCENDING)], unique=True)
    database.blogs.create_index([("created_at", DESCENDING)])
    database.blogs.create_index([("author", ASCENDING)])
    return database

if not MONGO_URI:
    st.error("MongoDB connection is not configured. Add MONGO_URI to your environment or Streamlit secrets.")
    st.stop()

try:
    db = get_database(MONGO_URI)
    users = db["users"]
    blogs = db["blogs"]
except Exception:
    st.error("Could not connect to MongoDB. Check your connection string, database user, and Atlas network access.")
    st.stop()

# -------------------- SESSION --------------------
if "user" not in st.session_state:
    st.session_state.user = None
if "selected_blog_id" not in st.session_state:
    st.session_state.selected_blog_id = None
if "confirm_delete_id" not in st.session_state:
    st.session_state.confirm_delete_id = None

def logout():
    st.session_state.user = None
    st.session_state.selected_blog_id = None
    st.session_state.confirm_delete_id = None
    st.rerun()

def current_username():
    return st.session_state.user["username"] if st.session_state.user else None

# -------------------- AUTH --------------------
def register_user(username: str, email: str, password: str):
    username = username.strip()
    email = email.strip().lower()
    if len(username) < 3:
        return False, "Username must be at least 3 characters."
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        return False, "Enter a valid email address."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    try:
        users.insert_one({
            "username": username,
            "email": email,
            "password_hash": hashed,
            "created_at": datetime.now(timezone.utc),
        })
        return True, "Account created. You can now log in."
    except DuplicateKeyError:
        return False, "That username or email is already registered."
    except PyMongoError:
        return False, "Registration failed because of a database error."

def authenticate(username: str, password: str):
    user = users.find_one({"username": username.strip()})
    if not user:
        return None
    try:
        stored_hash = user.get("password_hash") or user.get("password")
        if stored_hash and bcrypt.checkpw(password.encode("utf-8"), bytes(stored_hash)):
            return {
                "id": str(user["_id"]),
                "username": user["username"],
                "email": user["email"],
            }
    except (ValueError, TypeError):
        return None
    return None

# -------------------- BLOG DATA --------------------
def blog_query_for_user(username):
    # Supports this project's author field and older blog records.
    return {"author": username}

def list_blogs(search="", category="All", owner_only=False):
    query = {}
    if owner_only:
        query["author"] = current_username()
    if category != "All":
        query["category"] = category
    if search.strip():
        query["$and"] = [
            {"$or": [
                {"title": {"$regex": search.strip(), "$options": "i"}},
                {"content": {"$regex": search.strip(), "$options": "i"}},
            ]}
        ]
    return list(blogs.find(query).sort("created_at", DESCENDING))

def create_blog(title, category, image_url, content):
    blogs.insert_one({
        "title": title.strip(),
        "category": category,
        "image": image_url.strip(),
        "content": content.strip(),
        "author": current_username(),
        "created_at": datetime.now(timezone.utc),
        "updated_at": None,
    })

def get_blog(blog_id):
    try:
        return blogs.find_one({"_id": ObjectId(blog_id)})
    except Exception:
        return None

def update_blog(blog_id, title, category, image_url, content):
    return blogs.update_one(
        {"_id": ObjectId(blog_id), "author": current_username()},
        {"$set": {
            "title": title.strip(),
            "category": category,
            "image": image_url.strip(),
            "content": content.strip(),
            "updated_at": datetime.now(timezone.utc),
        }},
    )

def remove_blog(blog_id):
    return blogs.delete_one({
        "_id": ObjectId(blog_id),
        "author": current_username(),
    })

def valid_image_url(value):
    if not value.strip():
        return True
    parsed = urlparse(value.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)

# -------------------- HEADER --------------------
st.markdown("""
<div class="hero">
  <h1>📝 Blog Application</h1>
  <p>Write, publish, discover and manage your stories.</p>
</div>
""", unsafe_allow_html=True)

# -------------------- LOGIN / REGISTER --------------------
if not st.session_state.user:
    login_tab, register_tab = st.tabs(["🔐 Login", "📝 Create account"])

    with login_tab:
        st.subheader("Welcome back")
        with st.form("login_form"):
            login_name = st.text_input("Username")
            login_password = st.text_input("Password", type="password")
            login_submit = st.form_submit_button("Login", use_container_width=True)
        if login_submit:
            user = authenticate(login_name, login_password)
            if user:
                st.session_state.user = user
                st.success("Login successful.")
                st.rerun()
            else:
                st.error("Incorrect username or password.")

    with register_tab:
        st.subheader("Join the blog community")
        with st.form("register_form"):
            new_name = st.text_input("Username (at least 3 characters)")
            new_email = st.text_input("Email")
            new_password = st.text_input("Password (at least 8 characters)", type="password")
            confirm_password = st.text_input("Confirm password", type="password")
            register_submit = st.form_submit_button("Register", use_container_width=True)
        if register_submit:
            if new_password != confirm_password:
                st.error("Passwords do not match.")
            else:
                ok, message = register_user(new_name, new_email, new_password)
                (st.success if ok else st.error)(message)
    st.stop()

# -------------------- PRIVATE APP --------------------
username = current_username()
sidebar = st.sidebar
sidebar.title("📝 Blog Menu")
sidebar.write(f"Signed in as **{username}**")
page = sidebar.radio(
    "Navigate",
    ["Dashboard", "All Blogs", "Create Blog", "My Blogs", "My Profile"],
)
if sidebar.button("🚪 Logout", use_container_width=True):
    logout()

# Dashboard
if page == "Dashboard":
    st.title(f"Welcome, {username} 👋")
    own_blogs = list_blogs(owner_only=True)
    all_count = blogs.count_documents({})
    category_count = len({b.get("category", "Other") for b in own_blogs})
    c1, c2, c3 = st.columns(3)
    c1.metric("My published blogs", len(own_blogs))
    c2.metric("All community blogs", all_count)
    c3.metric("Categories used", category_count)
    st.subheader("Your latest posts")
    if not own_blogs:
        st.info("You haven't published a blog yet. Choose Create Blog to get started.")
    for item in own_blogs[:5]:
        with st.container(border=True):
            st.subheader(item.get("title", "Untitled"))
            st.caption(f"{item.get('category', 'Other')} • by {item.get('author', 'Unknown')}")
            st.write(item.get("content", "")[:220] + ("…" if len(item.get("content", "")) > 220 else ""))
            if st.button("Open post", key=f"dash_{item['_id']}"):
                st.session_state.selected_blog_id = str(item["_id"])
                st.session_state.page_to_open = "details"
                st.rerun()

# All blogs
elif page == "All Blogs":
    st.title("🌍 Explore blogs")
    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("Search by title or content")
    with col2:
        category = st.selectbox("Category", ["All"] + CATEGORIES)
    results = list_blogs(search, category)
    st.caption(f"{len(results)} post(s) found")
    if not results:
        st.info("No blogs match your search.")
    for item in results:
        with st.container(border=True):
            left, right = st.columns([1, 2])
            with left:
                if item.get("image"):
                    st.image(item["image"], use_container_width=True)
            with right:
                st.subheader(item.get("title", "Untitled"))
                st.caption(f"{item.get('category', 'Other')} • by {item.get('author', 'Unknown')}")
                text = item.get("content", "")
                st.write(text[:240] + ("…" if len(text) > 240 else ""))
                if st.button("Read full blog", key=f"all_{item['_id']}"):
                    st.session_state.selected_blog_id = str(item["_id"])
                    st.session_state.page_to_open = "details"
                    st.rerun()
                if item.get("author") == username:
                    st.caption("This is your post.")

# Create
elif page == "Create Blog":
    st.title("✍️ Create a blog")
    with st.form("create_blog_form"):
        title = st.text_input("Blog title")
        category = st.selectbox("Category", CATEGORIES)
        image_url = st.text_input("Image URL (optional, HTTPS recommended)")
        content = st.text_area("Your blog content", height=260)
        publish = st.form_submit_button("Publish blog", use_container_width=True)
    if publish:
        if not title.strip() or not content.strip():
            st.error("Title and content are required.")
        elif not valid_image_url(image_url):
            st.error("Image URL must begin with http:// or https://.")
        else:
            try:
                create_blog(title, category, image_url, content)
                st.success("Your blog has been published.")
                st.rerun()
            except PyMongoError:
                st.error("Could not save the blog. Please try again.")

# My blogs
elif page == "My Blogs":
    st.title("📚 My blogs")
    col1, col2 = st.columns([2, 1])
    with col1:
        search = st.text_input("Search your posts")
    with col2:
        category = st.selectbox("Filter category", ["All"] + CATEGORIES)
    results = list_blogs(search, category, owner_only=True)
    if not results:
        st.info("No posts found. Create your first blog!")
    for item in results:
        with st.container(border=True):
            st.subheader(item.get("title", "Untitled"))
            st.caption(item.get("category", "Other"))
            st.write(item.get("content", "")[:200] + "…")
            a, b, c = st.columns(3)
            with a:
                if st.button("View", key=f"view_{item['_id']}"):
                    st.session_state.selected_blog_id = str(item["_id"])
                    st.session_state.page_to_open = "details"
                    st.rerun()
            with b:
                if st.button("Edit", key=f"edit_{item['_id']}"):
                    st.session_state.selected_blog_id = str(item["_id"])
                    st.session_state.page_to_open = "edit"
                    st.rerun()
            with c:
                if st.button("Delete", key=f"delete_{item['_id']}"):
                    st.session_state.confirm_delete_id = str(item["_id"])
                    st.rerun()

    delete_id = st.session_state.confirm_delete_id
    if delete_id:
        target = get_blog(delete_id)
        if target and target.get("author") == username:
            st.warning(f"Delete “{target.get('title', 'this blog')}”? This cannot be undone.")
            yes, no = st.columns(2)
            with yes:
                if st.button("Yes, delete permanently", type="primary"):
                    try:
                        result = remove_blog(delete_id)
                        st.session_state.confirm_delete_id = None
                        if result.deleted_count:
                            st.success("Blog deleted.")
                        st.rerun()
                    except PyMongoError:
                        st.error("Delete failed. Please try again.")
            with no:
                if st.button("Cancel deletion"):
                    st.session_state.confirm_delete_id = None
                    st.rerun()
        else:
            st.session_state.confirm_delete_id = None
            st.warning("Blog not found or you do not own it.")

# Blog details / edit are available via selected item. Dedicated actions on My Blogs.
elif page == "My Profile":
    st.title("👤 My profile")
    profile = users.find_one({"_id": ObjectId(st.session_state.user["id"])})
    if profile:
        st.text_input("Username", value=profile.get("username", ""), disabled=True)
        with st.form("profile_form"):
            email = st.text_input("Email address", value=profile.get("email", ""))
            save = st.form_submit_button("Save profile")
        if save:
            email = email.strip().lower()
            if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
                st.error("Enter a valid email.")
            else:
                try:
                    users.update_one(
                        {"_id": profile["_id"]},
                        {"$set": {"email": email}},
                    )
                    st.session_state.user["email"] = email
                    st.success("Profile updated.")
                    st.rerun()
                except DuplicateKeyError:
                    st.error("That email is already used by another account.")
        st.divider()
        st.metric("Your published blogs", blogs.count_documents({"author": username}))
        st.caption(f"Member since: {profile.get('created_at', 'Date unavailable')}")

# Handle selected blog view/edit after reruns.
if st.session_state.get("page_to_open") in ("details", "edit"):
    action = st.session_state.page_to_open
    blog_id = st.session_state.get("selected_blog_id")
    blog = get_blog(blog_id) if blog_id else None
    if action == "details" and blog:
        st.divider()
        st.title("📖 Blog details")
        st.subheader(blog.get("title", "Untitled"))
        st.caption(f"{blog.get('category', 'Other')} • by {blog.get('author', 'Unknown')}")
        if blog.get("image"):
            st.image(blog["image"], use_container_width=True)
        st.write(blog.get("content", ""))
        if blog.get("author") == username:
            if st.button("Edit this blog"):
                st.session_state.page_to_open = "edit"
                st.rerun()
        if st.button("Close details"):
            st.session_state.page_to_open = None
            st.session_state.selected_blog_id = None
            st.rerun()
    elif action == "edit":
        st.divider()
        st.title("✏️ Edit selected blog")
        if not blog or blog.get("author") != username:
            st.error("Blog not found or you do not have permission to edit it.")
        else:
            current_cat = blog.get("category", "Other")
            cat_index = CATEGORIES.index(current_cat) if current_cat in CATEGORIES else len(CATEGORIES)-1
            with st.form("edit_selected_blog"):
                new_title = st.text_input("Title", value=blog.get("title", ""))
                new_category = st.selectbox("Category", CATEGORIES, index=cat_index)
                new_image = st.text_input("Image URL", value=blog.get("image", ""))
                new_content = st.text_area("Content", value=blog.get("content", ""), height=250)
                save_edit = st.form_submit_button("Save changes")
            if save_edit:
                if not new_title.strip() or not new_content.strip():
                    st.error("Title and content are required.")
                elif not valid_image_url(new_image):
                    st.error("Image URL must begin with http:// or https://.")
                else:
                    try:
                        result = update_blog(blog_id, new_title, new_category, new_image, new_content)
                        if result.matched_count:
                            st.success("Blog updated.")
                            st.session_state.page_to_open = None
                            st.rerun()
                        else:
                            st.error("No matching blog was updated.")
                    except PyMongoError:
                        st.error("Update failed. Please try again.")

st.divider()
st.caption("© 2026 Blog Application • Built with Python, Streamlit and MongoDB")
