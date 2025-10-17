# ------------- Markify v2 (Photo Upload Coming Soon Edition) -------------
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import hashlib
import pandas as pd
import plotly.express as px
import json
import os
import numpy as np

# --- Session-State Trigger for Auto-refresh ---
if "refresh_trigger" not in st.session_state:
    st.session_state["refresh_trigger"] = 0

# --- Firebase Initialization ---
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

# --- Firebase key as Python dictionary ---
firebase_key_dict = {
    "type": "service_account",
    "project_id": "markify-7e6af",
    "private_key_id": "109fc85f9dedb6eecd27233ee9bb4fa89bb4f795",
    "private_key": """-----BEGIN PRIVATE KEY-----
MIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQDSi1gikDZ8/k02
G87czksdfnBlTly/alWM0kUM0syG4rA5qEdhMW9BOZ4/ck70kBnGR9imEimapXc6
1rNHv+WnyVAmi7HHS3OS5Hm/9XTRQ3P9moJKDS49sE/diqiOcxUkiicCpQMaXjxR
ymKBTIkf/8NaHnb2HW/Bfh6uBC2TiAg2QJg0XAs9EVWgifvef7KIBOZX20/qI1kc
XNR8wVqWoyZWYdPY92bmKi1HTxjBw6FPrSs0oFE8oSp4bi7nkw3z64hK08lVzX+H
GsFlHV3FICfEtcaLVaFCC3kT587VFZIuIR+xkVV0hF41Sf1tawq9D08tA5K+wqUY
3IQqljTjAgMBAAECggEAGzweLv5jpgCJQVYQiLyAt/R6mogr9DDPlzM97l44Sbx6
GkM71IU+BHxtDXz+XKFlTCJQEo9n5VLBHRHXyBC5Jt6iKRJJ8WM/tIEshJm+PjGR
B/2cG/Mfh6hOdHRywFZ/piXezPdGcvs8p0HcQyiA1mxRu08UiVqecbOcSVtN//bN
Gffx7PgTPgUlj32IMnHCN6tXdYT7IP1b+BUbA5ODybQLOxA8t9DmlYZTFt3Jzb8y
Ro7f8xasxQp1zMn2z+2MXZ/LeQlUyvaLIOrMgMggUIs/vD3ZYT4aN1glCRS/wN88
QQ6Jeg5pn7tgJOaNCQouxVdATfhTxpil9XKTaJ6ycQKBgQD2Uii4zlsWIgHTSN5i
IPV2D9I39mwQb4bc939dmCzNC9Sn67NBUdLW/58wdGaiaVl3R988UBP2K+a2T39g
ie/ihlryMiN3OyfUAJAR5hHCRCN/e+Hdo09svmys3O4B9yDuTnSO16KSW0++MqLd
+xshvrw6zLRnsxsoPEQJqD45cwKBgQDa0Us6EbzD0gQXj0bABDveXGY5fW31yFr1
GihllY1mceIzIYOfd0kWz31lLlHgfSKMyLO4sHBGuIOmYtQnWKD4sNrx5vWRpWE5
dJONCdRbqTkqNbmqF7Tt+WUjmYg3kQcSaxKKw3/Lr3BE3Z/sMtCtp40Vsr6ilcAF
iHbQBdX60QKBgG+qQ0e0VNqtxAISkK4PnvdMqNIx5j91L8BQeu7lI7o42MjfMz4z
Z8+LxpDi0/xgoexPKsZezw3UTRzs4SPUpGke22/chvNwX9feAXH7yKU22pjagkRF
2qXDleSvqz482DLwYiq3Wr3ao0XoEqlrQpuDqjVFw6sXKQKOf5GZMcw9AoGBAI5G
T1dueQIJ58c5zZLELfkiswTmXTzWDO4ZF/MVDl9x5NXCEMb61HcUakADohEIzBIl
3VVUw2v4RQFGeRMsOV36ACIRPdJ5aYHmHpoxrfX7TcP4MsQ5rdadtfkztrIKhkKf
g+rdupZBeAoO4BC/6Zc/vihBlFo6bCQs2rPfV4ZBAoGBAJB0IZgcvX9rKMtKOScw
p4CdiGGqPtqR+e/CoehIzhwSuLRcv2P9iNZUrOi1KoKKyj4twv8f+5yeYrkNDOlw
1okInVCOSWxgbYQs74Nds7SLsWuNW1SqhawKL9IdTPnBnVJqZ5efNY+66i6xcEzz
xegc+fNF/MoQIzuMMoMssz76
-----END PRIVATE KEY-----""",
    "client_email": "firebase-adminsdk-fbsvc@markify-7e6af.iam.gserviceaccount.com",
    "client_id": "105380457781434182722",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40markify-7e6af.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com"
}

