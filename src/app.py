
# ------------- Markify v2 -------------
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import hashlib
import pandas as pd
import plotly.express as px
import datetime
import json

# --- Session-State Trigger for Auto-refresh ---
if "refresh_trigger" not in st.session_state:
    st.session_state["refresh_trigger"] = 0

# --- Firebase Initialization ---
import os

if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_key.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

# --- Utility Functions ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_user_doc(uid):
    return db.collection("users").document(uid)

def user_data(uid):
    doc = get_user_doc(uid).get()
    if doc.exists:
        return doc.to_dict()
    return None

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
        if user.exists:
            user_dict = user.to_dict()
            user_dict["uid"] = doc_ref.id
            return user_dict
        else:
            return None
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
def exam_id_from_fields(exam_name, exam_type, student_uid, exam_date):
    # exam_date: datetime object
    unique_str = f"{exam_name.strip()}_{exam_type}_{student_uid}_{exam_date.isoformat()}"
    return hashlib.sha256(unique_str.encode()).hexdigest()[:16]

def create_exam(exam_name, exam_type, exam_date, student_uid):
    # Only allow to create exam for own UID, unless admin
    current_uid = st.session_state.get("uid", "")
    if student_uid != current_uid and not is_admin(current_uid):
        raise Exception("You can only create exams for yourself unless you are admin.")
    eid = exam_id_from_fields(exam_name, exam_type, student_uid, exam_date)
    doc_ref = db.collection("exams").document(eid)
    doc_ref.set({
        "name": exam_name.strip(),
        "type": exam_type,
        "date": exam_date,
        "student_uid": student_uid
    })
    return eid

def get_marks_collection(exam_id):
    return db.collection("exams").document(exam_id).collection("marks")

def add_mark(exam_id, uid, subject, mark, total_mark):
    # Only allow to add mark for own UID, unless admin
    current_uid = st.session_state.get("uid", "")
    if uid != current_uid and not is_admin(current_uid):
        raise Exception("You can only submit marks for yourself unless you are admin.")
    marks_col = get_marks_collection(exam_id)
    doc_id = f"{uid}_{subject}"
    marks_col.document(doc_id).set({
        "uid": uid,
        "subject": subject,
        "mark": mark,
        "total_mark": total_mark
    })

def get_marks_for_exam(exam_id):
    marks_col = get_marks_collection(exam_id)
    docs = marks_col.stream()
    marks = {}
    for doc in docs:
        d = doc.to_dict()
        uid = d["uid"]
        subject = d["subject"]
        mark = d.get("mark", 0)
        total_mark = d.get("total_mark", 100)
        if uid not in marks:
            marks[uid] = {}
        marks[uid][subject] = {"mark": mark, "total_mark": total_mark}
    return marks

def get_marks_for_student_exam(exam_id, uid):
    marks_col = get_marks_collection(exam_id)
    docs = marks_col.where("uid", "==", uid).stream()
    marks = {}
    for doc in docs:
        d = doc.to_dict()
        subject = d["subject"]
        mark = d.get("mark", 0)
        total_mark = d.get("total_mark", 100)
        marks[subject] = {"mark": mark, "total_mark": total_mark}
    return marks

def get_user_name(uid):
    data = user_data(uid)
    return data["name"] if data else "Unknown"

def get_exams_for_student(uid, exam_type=None):
    query = db.collection("exams").where("student_uid", "==", uid)
    if exam_type:
        query = query.where("type", "==", exam_type)
    docs = query.stream()
    exams = []
    for doc in docs:
        d = doc.to_dict()
        exams.append((doc.id, d.get("name", doc.id), d.get("date"), d.get("type", "Exam")))
    return sorted(exams, key=lambda x: x[2] if x[2] else datetime.datetime.min)

