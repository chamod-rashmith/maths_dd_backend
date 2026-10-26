"""
Admin Management Dashboard for Maths DD (Combined Mathematics).
Allows seamless management of Subjects, Syllabus Lessons, and Study Notes (Markdown & PDF).
"""

import streamlit as st
import requests

API_BASE_URL = "http://127.0.0.1:8000/api/v1"
ADMIN_AUTH_HEADER = {"Authorization": "Bearer dev-admin"}

st.set_page_config(
    page_title="Maths DD - Admin Studio",
    page_icon="📐",
    layout="wide",
)

st.title("📐 Maths DD - Curriculum & Study Notes Admin")
st.caption("Direct management interface for Subjects, Lessons, and Study Notes connected to FastAPI & PostgreSQL.")

# Sidebar navigation
tab = st.sidebar.radio(
    "Navigation",
    ["📚 Subjects Manager", "📖 Lessons Manager", "📝 Study Notes Manager", "👤 Admin Users & Roles"],
)


# Helper functions to fetch data
def fetch_subjects():
    try:
        res = requests.get(f"{API_BASE_URL}/curriculum/subjects", timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        st.error(f"Failed to connect to backend: {e}")
    return []


def fetch_lessons(subject_code=None):
    try:
        params = {"subject_code": subject_code} if subject_code else {}
        res = requests.get(f"{API_BASE_URL}/curriculum/lessons", params=params, timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        st.error(f"Failed to fetch lessons: {e}")
    return []


def fetch_study_notes(subject_id=None):
    try:
        params = {"subject_id": subject_id} if subject_id else {}
        res = requests.get(f"{API_BASE_URL}/study-notes/", params=params, timeout=5)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        st.error(f"Failed to fetch study notes: {e}")
    return []


# ==============================================================================
# TAB 1: SUBJECTS MANAGER
# ==============================================================================
if tab == "📚 Subjects Manager":
    st.subheader("Manage Curriculum Subjects")

    subjects = fetch_subjects()

    col1, col2 = st.columns([1, 1.5])

    with col1:
        st.markdown("### ➕ Add / Update Subject")
        with st.form("subject_form"):
            subj_name = st.text_input("Subject Name *", placeholder="e.g. Applied Mathematics")
            subj_sinhala = st.text_input("Sinhala Name", placeholder="e.g. ප්‍රායෝගික ගණිතය")
            subj_code = st.text_input("Subject Code *", placeholder="e.g. AMAT, PMAT").upper()
            subj_order = st.number_input("Order Index", min_value=1, value=1)
            subj_desc = st.text_area("Description", placeholder="Brief description...")
            
            submitted = st.form_submit_button("Save Subject", use_container_width=True)
            if submitted:
                if not subj_name or not subj_code:
                    st.warning("Please fill in Subject Name and Code.")
                else:
                    payload = {
                        "name": subj_name.strip(),
                        "sinhala_name": subj_sinhala.strip(),
                        "code": subj_code.strip(),
                        "order_index": subj_order,
                        "description": subj_desc.strip(),
                    }
                    res = requests.post(
                        f"{API_BASE_URL}/curriculum/subjects",
                        json=payload,
                        headers=ADMIN_AUTH_HEADER,
                    )
                    if res.status_code in (200, 201):
                        st.success(f"Subject '{subj_name}' saved successfully!")
                        st.rerun()
                    else:
                        st.error(f"Error: {res.text}")

    with col2:
        st.markdown("### 📋 Active Subjects")
        if subjects:
            for s in subjects:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1, 1])
                    c1.markdown(f"**[{s['code']}] {s['name']}** ({s.get('sinhala_name') or ''})")
                    c1.caption(f"ID: `{s['id']}` | Order: {s['order_index']}")
                    if s.get('description'):
                        c1.text(s['description'])
                    if c3.button("🗑️ Delete", key=f"del_subj_{s['id']}"):
                        d_res = requests.delete(
                            f"{API_BASE_URL}/curriculum/subjects/{s['id']}",
                            headers=ADMIN_AUTH_HEADER,
                        )
                        if d_res.status_code == 200:
                            st.success(f"Deleted {s['name']}")
                            st.rerun()
                        else:
                            st.error(f"Delete failed: {d_res.text}")
        else:
            st.info("No subjects found in database.")


