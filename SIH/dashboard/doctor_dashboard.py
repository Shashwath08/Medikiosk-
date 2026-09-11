"""
MediKiosk - Doctor + Triage Dashboard  (Member 5)
--------------------------------------------------
A self-contained Tkinter desktop app for the doctor-facing side of the
MediKiosk SIH project.

Flow:
  1. Doctor logs in.
  2. Doctor sees the patient queue (red-flag patients pinned to the top
     and highlighted).
  3. Selecting a patient loads their AI-generated clinical summary:
        - Chief Complaint + HPI
        - Past medical / surgical / family / personal history
        - Medication & allergy information
        - Medical document timeline
        - Red-flag / triage alerts
  4. For every section the doctor can Edit, Confirm, or Reject the
     AI-generated text.
  5. "Finalize Consultation Summary" compiles everything the doctor has
     confirmed/edited into one consultation-ready note, saves it, and
     marks the visit as consulted (removing it from the active queue).

Data lives in a local SQLite file (medikiosk.db) created next to this
script the first time it runs, pre-seeded with sample patients so the
dashboard is demo-ready out of the box. Swap `get_connection()` for a
real HIS/ABDM-backed connection when wiring this into the full system.
"""

import os
import sqlite3
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "medikiosk.db")

SECTIONS = ["chief_complaint_hpi", "history", "medications_allergies"]
SECTION_LABELS = {
    "chief_complaint_hpi": "Chief Complaint & HPI",
    "history": "Past Medical / Surgical / Family / Personal History",
    "medications_allergies": "Medications & Allergies",
}
STATUS_COLORS = {
    "ai_generated": "#b45309",   # amber
    "confirmed": "#15803d",      # green
    "edited": "#1d4ed8",         # blue
    "rejected": "#b91c1c",       # red
}
STATUS_LABELS = {
    "ai_generated": "AI Generated \u2022 Pending Review",
    "confirmed": "Confirmed by Doctor",
    "edited": "Edited by Doctor",
    "rejected": "Rejected by Doctor",
}

# ----------------------------------------------------------------------
# DATABASE
# ----------------------------------------------------------------------

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create tables if missing and seed sample data on first run."""
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            specialization TEXT
        );

        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            sex TEXT,
            contact TEXT,
            abha_id TEXT
        );

        CREATE TABLE IF NOT EXISTS visits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL REFERENCES patients(id),
            token_no TEXT,
            status TEXT DEFAULT 'waiting',       -- waiting | consulted
            priority TEXT DEFAULT 'normal',      -- normal | red_flag
            chief_complaint TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS history (
            visit_id INTEGER PRIMARY KEY REFERENCES visits(id),
            hpi TEXT,
            past_medical TEXT,
            past_surgical TEXT,
            drug_allergy TEXT,
            family_history TEXT,
            personal_history TEXT,
            ros TEXT
        );

        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL REFERENCES patients(id),
            doc_type TEXT,
            doc_date TEXT,
            summary TEXT
        );

        CREATE TABLE IF NOT EXISTS red_flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visit_id INTEGER NOT NULL REFERENCES visits(id),
            flag_text TEXT,
            severity TEXT   -- high | medium
        );

        CREATE TABLE IF NOT EXISTS review_status (
            visit_id INTEGER NOT NULL REFERENCES visits(id),
            section TEXT NOT NULL,
            status TEXT DEFAULT 'ai_generated',
            PRIMARY KEY (visit_id, section)
        );

        CREATE TABLE IF NOT EXISTS final_summary (
            visit_id INTEGER PRIMARY KEY REFERENCES visits(id),
            summary_text TEXT,
            finalized_at TEXT
        );
        """
    )
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM doctors")
    if cur.fetchone()[0] == 0:
        _seed_sample_data(conn)

    conn.close()