def get_all_student_exams(exam_type=None):
    query = db.collection("exams")
    if exam_type:
        query = query.where("type", "==", exam_type)
    docs = query.stream()
    exams = []
    for doc in docs:
        d = doc.to_dict()
        exams.append((doc.id, d.get("name", doc.id), d.get("student_uid"), d.get("date"), d.get("type", "Exam")))
    return exams

# --- Session Management ---
def login_user(user):
    st.session_state["uid"] = user.get("uid")
    st.session_state["name"] = user.get("name", "")
    st.session_state["role"] = user.get("role", "user")

def logout_user():
    for key in ["uid", "name", "role"]:
        if key in st.session_state:
            del st.session_state[key]

def logged_in():
    return "uid" in st.session_state

# --- UI Components ---
def signup_page():
    st.title("Sign Up to Markify")
    name = st.text_input("Full Name")
    password = st.text_input("Password", type="password")
    password2 = st.text_input("Confirm Password", type="password")
    if st.button("Sign Up"):
        if not name or not password or not password2:
            st.warning("Please fill all fields.")
            return
        if password != password2:
            st.warning("Passwords do not match.")
            return
        user = create_user(password, name)
        if user:
            login_user(user)
            st.success("Account created and logged in.")
            st.session_state["refresh_trigger"] += 1

def login_page():
    st.title("Login to Markify")
    name = st.text_input("Full Name")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if not name or not password:
            st.warning("Please enter name and password.")
            return
        users_ref = db.collection("users")
        query = users_ref.where("name", "==", name).limit(1).stream()
        user_doc = None
        for doc in query:
            user_doc = doc
            break
        if not user_doc:
            st.error("Invalid name or password.")
            return
        user = user_doc.to_dict()
        if user.get("password_hash") == hash_password(password):
            user["uid"] = user_doc.id
            login_user(user)
            st.success(f"Welcome back, {user.get('name','User')}!")
            st.session_state["refresh_trigger"] += 1
        else:
            st.error("Invalid name or password.")
    st.markdown("[Forgot Password?](#forgot-password-placeholder)")

def forgot_password_page():
    st.title("Forgot Password")
    st.info("This feature is coming soon. Please contact admin to reset your password.")