# --- Initialize Firebase ---
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_key_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()
# --- Utility Functions ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user_doc(uid):
    return db.collection("users").document(uid)

def user_data(uid):
    doc = get_user_doc(uid).get()
    return doc.to_dict() if doc.exists else None

def is_admin(uid):
    data = user_data(uid)
    return data and data.get("role") == "admin"

def create_user(password, name):
    try:
        doc_ref = db.collection("users").document()
        doc_ref.set({
            "name": name,
            "password_hash": hash_password(password),
            "role": "user"
        })
        user = doc_ref.get()
        user_dict = user.to_dict()
        user_dict["uid"] = doc_ref.id
        return user_dict
    except Exception as e:
        st.error(f"Error creating user: {e}")
        return None

def update_password(uid, new_password):
    try:
        get_user_doc(uid).update({"password_hash": hash_password(new_password)})
        st.success("Password updated successfully.")
    except Exception as e:
        st.error(f"Error updating password: {e}")

def update_name(uid, new_name):
    try:
        get_user_doc(uid).update({"name": new_name})
        st.success("Name updated successfully.")
    except Exception as e:
        st.error(f"Error updating name: {e}")

def get_subjects_collection():
    return db.collection("subjects")

def add_subject(subject_name):
    try:
        get_subjects_collection().add({"name": subject_name})
        st.success("Subject added successfully.")
    except Exception as e:
        st.error(f"Error adding subject: {e}")

def get_all_subjects():
    docs = get_subjects_collection().stream()
    return sorted([doc.to_dict()["name"] for doc in docs])

# --- Exam/Mark Storage ---
def exam_id_from_fields(exam_name, exam_type, student_uid):
    unique_str = f"{exam_name.strip()}_{exam_type}_{student_uid}"
    return hashlib.sha256(unique_str.encode()).hexdigest()[:16]

def create_exam(exam_name, exam_type, student_uid):
    eid = exam_id_from_fields(exam_name, exam_type, student_uid)
    db.collection("exams").document(eid).set({
        "name": exam_name.strip(),
        "type": exam_type,
        "student_uid": student_uid
    })
    return eid

def get_marks_collection(exam_id):
    return db.collection("exams").document(exam_id).collection("marks")

def add_mark(exam_id, uid, subject, mark, total_mark):
    marks_col = get_marks_collection(exam_id)
    doc_id = f"{uid}_{subject}"
    marks_col.document(doc_id).set({
        "uid": uid,
        "subject": subject,
        "mark": mark,
        "total_mark": total_mark
    })

def get_marks_for_student_exam(exam_id, uid):
    marks_col = get_marks_collection(exam_id)
    docs = marks_col.where("uid", "==", uid).stream()
    marks = {}
    for doc in docs:
        d = doc.to_dict()
        marks[d["subject"]] = {"mark": d["mark"], "total_mark": d["total_mark"]}
    return marks

def get_exams_for_student(uid, exam_type=None):
    query = db.collection("exams").where("student_uid", "==", uid)
    if exam_type:
        query = query.where("type", "==", exam_type)
    docs = query.stream()
    exams = []
    for doc in docs:
        d = doc.to_dict()
        exams.append((doc.id, d.get("name"), d.get("type")))
    return exams

# --- Session Management ---
def login_user(user):
    st.session_state["uid"] = user.get("uid")
    st.session_state["name"] = user.get("name")
    st.session_state["role"] = user.get("role", "user")

def logout_user():
    for k in ["uid", "name", "role"]:
        st.session_state.pop(k, None)

def logged_in():
    return "uid" in st.session_state

# --- Pages ---
def signup_page():
    st.title("Sign Up to Markify")
    name = st.text_input("Full Name")
    pw1 = st.text_input("Password", type="password")
    pw2 = st.text_input("Confirm Password", type="password")
    if st.button("Sign Up"):
        if not name or not pw1 or not pw2:
            st.warning("All fields required.")
        elif pw1 != pw2:
            st.warning("Passwords don't match.")
        else:
            user = create_user(pw1, name)
            if user:
                login_user(user)
                st.success("Account created successfully.")
                st.session_state["refresh_trigger"] += 1