# ==============================================================================
# TAB 2: LESSONS MANAGER
# ==============================================================================
elif tab == "📖 Lessons Manager":
    st.subheader("Manage Syllabus Lessons")

    subjects = fetch_subjects()
    if not subjects:
        st.warning("Please create at least one Subject first!")
    else:
        subject_map = {f"[{s['code']}] {s['name']}": s['id'] for s in subjects}
        subject_code_map = {s['id']: s['code'] for s in subjects}

        col1, col2 = st.columns([1, 1.5])

        with col1:
            st.markdown("### ➕ Add Syllabus Lesson")
            with st.form("lesson_form"):
                selected_subj_label = st.selectbox("Select Subject *", list(subject_map.keys()))
                selected_subj_id = subject_map[selected_subj_label]

                lesson_title = st.text_input("Lesson Title (English) *", placeholder="e.g. Mathematical Induction")
                lesson_sinhala = st.text_input("Lesson Title (Sinhala)", placeholder="e.g. ගණිත අභ්‍යුහනය")
                lesson_order = st.number_input("Order Index", min_value=1, value=1)
                lesson_desc = st.text_area("Lesson Description", placeholder="Outline of concepts...")

                submit_lesson = st.form_submit_button("Save Lesson", use_container_width=True)
                if submit_lesson:
                    if not lesson_title:
                        st.warning("Please provide a lesson title.")
                    else:
                        payload = {
                            "subject_id": selected_subj_id,
                            "title": lesson_title.strip(),
                            "sinhala_title": lesson_sinhala.strip(),
                            "order_index": lesson_order,
                            "description": lesson_desc.strip(),
                        }
                        res = requests.post(
                            f"{API_BASE_URL}/curriculum/lessons",
                            json=payload,
                            headers=ADMIN_AUTH_HEADER,
                        )
                        if res.status_code in (200, 201):
                            st.success(f"Lesson '{lesson_title}' added successfully!")
                            st.rerun()
                        else:
                            st.error(f"Error: {res.text}")

        with col2:
            st.markdown("### 📋 Filter Lessons by Subject")
            filter_subj_label = st.selectbox("Filter Subject:", ["All Subjects"] + list(subject_map.keys()))
            
            filter_code = None
            if filter_subj_label != "All Subjects":
                sid = subject_map[filter_subj_label]
                filter_code = subject_code_map.get(sid)

            lessons = fetch_lessons(subject_code=filter_code)

            if lessons:
                st.caption(f"Showing {len(lessons)} lesson(s)")
                for l in lessons:
                    with st.container(border=True):
                        c1, c2 = st.columns([4, 1])
                        c1.markdown(f"**#{l['order_index']} - {l['title']}** ({l.get('sinhala_title') or ''})")
                        c1.caption(f"ID: `{l['id']}` | Subject ID: `{l['subject_id']}`")
                        if l.get('description'):
                            c1.text(l['description'])

                        if c2.button("🗑️ Delete", key=f"del_les_{l['id']}"):
                            d_res = requests.delete(
                                f"{API_BASE_URL}/curriculum/lessons/{l['id']}",
                                headers=ADMIN_AUTH_HEADER,
                            )
                            if d_res.status_code == 200:
                                st.success(f"Deleted {l['title']}")
                                st.rerun()
                            else:
                                st.error(f"Delete failed: {d_res.text}")
            else:
                st.info("No lessons found for selected filter.")