def dashboard_page():
    _ = st.session_state.get("refresh_trigger", 0)  # For auto-refresh
    st.title(f"🏠 Dashboard - Welcome {st.session_state['name']}")
    with st.container():
        st.markdown("### 📝 Enter Exam/Test Details")
        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])
        with col1:
            exam_name = st.text_input("**Exam/Test Name**", key="v2_exam_name")
        with col2:
            exam_type = st.selectbox("**Exam/Test Type**", ["Exam", "Class Test", "Others"], key="v2_exam_type")
        with col3:
            all_subjects = get_all_subjects()
            if not all_subjects:
                st.info("No subjects available. Please ask admin to add subjects.")
                return
            subject_selected = st.selectbox("**Subject**", all_subjects, key="v2_subject_select")
        with col4:
            mark_input = st.number_input("**Marks**", min_value=0.0, max_value=1000.0, step=0.1, format="%.2f", key="v2_marks_input")
        with col5:
            total_marks_input = st.number_input("**Total Marks**", min_value=1.0, max_value=1000.0, step=0.1, value=100.0, format="%.2f", key="v2_total_marks_input")
        st.markdown("")
        submit_col, _ = st.columns([1, 6])
        with submit_col:
            submitted = st.button("✅ Submit Mark")
        if submitted:
            student_uid = st.session_state["uid"]
            if not exam_name.strip():
                st.warning("Exam/Test name cannot be empty.")
            else:
                now_dt = datetime.datetime.now()
                eid = exam_id_from_fields(exam_name, exam_type, student_uid, now_dt)
                try:
                    # Create exam if it doesn't exist
                    exam_doc = db.collection("exams").document(eid).get()
                    if not exam_doc.exists:
                        create_exam(exam_name, exam_type, now_dt, student_uid)
                    # Check if mark already exists
                    marks_col = get_marks_collection(eid)
                    doc_id = f"{student_uid}_{subject_selected}"
                    marks_col.document(doc_id).set({
                        "uid": student_uid,
                        "subject": subject_selected,
                        "mark": mark_input,
                        "total_mark": total_marks_input
                    })
                    st.success(f"Marks for {subject_selected} in '{exam_name}' ({exam_type}) submitted/updated successfully.")
                    st.session_state["refresh_trigger"] += 1
                except Exception as e:
                    st.error(str(e))
    st.divider()
    st.markdown("### 📊 Your Exams (Grouped by Name & Type)")
    student_uid = st.session_state["uid"]
    all_exams = get_exams_for_student(student_uid)
    grouped = {}
    for eid, ename, edate, etype in all_exams:
        key = (ename, etype)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append((eid, edate))
    if grouped:
        for (ename, etype), exams_list in grouped.items():
            with st.expander(f"**{ename}** ({etype})", expanded=False):
                # Table header using columns
                col_exam, col_type, col_subject, col_marks, col_total = st.columns([2, 1, 2, 1, 1])
                col_exam.markdown("**Exam Name**")
                col_type.markdown("**Type**")
                col_subject.markdown("**Subjects**")
                col_marks.markdown("**Marks**")
                col_total.markdown("**Total Marks**")
                for eid, edate in sorted(exams_list, key=lambda x: x[1] if x[1] else datetime.datetime.min):
                    marks_dict = get_marks_for_student_exam(eid, student_uid)
                    if marks_dict:
                        obtained_marks = []
                        total_marks_list = []
                        subjects = []
                        marks_list = []
                        total_list = []
                        df_rows = []
                        for s, v in marks_dict.items():
                            m = v.get("mark", 0)
                            t = v.get("total_mark", 100)
                            obtained_marks.append(m)
                            total_marks_list.append(t)
                            subjects.append(s)
                            marks_list.append(str(m))
                            total_list.append(str(t))
                            df_rows.append({"Subject": s, "Marks": m, "Total Marks": t})
                        total_obtained = sum(obtained_marks)
                        total_possible = sum(total_marks_list)
                        percentage = (total_obtained / total_possible) * 100 if total_possible > 0 else 0
                        # --- Pass/Fail per subject ---
                        pass_fail_dict = {}
                        for subj, v in marks_dict.items():
                            m = v.get("mark", 0)
                            t = v.get("total_mark", 100)
                            pct = (m / t) * 100 if t > 0 else 0
                            pass_fail_dict[subj] = "Pass ✅" if pct >= 35 else "Fail ❌"
                        # Display as a row
                        col_exam, col_type, col_subject, col_marks, col_total = st.columns([2, 1, 2, 1, 1])
                        col_exam.markdown(f"{ename}<br><sub>{edate.strftime('%Y-%m-%d %H:%M') if edate else 'No Date'}</sub>", unsafe_allow_html=True)
                        col_type.markdown(f"{etype}")
                        col_subject.markdown(", ".join([f"{s} ({pass_fail_dict[s]})" for s in subjects]))
                        col_marks.markdown(", ".join(marks_list))
                        col_total.markdown(", ".join(total_list))
                        # Show details in expander for each exam instance
                        with st.expander(f"Details: {edate.strftime('%Y-%m-%d %H:%M') if edate else 'No Date'}"):
                            df = pd.DataFrame(df_rows)
                            st.dataframe(df, hide_index=True)
                            st.markdown(f"**Total Marks:** {total_obtained} / {total_possible}")
                            st.markdown(f"**Percentage:** {percentage:.2f}%")
                            # Chart: Bar of marks
                            fig = px.bar(df, x="Subject", y="Marks", text="Marks", color="Subject", color_discrete_sequence=px.colors.qualitative.Plotly)
                            fig.update_traces(marker_line_width=2, marker_line_color='black', textposition='outside')
                            max_total = max(total_marks_list) if total_marks_list else 100
                            fig.update_layout(title="Marks by Subject", yaxis=dict(range=[0, max_total]))
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No marks entered yet for this exam instance.")
                    st.divider()
    else:
        st.info("No exams found yet. Enter marks above to create your first exam.")