def _seed_sample_data(conn):
    cur = conn.cursor()
    now = datetime.datetime.now()

    cur.executemany(
        "INSERT INTO doctors (username, password, full_name, specialization) VALUES (?, ?, ?, ?)",
        [
            ("dr.mehta", "doctor123", "Dr. Anjali Mehta", "General Medicine"),
            ("dr.rao", "doctor123", "Dr. Suresh Rao", "Cardiology"),
        ],
    )

    patients = [
        ("Ramesh Kumar", 58, "M", "9876500011", "ABHA-1001-2233"),
        ("Sunita Devi", 34, "F", "9876500022", "ABHA-1002-4455"),
        ("Aarav Sharma", 7, "M", "9876500033", "ABHA-1003-6677"),
        ("Fatima Sheikh", 45, "F", "9876500044", "ABHA-1004-8899"),
        ("Bhavesh Patel", 67, "M", "9876500055", "ABHA-1005-0011"),
    ]
    cur.executemany(
        "INSERT INTO patients (name, age, sex, contact, abha_id) VALUES (?, ?, ?, ?, ?)",
        patients,
    )

    visits = [
        # patient_id, token_no, status, priority, chief_complaint
        (1, "T-101", "waiting", "red_flag", "Sudden chest pain radiating to left arm since 1 hour"),
        (2, "T-102", "waiting", "normal", "Fever and body ache for 3 days"),
        (3, "T-103", "waiting", "normal", "Cough and cold for 1 week"),
        (4, "T-104", "waiting", "red_flag", "Severe headache with blurred vision since morning"),
        (5, "T-105", "waiting", "normal", "Follow-up for diabetes management"),
    ]
    for v in visits:
        cur.execute(
            """INSERT INTO visits (patient_id, token_no, status, priority, chief_complaint, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (*v, now.strftime("%Y-%m-%d %H:%M")),
        )

    histories = {
        1: dict(
            hpi=("Patient reports sudden onset central chest pain, crushing in character, "
                 "radiating to the left arm and jaw, started ~1 hour ago while at rest. "
                 "Associated with sweating and breathlessness. No relief with rest so far."),
            past_medical="Hypertension (8 years), Type 2 Diabetes Mellitus (5 years).",
            past_surgical="None reported.",
            drug_allergy="Tab. Telmisartan 40mg OD, Tab. Metformin 500mg BD. No known drug allergies.",
            family_history="Father had a myocardial infarction at age 60.",
            personal_history="Smoker - 10 cigarettes/day for 20 years. Occasional alcohol use.",
            ros="Denies fever, vomiting. Reports mild dizziness.",
        ),
        2: dict(
            hpi=("Fever, intermittent, low to moderate grade for 3 days, associated with "
                 "generalized body ache and mild headache. No rash, no chills/rigors reported."),
            past_medical="No significant past medical history.",
            past_surgical="Appendectomy in 2018.",
            drug_allergy="Taking OTC paracetamol for fever. Allergic to Penicillin (rash).",
            family_history="Non-contributory.",
            personal_history="Non-smoker, non-alcoholic. Homemaker.",
            ros="No cough, no breathlessness, mild loss of appetite.",
        ),
        3: dict(
            hpi="Dry cough and nasal congestion for 1 week, mild in intensity, no fever currently.",
            past_medical="No known chronic illness. Up to date on immunizations per parent.",
            past_surgical="None.",
            drug_allergy="No regular medication. No known allergies.",
            family_history="Non-contributory.",
            personal_history="Attends school; sibling recently had similar symptoms.",
            ros="No ear pain, no breathlessness, appetite normal.",
        ),
        4: dict(
            hpi=("Severe throbbing headache since this morning, holocranial, associated with "
                 "blurred vision and one episode of vomiting. No history of trauma."),
            past_medical="Migraine (diagnosed 3 years ago), on and off medication.",
            past_surgical="None reported.",
            drug_allergy="Occasional Sumatriptan for migraine. No known drug allergies.",
            family_history="Mother has hypertension.",
            personal_history="Non-smoker, non-alcoholic. Works long hours on computer.",
            ros="No fever, no neck stiffness reported by patient.",
        ),
        5: dict(
            hpi="Routine follow-up visit for diabetes management, no new complaints today.",
            past_medical="Type 2 Diabetes Mellitus (10 years), Hyperlipidemia.",
            past_surgical="Cataract surgery (right eye) in 2021.",
            drug_allergy="Tab. Metformin 1000mg BD, Tab. Atorvastatin 10mg OD. No known allergies.",
            family_history="Both parents had diabetes.",
            personal_history="Non-smoker, non-alcoholic. Follows a diabetic diet.",
            ros="No polyuria/polydipsia currently, vision stable.",
        ),
    }
    for visit_id, h in histories.items():
        cur.execute(
            """INSERT INTO history
               (visit_id, hpi, past_medical, past_surgical, drug_allergy, family_history, personal_history, ros)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                visit_id, h["hpi"], h["past_medical"], h["past_surgical"],
                h["drug_allergy"], h["family_history"], h["personal_history"], h["ros"],
            ),
        )
        for section in SECTIONS:
            cur.execute(
                "INSERT INTO review_status (visit_id, section, status) VALUES (?, ?, 'ai_generated')",
                (visit_id, section),
            )

    documents = [
        (1, "Prescription", "2026-06-10", "Cardiology OPD prescription - Telmisartan, Metformin refill."),
        (1, "Lab Report", "2026-06-10", "Lipid profile - LDL 168 mg/dL (high), HDL 38 mg/dL (low)."),
        (2, "Lab Report", "2026-09-05", "CBC - WBC count mildly elevated, suggestive of viral infection."),
        (4, "Discharge Summary", "2023-11-02", "Admitted for migraine with aura, discharged stable on prophylaxis."),
        (5, "Lab Report", "2026-08-20", "HbA1c 7.8%, Fasting glucose 142 mg/dL."),
        (5, "Prescription", "2026-08-20", "Metformin 1000mg BD, Atorvastatin 10mg OD continued."),
    ]
    cur.executemany(
        "INSERT INTO documents (patient_id, doc_type, doc_date, summary) VALUES (?, ?, ?, ?)",
        documents,
    )

    red_flags = [
        (1, "Acute chest pain with diaphoresis and breathlessness - possible ACS. Immediate evaluation required.", "high"),
        (4, "Sudden severe headache with visual disturbance - rule out raised ICP / neurological emergency.", "high"),
    ]
    cur.executemany(
        "INSERT INTO red_flags (visit_id, flag_text, severity) VALUES (?, ?, ?)",
        red_flags,
    )

    conn.commit()