# ==============================================================================
# TAB 3: STUDY NOTES MANAGER
# ==============================================================================
elif tab == "📝 Study Notes Manager":
    st.subheader("Manage Study Notes (Markdown & Cloud PDF)")

    subjects = fetch_subjects()
    if not subjects:
        st.warning("Please create at least one Subject first!")
    else:
        subject_map = {f"[{s['code']}] {s['name']}": s['id'] for s in subjects}

        tab_action = st.radio("Action:", ["➕ Create New Study Note", "📚 Browse & View Existing Notes"], horizontal=True)

        if tab_action == "➕ Create New Study Note":
            with st.form("create_note_form"):
                col_a, col_b = st.columns(2)
                with col_a:
                    selected_subj_label = st.selectbox("Subject *", list(subject_map.keys()))
                    selected_subj_id = subject_map[selected_subj_label]
                    note_title = st.text_input("Note Title *", placeholder="e.g. Complete Circular Motion Guide")
                    note_author = st.text_input("Author / Teacher", value="Maths DD Academic Team")
                    note_order = st.number_input("Sort Order", min_value=0, value=1)
                
                with col_b:
                    # Fetch lessons for selected subject
                    current_lessons = fetch_lessons(subject_code=None)
                    subject_lessons = [l for l in current_lessons if l.get('subject_id') == selected_subj_id]
                    lesson_opts = {"None (General Subject Note)": None}
                    for l in subject_lessons:
                        lesson_opts[f"{l['order_index']}. {l['title']}"] = l['id']

                    selected_lesson_label = st.selectbox("Associated Lesson (Optional)", list(lesson_opts.keys()))
                    selected_lesson_id = lesson_opts[selected_lesson_label]

                    note_desc = st.text_area("Brief Summary / Description", placeholder="Short overview for the card...")
                    is_premium = st.checkbox("🔒 Premium / PRO Only Note", value=False)

                st.markdown("---")
                st.markdown("#### 📄 Content Format Selection (Mutually Exclusive)")
                content_mode = st.radio("Select Content Type:", ["Markdown / LaTeX Notes", "PDF Document (Storage Path)"], horizontal=True)

                content_text = ""
                pdf_url = ""

                if content_mode == "Markdown / LaTeX Notes":
                    content_text = st.text_area(
                        "Markdown / LaTeX Content *",
                        height=250,
                        placeholder="# Theory\n\nWrite your notes here with LaTeX:\n$$\\int x^n dx = \\frac{x^{n+1}}{n+1} + C$$",
                    )
                else:
                    st.info("💡 Enter the Cloud Storage relative path (e.g. `study_notes/applied/circular_motion.pdf`).")
                    pdf_url = st.text_input(
                        "Cloud Storage PDF Path or URL *",
                        placeholder="study_notes/pure/induction_summary.pdf",
                    )

                save_note = st.form_submit_button("🚀 Publish Study Note", use_container_width=True)
                if save_note:
                    if not note_title:
                        st.warning("Please provide a note title.")
                    elif content_mode == "Markdown / LaTeX Notes" and not content_text.strip():
                        st.warning("Please provide Markdown content.")
                    elif content_mode == "PDF Document (Storage Path)" and not pdf_url.strip():
                        st.warning("Please provide a PDF storage path.")
                    else:
                        payload = {
                            "title": note_title.strip(),
                            "subject_id": selected_subj_id,
                            "lesson_id": selected_lesson_id,
                            "description": note_desc.strip(),
                            "content_text": content_text.strip() if content_mode == "Markdown / LaTeX Notes" else None,
                            "pdf_url": pdf_url.strip() if content_mode != "Markdown / LaTeX Notes" else None,
                            "is_premium": is_premium,
                            "order_index": note_order,
                            "author": note_author.strip(),
                        }
                        res = requests.post(
                            f"{API_BASE_URL}/study-notes/",
                            json=payload,
                            headers=ADMIN_AUTH_HEADER,
                        )
                        if res.status_code in (200, 201):
                            st.success(f"🎉 Note '{note_title}' published successfully with auto-generated UUID!")
                            st.rerun()
                        else:
                            st.error(f"Error publishing note: {res.text}")

        else:
            # Browse existing notes
            st.markdown("### 📋 Published Study Notes")
            filter_subj_label = st.selectbox("Filter by Subject:", ["All Subjects"] + list(subject_map.keys()))
            filter_subj_id = None if filter_subj_label == "All Subjects" else subject_map[filter_subj_label]

            notes = fetch_study_notes(subject_id=filter_subj_id)

            if notes:
                for n in notes:
                    with st.container(border=True):
                        c1, c2, c3 = st.columns([3, 1, 1])
                        c1.markdown(f"**{n['title']}**")
                        c1.caption(f"Type: **`{n['content_type'].upper()}`** | Subject: {n.get('subject_name')} | Author: {n.get('author') or 'N/A'}")
                        if n.get('description'):
                            c1.text(n['description'])
                        if n.get('is_premium'):
                            c1.markdown("🔒 *PRO Exclusive*")

                        # View Full Detail on-demand
                        if c2.button("👁️ View Full", key=f"view_note_{n['id']}"):
                            detail_res = requests.get(f"{API_BASE_URL}/study-notes/{n['id']}")
                            if detail_res.status_code == 200:
                                detail = detail_res.json()
                                st.session_state[f"detail_{n['id']}"] = detail

                        if c3.button("🗑️ Delete", key=f"del_note_{n['id']}"):
                            d_res = requests.delete(
                                f"{API_BASE_URL}/study-notes/{n['id']}",
                                headers=ADMIN_AUTH_HEADER,
                            )
                            if d_res.status_code == 200:
                                st.success("Note deleted!")
                                st.rerun()
                            else:
                                st.error(f"Delete failed: {d_res.text}")

                        # Show detail expansion if clicked
                        if f"detail_{n['id']}" in st.session_state:
                            d = st.session_state[f"detail_{n['id']}"]
                            with st.expander("📄 On-Demand Hydrated Content", expanded=True):
                                if d.get('content_type') == 'markdown':
                                    st.markdown(d.get('content_text') or '')
                                else:
                                    st.info(f"**Signed PDF URL (1-Hour Expiry):**")
                                    st.code(d.get('pdf_url') or '')
                                    if d.get('pdf_url'):
                                        st.link_button("Open Signed PDF in Browser", d['pdf_url'])
            else:
                st.info("No study notes published yet.")