def leaderboard_page():
    _ = st.session_state.get("refresh_trigger", 0)  # For auto-refresh
    st.title("🏆 Leaderboard")
    st.markdown("#### Select Exam/Test Type")
    exam_type = st.selectbox("Type", ["Exam", "Class Test", "Others"], key="v2_lb_type")
    exams = get_all_student_exams(exam_type)
    if not exams:
        st.info(f"No {exam_type.lower()}s available.")
        return
    grouped = {}
    for eid, ename, student_uid, edate, etype in exams:
        key = (ename, etype)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append((eid, student_uid, edate))
    group_labels = [f"{ename} ({etype})" for (ename, etype) in grouped]
    selected_group = st.selectbox("Select Exam Group", group_labels, key="v2_lb_group")
    group_keys = list(grouped.keys())
    group_idx = group_labels.index(selected_group)
    sel_group_key = group_keys[group_idx]
    sel_group_exams = grouped[sel_group_key]
    for eid, student_uid, edate in sorted(sel_group_exams, key=lambda x: x[2] if x[2] else datetime.datetime.min, reverse=True):
        with st.container():
            st.markdown(f"### {sel_group_key[0]} ({sel_group_key[1]}) - {edate.strftime('%Y-%m-%d %H:%M') if edate else 'No Date'}")
            marks = get_marks_for_exam(eid)
            if not marks:
                st.info("No marks entered yet for this exam instance.")
                continue
            rows = []
            subject_names = set()
            for uid, sub_marks in marks.items():
                obtained_marks = []
                total_marks_list = []
                subj_dict = {}
                for subj, v in sub_marks.items():
                    m = v.get("mark", 0)
                    t = v.get("total_mark", 100)
                    obtained_marks.append(m)
                    total_marks_list.append(t)
                    subj_dict[subj] = m
                    subject_names.add(subj)
                total = sum(obtained_marks)
                total_possible = sum(total_marks_list)
                percentage = (total / total_possible) * 100 if total_possible > 0 else 0
                row = {"uid": uid, "name": get_user_name(uid), "total": total, "percentage": percentage}
                row.update(subj_dict)
                rows.append(row)
            df = pd.DataFrame(rows)
            df = df.sort_values(by="total", ascending=False).reset_index(drop=True)
            df["Rank"] = df.index + 1
            def medal(rank):
                if rank == 1: return "🥇"
                elif rank == 2: return "🥈"
                elif rank == 3: return "🥉"
                else: return ""
            df["Medal"] = df["Rank"].apply(medal)
            # Highlight top 10% (or top 3, whichever is higher)
            highlight_count = max(3, int(len(df) * 0.1))
            highlight_idxs = df.index[:highlight_count]
            # Highlight top 10-20% for conditional formatting
            ten_pct = int(len(df) * 0.1)
            twenty_pct = int(len(df) * 0.2)
            mid_idxs = df.index[ten_pct:twenty_pct]
            show_cols = ["Rank", "Medal", "name", "total", "percentage"] + [col for col in df.columns if col not in ['Rank','Medal','name','total','percentage','uid']]
            def highlight_row(row):
                if row.name in highlight_idxs:
                    return ['background-color: #FFE066; font-weight: bold'] * len(row)
                elif row.name in mid_idxs:
                    return ['background-color: #B2FF66;'] * len(row)
                return [''] * len(row)
            st.markdown("#### 🏅 Leaderboard Table")
            leaderboard_container = st.empty()
            leaderboard_container.dataframe(
                df[show_cols].style.apply(highlight_row, axis=1),
                hide_index=True
            )
            st.markdown("#### 📈 Scores per Subject")
            if len(df) > 0:
                subjects = [col for col in df.columns if col not in ['Rank','Medal','name','total','percentage','uid']]
                df_melt = df.melt(id_vars=['name'], value_vars=subjects, var_name='Subject', value_name='Score')
                fig_bar = px.bar(
                    df_melt,
                    x='name',
                    y='Score',
                    color='Subject',
                    barmode='group',
                    title=f"Scores per Subject - {sel_group_key[0]}",
                    color_discrete_sequence=px.colors.qualitative.Plotly
                )
                fig_bar.update_traces(marker_line_width=1.5, marker_line_color='black')
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("No data available for bar chart.")
            st.divider()