# ----------------------------------------------------------------------
# LOGIN WINDOW
# ----------------------------------------------------------------------

class LoginWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("MediKiosk - Doctor Login")
        self.root.configure(bg="#f0f9ff")
        self.root.geometry("420x420")
        self.root.resizable(False, False)

        self.username = tk.StringVar()
        self.password = tk.StringVar()

        card = tk.Frame(self.root, bg="white", bd=0)
        card.place(relx=0.5, rely=0.5, anchor="center", width=340, height=340)

        tk.Label(card, text="\U0001FA7A", font=("Segoe UI Emoji", 34), bg="white").pack(pady=(25, 0))
        tk.Label(card, text="MediKiosk", font=("Helvetica", 20, "bold"), bg="white", fg="#0f172a").pack()
        tk.Label(card, text="Doctor + Triage Dashboard", font=("Helvetica", 11), bg="white", fg="#475569").pack(pady=(0, 15))

        tk.Label(card, text="Username", font=("Helvetica", 10), bg="white", anchor="w").pack(fill="x", padx=40)
        tk.Entry(card, textvariable=self.username, font=("Helvetica", 11)).pack(fill="x", padx=40, pady=(2, 10))

        tk.Label(card, text="Password", font=("Helvetica", 10), bg="white", anchor="w").pack(fill="x", padx=40)
        tk.Entry(card, textvariable=self.password, show="*", font=("Helvetica", 11)).pack(fill="x", padx=40, pady=(2, 15))

        ttk.Button(card, text="Login", command=self.login).pack(fill="x", padx=40, pady=(5, 0))
        tk.Label(card, text="Demo login: dr.mehta / doctor123", font=("Helvetica", 8), bg="white", fg="#94a3b8").pack(pady=(15, 0))

        self.root.bind("<Return>", lambda e: self.login())

    def login(self):
        uname = self.username.get().strip()
        pwd = self.password.get().strip()
        if not uname or not pwd:
            messagebox.showerror("Error", "Please enter both username and password.")
            return

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, full_name, specialization FROM doctors WHERE username=? AND password=?",
            (uname, pwd),
        )
        row = cur.fetchone()
        conn.close()

        if row:
            doctor = {"id": row[0], "name": row[1], "specialization": row[2]}
            self.root.destroy()
            DashboardWindow(doctor)
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")