def login_page():
    st.title("Login to Markify")
    name = st.text_input("Full Name")
    pw = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if not name or not pw:
            st.warning("Please enter both name and password.")
            return
        
        try:
            users_ref = db.collection("users")
            query = users_ref.where("name", "==", name).limit(1).stream()
            user_docs = list(query)
            if not user_docs:
                st.error("Invalid credentials.")
                return
            
            user_doc = user_docs[0]
            user = user_doc.to_dict()
            
            if user.get("password_hash") == hashlib.sha256(pw.encode()).hexdigest():
                user["uid"] = user_doc.id
                login_user(user)
                st.success(f"Welcome back, {user.get('name','User')}!")
                st.session_state["refresh_trigger"] += 1
            else:
                st.error("Invalid credentials.")
        
        except Exception as e:
            st.error(f"Error logging in: {e}")
            
def dashboard_page():
    st.title(f"🏠 Dashboard - Welcome {st.session_state['name']}")
    st.markdown("### 📝 Add Marks")
    c1, c2, c3, c4, c5 = st.columns([2,2,2,1,1])
    with c1:
        exam_type = st.selectbox("Type", ["Exam", "Class Test", "Others"], key="exam_type")
    with c2:
        exam_name = st.text_input("Exam/Test Name", key="exam_name")
    with c3:
        all_subjects = get_all_subjects()
        if not all_subjects:
            st.info("No subjects found. Ask admin to add.")
            return
        subj = st.selectbox("Subject", all_subjects)
    with c4:
        mark = st.number_input("Marks", 0.0, 1000.0, 0.0, 0.5)
    with c5:
        total = st.number_input("Total", 1.0, 1000.0, 100.0, 0.5)

    if st.button("✅ Submit Mark"):
        uid = st.session_state["uid"]
        if not exam_name.strip():
            st.warning("Please enter exam/test name.")
            return
        eid = create_exam(exam_name, exam_type, uid)
        add_mark(eid, uid, subj, mark, total)
        st.success("Mark added successfully.")
        st.session_state["refresh_trigger"] += 1

    st.divider()
    st.markdown("### 📚 Your Exams")
    exams = get_exams_for_student(st.session_state["uid"])
    if not exams:
        st.info("No exams yet.")
        return
    for eid, name, etype in exams:
        marks = get_marks_for_student_exam(eid, st.session_state["uid"])
        total_obt = sum(v["mark"] for v in marks.values())
        total_full = sum(v["total_mark"] for v in marks.values())
        pct = (total_obt / total_full) * 100 if total_full > 0 else 0
        with st.expander(f"{name} ({etype}) - {pct:.2f}%"):
            df = pd.DataFrame([
                {"Subject": s, "Mark": v["mark"], "Total": v["total_mark"]}
                for s, v in marks.items()
            ])
            st.dataframe(df, hide_index=True)

def photo_upload_page():
    st.title("📸 Photo Upload - Coming Soon")
    st.info("This feature will be available in a future version.")

def statistics_page():
    st.title("📈 Statistics & Improvement (Coming Soon)")
    st.info("All marks are stored and visible in the Dashboard for now.")

def account_settings():
    st.title("⚙️ Account Settings")
    new_name = st.text_input("New Name", value=st.session_state["name"])
    if st.button("Update Name"):
        if new_name.strip():
            update_name(st.session_state["uid"], new_name)
            st.session_state["name"] = new_name
    st.divider()
    old_pw = st.text_input("Current Password", type="password")
    new_pw = st.text_input("New Password", type="password")
    if st.button("Change Password"):
        data = user_data(st.session_state["uid"])
        if data and data["password_hash"] == hashlib.sha256(old_pw.encode()).hexdigest():
            update_password(st.session_state["uid"], new_pw)
        else:
            st.error("Incorrect password.")

# --- Main ---
def main():
    st.set_page_config(page_title="Markify v2", layout="wide")
    if not logged_in():
        page = st.sidebar.radio("Navigation", ["🔑 Login", "📝 Sign Up"])
        if page == "🔑 Login":
            login_page()
        else:
            signup_page()
        return

    st.sidebar.title("Markify")
    page = st.sidebar.radio(
        "Navigate",
        ["🏠 Dashboard", "📸 Photo Upload", "📈 Statistics", "⚙️ Account Settings", "🚪 Logout"]
    )

    if page == "🏠 Dashboard":
        dashboard_page()
    elif page == "📈 Statistics":
        statistics_page()
    elif page == "📸 Photo Upload":
        photo_upload_page()
    elif page == "⚙️ Account Settings":
        account_settings()
    elif page == "🚪 Logout":
        logout_user()
        st.success("Logged out.")

if __name__ == "__main__":
    main()