def statistics_improvement_page():
    _ = st.session_state.get("refresh_trigger", 0)  # For auto-refresh
    st.title("📈 Statistics & Improvement")
    st.markdown("#### Your Progress Over Time")
    student_uid = st.session_state["uid"]
    all_exams = get_exams_for_student(student_uid)
    grouped = {}
    for eid, ename, edate, etype in all_exams:
        key = (ename, etype)
        if key not in grouped:
            grouped[key] = []
        grouped[key].append((eid, edate))
    for (ename, etype), exams_list in grouped.items():
        data = []
        for eid, edate in exams_list:
            marks = get_marks_for_student_exam(eid, student_uid)
            if marks:
                total = sum([v["mark"] for v in marks.values()])
                total_possible = sum([v.get("total_mark", 100) for v in marks.values()])
                percentage = (total / total_possible) * 100 if total_possible > 0 else 0
                data.append({"Exam": ename, "Date": edate, "Total Marks": total, "Percentage": percentage, "Type": etype})
        if data:
            df = pd.DataFrame(data)
            df = df.sort_values(by="Date")
            with st.expander(f"📚 {ename} ({etype})", expanded=False):
                stats_container = st.empty()
                fig = px.line(
                    df, x="Date", y="Total Marks", markers=True,
                    title=f"{ename} ({etype}) Improvement Over Time",
                    color_discrete_sequence=px.colors.qualitative.Plotly
                )
                fig.update_traces(marker=dict(size=10, line=dict(width=2, color='DarkSlateGrey')))
                stats_container.plotly_chart(fig, use_container_width=True)
                fig2 = px.line(
                    df, x="Date", y="Percentage", markers=True,
                    title=f"{ename} ({etype}) Percentage Over Time",
                    color_discrete_sequence=px.colors.qualitative.Plotly
                )
                fig2.update_traces(marker=dict(size=10, line=dict(width=2, color='DarkSlateGrey')))
                st.plotly_chart(fig2, use_container_width=True)
                avg = df["Total Marks"].mean()
                best = df["Total Marks"].max()
                avg_pct = df["Percentage"].mean()
                best_pct = df["Percentage"].max()
                st.markdown(f"**Average:** {avg:.2f} &nbsp;&nbsp; **Best:** {best:.2f} &nbsp;&nbsp; **Number of Exams:** {len(df)}")
                st.markdown(f"**Average Percentage:** {avg_pct:.2f}% &nbsp;&nbsp; **Best Percentage:** {best_pct:.2f}%")
        else:
            st.info(f"No marks found for {ename} ({etype}).")
    st.markdown("---")
    st.markdown("#### Subject-wise Progress (Grouped by Exam Name/Type)")
    for (ename, etype), exams_list in grouped.items():
        subj_totals = {}
        subj_counts = {}
        subj_percentages = {}
        subj_total_marks = {}
        for eid, edate in exams_list:
            marks = get_marks_for_student_exam(eid, student_uid)
            for subj, v in marks.items():
                mark = v.get("mark", 0)
                total_mark = v.get("total_mark", 100)
                subj_totals[subj] = subj_totals.get(subj, 0) + mark
                subj_counts[subj] = subj_counts.get(subj, 0) + 1
                subj_percentages[subj] = subj_percentages.get(subj, 0) + ((mark / total_mark) * 100 if total_mark > 0 else 0)
                subj_total_marks[subj] = subj_total_marks.get(subj, 0) + total_mark
        if subj_totals:
            avg_per_subject = {s: subj_totals[s]/subj_counts[s] for s in subj_totals}
            avg_pct_per_subject = {s: subj_percentages[s]/subj_counts[s] for s in subj_percentages}
            best_subjects = sorted(avg_per_subject.items(), key=lambda x: x[1], reverse=True)
            with st.expander(f"📚 {ename} ({etype}) - Average per Subject", expanded=False):
                for subj, avg in best_subjects:
                    st.markdown(f"- **{subj}**: {avg:.2f} (Avg. Percentage: {avg_pct_per_subject[subj]:.2f}%)")
                # Line chart per subject over time
                history = []
                for eid, edate in exams_list:
                    marks = get_marks_for_student_exam(eid, student_uid)
                    for subj, v in marks.items():
                        mark = v.get("mark", 0)
                        total_mark = v.get("total_mark", 100)
                        pct = (mark / total_mark) * 100 if total_mark > 0 else 0
                        history.append({"Date": edate, "Subject": subj, "Marks": mark, "Percentage": pct})
                if history:
                    hdf = pd.DataFrame(history)
                    fig2 = px.line(
                        hdf, x="Date", y="Marks", color="Subject", markers=True,
                        title=f"Subject-wise Progress - {ename} ({etype})",
                        color_discrete_sequence=px.colors.qualitative.Plotly
                    )
                    fig2.update_traces(marker=dict(size=10, line=dict(width=2)))
                    st.plotly_chart(fig2, use_container_width=True)
                    fig3 = px.line(
                        hdf, x="Date", y="Percentage", color="Subject", markers=True,
                        title=f"Subject-wise Percentage - {ename} ({etype})",
                        color_discrete_sequence=px.colors.qualitative.Plotly
                    )
                    fig3.update_traces(marker=dict(size=10, line=dict(width=2)))
                    st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info(f"No subject marks yet for {ename} ({etype}).")