# ==============================================================================
# TAB 4: ADMIN USERS & ROLES
# ==============================================================================
elif tab == "👤 Admin Users & Roles":
    st.subheader("Database Users & Admin Privileges")
    st.caption("Inspect and promote users to ADMIN or EDITOR directly.")

    try:
        from app.core.database import get_db_connection
        import asyncio

        async def get_all_users():
            conn = await get_db_connection()
            rows = await conn.fetch("SELECT uid, email, name, role, is_premium, created_at FROM users ORDER BY created_at DESC;")
            await conn.close()
            return [dict(r) for r in rows]

        users = asyncio.run(get_all_users())
        if users:
            st.dataframe(users, use_container_width=True)
            
            st.markdown("### 👑 Promote User to ADMIN")
            with st.form("promote_user_form"):
                user_email = st.selectbox("Select User by Email:", [u['email'] for u in users])
                new_role = st.selectbox("Assign Role:", ["ADMIN", "EDITOR", "USER"])
                
                promote_btn = st.form_submit_button("Update Role", use_container_width=True)
                if promote_btn:
                    async def update_role():
                        conn = await get_db_connection()
                        await conn.execute("UPDATE users SET role = $1 WHERE email = $2;", new_role, user_email)
                        await conn.close()

                    asyncio.run(update_role())
                    st.success(f"Role for '{user_email}' updated to **{new_role}**!")
                    st.rerun()
        else:
            st.info("No users found in database. Once a user logs into the app, they will appear here.")
    except Exception as e:
        st.error(f"Database error: {e}")