# ----------------------------------------------------------------------
# DASHBOARD WINDOW
# ----------------------------------------------------------------------

class DashboardWindow:
    def __init__(self, doctor):
        self.doctor = doctor
        self.current_visit_id = None
        self.current_patient_name = None
        self.section_widgets = {}   # section -> {"text": Text, "status_label": Label}

        self.win = tk.Tk()
        self.win.title("MediKiosk - Doctor Dashboard")
        self.win.geometry("1300x760")
        self.win.configure(bg="#f0f9ff")

        self._build_header()
        self._build_body()
        self.refresh_queue()

        self.win.mainloop()

    # ---------------- header ----------------

    def _build_header(self):
        header = tk.Frame(self.win, bg="#0f172a", height=60)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        tk.Label(
            header, text="  MediKiosk \u2013 Triage & Consultation Dashboard",
            font=("Helvetica", 15, "bold"), bg="#0f172a", fg="white",
        ).pack(side="left", padx=10)

        tk.Label(
            header,
            text=f"{self.doctor['name']}  \u2022  {self.doctor.get('specialization') or ''}  ",
            font=("Helvetica", 11), bg="#0f172a", fg="#cbd5e1",
        ).pack(side="right", padx=15)

    # ---------------- body layout ----------------

    def _build_body(self):
        body = tk.Frame(self.win, bg="#f0f9ff")
        body.pack(fill="both", expand=True, padx=12, pady=12)

        left = tk.Frame(body, bg="#f0f9ff", width=380)
        left.pack(side="left", fill="y", padx=(0, 12))
        left.pack_propagate(False)

        right = tk.Frame(body, bg="#f0f9ff")
        right.pack(side="left", fill="both", expand=True)

        self._build_queue_panel(left)
        self._build_summary_panel(right)

    # ---------------- queue panel ----------------

    def _build_queue_panel(self, parent):
        tk.Label(parent, text="Patient Queue", font=("Helvetica", 13, "bold"),
                 bg="#f0f9ff", fg="#0f172a", anchor="w").pack(fill="x", pady=(0, 6))

        cols = ("Token", "Name", "Age/Sex", "Chief Complaint")
        self.queue_tree = ttk.Treeview(parent, columns=cols, show="headings", selectmode="browse", height=22)
        for c, w in zip(cols, (55, 100, 65, 160)):
            self.queue_tree.heading(c, text=c)
            self.queue_tree.column(c, width=w, anchor="w")
        self.queue_tree.pack(fill="both", expand=True)
        self.queue_tree.tag_configure("red_flag", background="#fee2e2", foreground="#7f1d1d")
        self.queue_tree.tag_configure("normal", background="white", foreground="#0f172a")
        self.queue_tree.bind("<<TreeviewSelect>>", self.on_select_patient)

        ttk.Button(parent, text="\u21bb Refresh Queue", command=self.refresh_queue).pack(fill="x", pady=(8, 0))

    def refresh_queue(self):
        for row in self.queue_tree.get_children():
            self.queue_tree.delete(row)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT v.id, v.token_no, p.name, p.age, p.sex, v.chief_complaint, v.priority
               FROM visits v JOIN patients p ON p.id = v.patient_id
               WHERE v.status = 'waiting'
               ORDER BY CASE v.priority WHEN 'red_flag' THEN 0 ELSE 1 END, v.id"""
        )
        rows = cur.fetchall()
        conn.close()

        for visit_id, token, name, age, sex, complaint, priority in rows:
            tag = "red_flag" if priority == "red_flag" else "normal"
            label = ("\u26a0 " if priority == "red_flag" else "") + token
            self.queue_tree.insert(
                "", tk.END, iid=str(visit_id), tags=(tag,),
                values=(label, name, f"{age}/{sex}", complaint),
            )

    # ---------------- summary panel ----------------

    def _build_summary_panel(self, parent):
        self.summary_placeholder = tk.Label(
            parent, text="Select a patient from the queue to view their clinical summary.",
            font=("Helvetica", 12), bg="#f0f9ff", fg="#64748b",
        )
        self.summary_placeholder.pack(expand=True)

        self.summary_container = tk.Frame(parent, bg="#f0f9ff")

        # patient banner
        self.patient_banner = tk.Label(
            self.summary_container, text="", font=("Helvetica", 14, "bold"),
            bg="#f0f9ff", fg="#0f172a", anchor="w",
        )
        self.patient_banner.pack(fill="x", pady=(0, 4))

        self.red_flag_banner = tk.Label(
            self.summary_container, text="", font=("Helvetica", 11, "bold"),
            bg="#fee2e2", fg="#7f1d1d", anchor="w", justify="left", wraplength=850, padx=10, pady=6,
        )

        self.notebook = ttk.Notebook(self.summary_container)
        self.notebook.pack(fill="both", expand=True, pady=(8, 0))

        self.tab_summary = tk.Frame(self.notebook, bg="white")
        self.tab_history = tk.Frame(self.notebook, bg="white")
        self.tab_meds = tk.Frame(self.notebook, bg="white")
        self.tab_docs = tk.Frame(self.notebook, bg="white")
        self.tab_flags = tk.Frame(self.notebook, bg="white")

        self.notebook.add(self.tab_summary, text="Chief Complaint & HPI")
        self.notebook.add(self.tab_history, text="Medical History")
        self.notebook.add(self.tab_meds, text="Medications & Allergies")
        self.notebook.add(self.tab_docs, text="Document Timeline")
        self.notebook.add(self.tab_flags, text="Red Flags")

        self._build_section_tab(self.tab_summary, "chief_complaint_hpi")
        self._build_section_tab(self.tab_history, "history")
        self._build_section_tab(self.tab_meds, "medications_allergies")
        self._build_docs_tab(self.tab_docs)
        self._build_flags_tab(self.tab_flags)

        bottom = tk.Frame(self.summary_container, bg="#f0f9ff")
        bottom.pack(fill="x", pady=(10, 0))
        ttk.Button(bottom, text="Preview Final Summary", command=self.preview_final_summary).pack(side="left")
        ttk.Button(bottom, text="\u2713 Finalize Consultation Summary", command=self.finalize_summary).pack(side="right")

    def _build_section_tab(self, parent, section_key):
        wrap = tk.Frame(parent, bg="white")
        wrap.pack(fill="both", expand=True, padx=12, pady=12)

        header = tk.Frame(wrap, bg="white")
        header.pack(fill="x")
        tk.Label(header, text=SECTION_LABELS[section_key], font=("Helvetica", 12, "bold"),
                  bg="white", fg="#0f172a").pack(side="left")
        status_label = tk.Label(header, text="", font=("Helvetica", 9, "bold"), bg="white")
        status_label.pack(side="right")

        text_widget = scrolledtext.ScrolledText(wrap, font=("Helvetica", 10), wrap="word", height=16, bd=1, relief="solid")
        text_widget.pack(fill="both", expand=True, pady=(8, 8))

        btns = tk.Frame(wrap, bg="white")
        btns.pack(fill="x")
        ttk.Button(btns, text="Save Edit", command=lambda s=section_key: self.save_edit(s)).pack(side="left", padx=(0, 6))
        ttk.Button(btns, text="\u2713 Confirm", command=lambda s=section_key: self.set_status(s, "confirmed")).pack(side="left", padx=6)
        ttk.Button(btns, text="\u2716 Reject", command=lambda s=section_key: self.set_status(s, "rejected")).pack(side="left", padx=6)

        self.section_widgets[section_key] = {"text": text_widget, "status_label": status_label}

    def _build_docs_tab(self, parent):
        wrap = tk.Frame(parent, bg="white")
        wrap.pack(fill="both", expand=True, padx=12, pady=12)
        tk.Label(wrap, text="Prior Medical Document Timeline", font=("Helvetica", 12, "bold"),
                  bg="white", fg="#0f172a", anchor="w").pack(fill="x")
        tk.Label(wrap, text="Digitized from patient-uploaded prescriptions, lab reports & discharge summaries.",
                  font=("Helvetica", 9), bg="white", fg="#64748b", anchor="w").pack(fill="x", pady=(0, 8))

        cols = ("Date", "Type", "Summary")
        self.docs_tree = ttk.Treeview(wrap, columns=cols, show="headings", height=16)
        for c, w in zip(cols, (100, 130, 560)):
            self.docs_tree.heading(c, text=c)
            self.docs_tree.column(c, width=w, anchor="w")
        self.docs_tree.pack(fill="both", expand=True)

    def _build_flags_tab(self, parent):
        wrap = tk.Frame(parent, bg="white")
        wrap.pack(fill="both", expand=True, padx=12, pady=12)
        tk.Label(wrap, text="AI-Detected Red-Flag / Triage Alerts", font=("Helvetica", 12, "bold"),
                  bg="white", fg="#0f172a", anchor="w").pack(fill="x", pady=(0, 8))
        self.flags_list_frame = tk.Frame(wrap, bg="white")
        self.flags_list_frame.pack(fill="both", expand=True)

    # ---------------- selection & data loading ----------------

    def on_select_patient(self, event):
        selection = self.queue_tree.selection()
        if not selection:
            return
        visit_id = int(selection[0])
        self.load_patient(visit_id)

    def load_patient(self, visit_id):
        self.current_visit_id = visit_id
        self.summary_placeholder.pack_forget()
        self.summary_container.pack(fill="both", expand=True)

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """SELECT p.id, p.name, p.age, p.sex, p.contact, p.abha_id, v.token_no, v.chief_complaint, v.priority
               FROM visits v JOIN patients p ON p.id = v.patient_id WHERE v.id=?""",
            (visit_id,),
        )
        patient_id, name, age, sex, contact, abha_id, token, complaint, priority = cur.fetchone()
        self.current_patient_name = name

        self.patient_banner.config(
            text=f"{token}  \u2022  {name}   ({age} / {sex})   \u2022  ABHA: {abha_id}   \u2022  Contact: {contact}"
        )

        cur.execute(
            """SELECT hpi, past_medical, past_surgical, drug_allergy, family_history, personal_history, ros
               FROM history WHERE visit_id=?""",
            (visit_id,),
        )
        h = cur.fetchone() or ("", "", "", "", "", "", "")
        hpi, past_medical, past_surgical, drug_allergy, family_history, personal_history, ros = h

        chief_hpi_text = f"Chief Complaint:\n{complaint}\n\nHistory of Present Illness (HPI):\n{hpi}"
        history_text = (
            f"Past Medical History:\n{past_medical}\n\n"
            f"Past Surgical History:\n{past_surgical}\n\n"
            f"Family History:\n{family_history}\n\n"
            f"Personal History:\n{personal_history}\n\n"
            f"Review of Systems:\n{ros}"
        )
        meds_text = drug_allergy

        self._set_section_text("chief_complaint_hpi", chief_hpi_text)
        self._set_section_text("history", history_text)
        self._set_section_text("medications_allergies", meds_text)

        for section in SECTIONS:
            self._refresh_status_label(section)

        # documents
        for row in self.docs_tree.get_children():
            self.docs_tree.delete(row)
        cur.execute(
            "SELECT doc_date, doc_type, summary FROM documents WHERE patient_id=? ORDER BY doc_date",
            (patient_id,),
        )
        docs = cur.fetchall()
        if docs:
            for doc_date, doc_type, summary in docs:
                self.docs_tree.insert("", tk.END, values=(doc_date, doc_type, summary))
        else:
            self.docs_tree.insert("", tk.END, values=("-", "-", "No prior documents digitized for this patient."))

        # red flags
        for w in self.flags_list_frame.winfo_children():
            w.destroy()
        cur.execute("SELECT flag_text, severity FROM red_flags WHERE visit_id=?", (visit_id,))
        flags = cur.fetchall()
        conn.close()

        if flags:
            self.red_flag_banner.config(
                text="\u26a0  " + "   |   ".join(f.strip() for f, _ in flags)
            )
            self.red_flag_banner.pack(fill="x", before=self.notebook, pady=(0, 8))
            for flag_text, severity in flags:
                color = "#b91c1c" if severity == "high" else "#b45309"
                row = tk.Frame(self.flags_list_frame, bg="white")
                row.pack(fill="x", pady=4)
                tk.Label(row, text=("\u26a0 HIGH" if severity == "high" else "\u26a0 MEDIUM"),
                          font=("Helvetica", 9, "bold"), bg=color, fg="white", padx=8, pady=2).pack(side="left")
                tk.Label(row, text="  " + flag_text, font=("Helvetica", 10), bg="white",
                          fg="#0f172a", wraplength=750, justify="left", anchor="w").pack(side="left", fill="x")
        else:
            self.red_flag_banner.pack_forget()
            tk.Label(self.flags_list_frame, text="No red-flag alerts for this patient.",
                      font=("Helvetica", 10), bg="white", fg="#64748b").pack(anchor="w")

    def _set_section_text(self, section, text):
        widget = self.section_widgets[section]["text"]
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)

    def _refresh_status_label(self, section):
        status = self._get_status(section)
        lbl = self.section_widgets[section]["status_label"]
        lbl.config(text=STATUS_LABELS.get(status, status), fg=STATUS_COLORS.get(status, "#0f172a"))

    def _get_status(self, section):
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT status FROM review_status WHERE visit_id=? AND section=?",
            (self.current_visit_id, section),
        )
        row = cur.fetchone()
        conn.close()
        return row[0] if row else "ai_generated"

    # ---------------- doctor actions ----------------

    def save_edit(self, section):
        if not self.current_visit_id:
            return
        self.set_status(section, "edited", show_message=False)
        messagebox.showinfo("Saved", f"Your edits to '{SECTION_LABELS[section]}' have been saved.")

    def set_status(self, section, status, show_message=True):
        if not self.current_visit_id:
            return
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO review_status (visit_id, section, status) VALUES (?, ?, ?)
               ON CONFLICT(visit_id, section) DO UPDATE SET status=excluded.status""",
            (self.current_visit_id, section, status),
        )
        conn.commit()
        conn.close()
        self._refresh_status_label(section)
        if show_message:
            verb = {"confirmed": "confirmed", "rejected": "rejected"}.get(status, status)
            messagebox.showinfo("Updated", f"'{SECTION_LABELS[section]}' marked as {verb}.")

    def _compile_summary_text(self):
        lines = [f"CONSULTATION-READY CLINICAL SUMMARY", f"Patient: {self.current_patient_name}",
                  f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", ""]
        for section in SECTIONS:
            status = self._get_status(section)
            text = self.section_widgets[section]["text"].get("1.0", tk.END).strip()
            lines.append(f"--- {SECTION_LABELS[section]}  [{STATUS_LABELS.get(status, status)}] ---")
            if status == "rejected":
                lines.append("(Section rejected by doctor - not included in final record. Requires re-elicitation.)")
            else:
                lines.append(text)
            lines.append("")
        return "\n".join(lines)

    def preview_final_summary(self):
        if not self.current_visit_id:
            return
        popup = tk.Toplevel(self.win)
        popup.title("Consultation Summary Preview")
        popup.geometry("650x600")
        text = scrolledtext.ScrolledText(popup, font=("Consolas", 10), wrap="word")
        text.pack(fill="both", expand=True, padx=10, pady=10)
        text.insert("1.0", self._compile_summary_text())
        text.config(state="disabled")

    def finalize_summary(self):
        if not self.current_visit_id:
            messagebox.showwarning("No Patient Selected", "Select a patient before finalizing.")
            return

        pending = [SECTION_LABELS[s] for s in SECTIONS if self._get_status(s) == "ai_generated"]
        if pending:
            proceed = messagebox.askyesno(
                "Unreviewed Sections",
                "The following sections have not been confirmed, edited, or rejected:\n\n"
                + "\n".join(f"\u2022 {p}" for p in pending)
                + "\n\nFinalize anyway?",
            )
            if not proceed:
                return

        summary_text = self._compile_summary_text()
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO final_summary (visit_id, summary_text, finalized_at) VALUES (?, ?, ?)
               ON CONFLICT(visit_id) DO UPDATE SET summary_text=excluded.summary_text, finalized_at=excluded.finalized_at""",
            (self.current_visit_id, summary_text, datetime.datetime.now().strftime("%Y-%m-%d %H:%M")),
        )
        cur.execute("UPDATE visits SET status='consulted' WHERE id=?", (self.current_visit_id,))
        conn.commit()
        conn.close()

        messagebox.showinfo("Consultation Finalized",
                              f"Summary for {self.current_patient_name} saved and marked consulted.")
        self.current_visit_id = None
        self.summary_container.pack_forget()
        self.summary_placeholder.pack(expand=True)
        self.refresh_queue()


# ----------------------------------------------------------------------
# ENTRY POINT
# ----------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    root = tk.Tk()
    LoginWindow(root)
    root.mainloop()