def admin_panel():
    if not is_admin(st.session_state["uid"]):
        st.error("Access denied. Admins only.")
        return
    st.title("🛠️ Admin Panel")
    st.subheader("Add Subject (Global)")
    with st.form("add_subject_form"):
        subject_name = st.text_input("Subject Name")
        submitted = st.form_submit_button("Add Subject")
        if submitted:
            if not subject_name.strip():
                st.warning("Enter a valid subject name.")
            else:
                add_subject(subject_name.strip())
                st.session_state["refresh_trigger"] += 1
    st.divider()
    st.subheader("Export Backup")
    if st.button("Export Backup"):
        # Export exams, marks, subjects, students to CSV
        try:
            # Exams
            exams_docs = db.collection("exams").stream()
            exams_data = []
            marks_data = []
            for exam_doc in exams_docs:
                d = exam_doc.to_dict()
                d['id'] = exam_doc.id
                exams_data.append(d)
                # Get marks for this exam
                marks_docs = get_marks_collection(exam_doc.id).stream()
                for md in marks_docs:
                    m = md.to_dict()
                    m['exam_id'] = exam_doc.id
                    marks_data.append(m)
            # Subjects
            subjects_docs = db.collection("subjects").stream()
            subjects_data = [doc.to_dict() for doc in subjects_docs]
            # Students/Users
            users_docs = db.collection("users").stream()
            users_data = []
            for ud in users_docs:
                u = ud.to_dict()
                u['uid'] = ud.id
                users_data.append(u)
            # Create a single CSV with all sections separated by headers
            import csv
            with open("markify_backup.csv", "w", newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["-- Exams --"])
                if exams_data:
                    writer.writerow(exams_data[0].keys())
                    for row in exams_data:
                        writer.writerow([row.get(k, "") for k in exams_data[0].keys()])
                writer.writerow([])
                writer.writerow(["-- Marks --"])
                if marks_data:
                    writer.writerow(marks_data[0].keys())
                    for row in marks_data:
                        writer.writerow([row.get(k, "") for k in marks_data[0].keys()])
                writer.writerow([])
                writer.writerow(["-- Subjects --"])
                if subjects_data:
                    writer.writerow(subjects_data[0].keys())
                    for row in subjects_data:
                        writer.writerow([row.get(k, "") for k in subjects_data[0].keys()])
                writer.writerow([])
                writer.writerow(["-- Students --"])
                if users_data:
                    writer.writerow(users_data[0].keys())
                    for row in users_data:
                        writer.writerow([row.get(k, "") for k in users_data[0].keys()])
            st.success("Backup exported successfully to markify_backup.csv.")
        except Exception as e:
            st.error(f"Failed to export backup: {e}")

def account_settings():
    st.title("Account Settings")
    st.subheader("Update Name")
    new_name = st.text_input("New Name", value=st.session_state["name"])
    if st.button("Update Name"):
        if not new_name.strip():
            st.warning("Name cannot be empty.")
        else:
            update_name(st.session_state["uid"], new_name.strip())
            st.session_state["name"] = new_name.strip()
    st.divider()
    st.subheader("Change Password")
    old_password = st.text_input("Current Password", type="password")
    new_password = st.text_input("New Password", type="password")
    new_password2 = st.text_input("Confirm New Password", type="password")
    if st.button("Change Password"):
        if not old_password or not new_password or not new_password2:
            st.warning("Please fill all password fields.")
            return
        data = user_data(st.session_state["uid"])
        if data and data.get("password_hash") == hash_password(old_password):
            update_password(st.session_state["uid"], new_password)
        else:
            st.error("Current password is incorrect.")

# --- Main App Flow ---
def main():
    st.set_page_config(page_title="Markify v2", layout="wide")
    st.sidebar.title("Markify")
    sidebar_tabs = [
        "🏠 Dashboard",
        "🏆 Leaderboard",
        "📈 Statistics & Improvement",
        "⚙️ Account Settings"
    ]
    if logged_in():
        role = st.session_state.get("role", "user")
        st.sidebar.markdown("---")
        st.sidebar.markdown(
            f"**👤 Logged in as:** <span style='color: #2186eb; font-weight: bold'>{st.session_state['name']}</span>",
            unsafe_allow_html=True
        )
        st.sidebar.markdown(
            f"**Role:** {'🛡️ Admin' if is_admin(st.session_state['uid']) else '🎓 Student'}"
        )
        st.sidebar.divider()
        st.sidebar.markdown("### 📂 Navigation")
        if is_admin(st.session_state["uid"]):
            sidebar_tabs.append("🛠️ Admin Panel")
        sidebar_tabs.append("🚪 Logout")
        page = st.sidebar.radio("Navigate", sidebar_tabs)
        st.sidebar.divider()
    else:
        st.sidebar.markdown("---")
        page = st.sidebar.radio("Navigate", ["🔑 Login", "📝 Sign Up", "❓ Forgot Password"])
    # Map icons to function
    page_map = {
        "🏠 Dashboard": dashboard_page,
        "🏆 Leaderboard": leaderboard_page,
        "📈 Statistics & Improvement": statistics_improvement_page,
        "⚙️ Account Settings": account_settings,
        "🛠️ Admin Panel": admin_panel,
        "🚪 Logout": None,
        "🔑 Login": login_page,
        "📝 Sign Up": signup_page,
        "❓ Forgot Password": forgot_password_page
    }
    # Remove emoji for internal function calls
    if page in page_map and page_map[page]:
        page_map[page]()
    elif page == "🚪 Logout":
        logout_user()
        st.success("Logged out successfully.")
        st.session_state["refresh_trigger"] += 1

if __name__ == "__main__":
    main()
