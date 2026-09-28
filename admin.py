import tkinter as tk
from tkinter import ttk
from datetime import date, timedelta
from database import Database


class Admin:
    def __init__(self):
        self.db = Database()
        self.db.initialize()

        self.root = tk.Tk()
        self.root.title("Admin Dashboard - Student QR Attendance System")
        self.root.geometry("1100x700")
        self.root.resizable(False, False)

        self.create_default_subjects()
        self.create_default_schedules()
        self.create_ui()

    # ==========================================================
    # DEFAULT SUBJECTS
    # ==========================================================
    def create_default_subjects(self):
        subjects = [
            ("PE 301C", "PHYSICAL ACTIVITIES TOWARD HEALTH AND FITNESS 3 (PATHFIT3): DANCE"),
            ("MS 101", "DISCRETE MATHEMATICS"),
            ("GEC 3AA", "THE CONTEMPORARY WORLD (WITH PEACE EDUCATION)"),
            ("GEE 1", "ENVIRONMENTAL SCIENCE"),
            ("IT ELECTIVE 1", "IT ELECTIVE I"),
            ("GEM", "THE LIFE AND WORKS OF RIZAL"),
            ("CC 103", "COMPUTER PROGRAMMING II"),
        ]

        for code, name in subjects:
            existing = self.db.fetch_one(
                "SELECT id FROM subjects WHERE subject_code = ?", (code,)
            )
            if not existing:
                self.db.execute(
                    """
                    INSERT INTO subjects (subject_code, subject_name, description)
                    VALUES (?, ?, ?)
                    """,
                    (code, name, "")
                )

    # ==========================================================
    # DEFAULT SCHEDULES
    # ==========================================================
    def create_default_schedules(self):
        schedule_templates = [
            ("PE 301C", ["T", "TH"], "12:30 PM", "1:30 PM", "TBA"),
            ("MS 101", ["T", "TH"], "9:00 AM", "10:30 AM", "TBA"),
            ("GEC 3AA", ["M", "W"], "2:00 PM", "3:30 PM", "TBA"),
            ("GEE 1", ["M", "W"], "12:30 PM", "2:00 PM", "TBA"),
            ("IT ELECTIVE 1", ["M", "W"], "7:30 AM", "9:00 AM", "TBA"),
            ("IT ELECTIVE 1", ["T", "TH"], "3:30 PM", "4:30 PM", "TBA"),
            ("GEM", ["T", "TH"], "10:00 AM", "11:30 AM", "TBA"),
            ("CC 103", ["T", "TH"], "8:00 AM", "9:00 AM", "TBA"),
            ("CC 103", ["T", "TH"], "10:30 AM", "12:00 PM", "TBA"),
        ]

        day_numbers = {"M": 0, "T": 1, "W": 2, "TH": 3}
        today = date.today()
        monday = today - timedelta(days=today.weekday())

        for week in range(9):
            week_start = monday + timedelta(weeks=week)

            for subject_code, days, start_time, end_time, room in schedule_templates:
                subject = self.db.fetch_one(
                    "SELECT id FROM subjects WHERE subject_code = ?",
                    (subject_code,)
                )
                if not subject:
                    continue

                subject_id = subject["id"]

                for day_code in days:
                    schedule_date = (
                        week_start + timedelta(days=day_numbers[day_code])
                    ).strftime("%Y-%m-%d")

                    existing = self.db.fetch_one(
                        """
                        SELECT id FROM schedules
                        WHERE subject_id = ?
                        AND schedule_date = ?
                        AND start_time = ?
                        AND end_time = ?
                        """,
                        (subject_id, schedule_date, start_time, end_time)
                    )

                    if not existing:
                        self.db.execute(
                            """
                            INSERT INTO schedules
                            (subject_id, schedule_date, start_time, end_time, room)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (
                                subject_id,
                                schedule_date,
                                start_time,
                                end_time,
                                room
                            )
                        )

    # ==========================================================
    # MAIN UI
    # ==========================================================
    def create_ui(self):
        title = tk.Label(
            self.root,
            text="ADMIN DASHBOARD",
            font=("Arial", 22, "bold")
        )
        title.pack(pady=15)

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=15, pady=10)

        self.subject_frame = ttk.Frame(notebook)
        self.schedule_frame = ttk.Frame(notebook)
        self.student_frame = ttk.Frame(notebook)
        self.attendance_frame = ttk.Frame(notebook)

        notebook.add(self.subject_frame, text="Subjects")
        notebook.add(self.schedule_frame, text="Schedules")
        notebook.add(self.student_frame, text="Students")
        notebook.add(self.attendance_frame, text="Attendance")

        self.create_subject_tab()
        self.create_schedule_tab()
        self.create_student_tab()
        self.create_attendance_tab()

    # ==========================================================
    # SUBJECT TAB
    # ==========================================================
    def create_subject_tab(self):
        title = tk.Label(
            self.subject_frame,
            text="Subject List",
            font=("Arial", 16, "bold")
        )
        title.pack(pady=10)

        columns = ("id", "code", "name")

        self.subject_tree = ttk.Treeview(
            self.subject_frame,
            columns=columns,
            show="headings",
            height=22
        )

        self.subject_tree.heading("id", text="ID")
        self.subject_tree.heading("code", text="Subject Code")
        self.subject_tree.heading("name", text="Subject Name")

        self.subject_tree.column("id", width=60)
        self.subject_tree.column("code", width=150)
        self.subject_tree.column("name", width=700)

        self.subject_tree.pack(
            fill="both", expand=True, padx=15, pady=10
        )

        button = tk.Button(
            self.subject_frame,
            text="Refresh Subjects",
            width=20,
            command=self.load_subjects
        )
        button.pack(pady=10)

        self.load_subjects()

    def load_subjects(self):
        for item in self.subject_tree.get_children():
            self.subject_tree.delete(item)

        subjects = self.db.fetch_all(
            """
            SELECT id, subject_code, subject_name
            FROM subjects
            ORDER BY subject_code
            """
        )

        for subject in subjects:
            self.subject_tree.insert(
                "",
                "end",
                values=(
                    subject["id"],
                    subject["subject_code"],
                    subject["subject_name"]
                )
            )

    # ==========================================================
    # SCHEDULE TAB
    # ==========================================================
    def create_schedule_tab(self):
        title = tk.Label(
            self.schedule_frame,
            text="Schedule List",
            font=("Arial", 16, "bold")
        )
        title.pack(pady=10)

        columns = ("id", "subject", "date", "start", "end", "room")

        self.schedule_tree = ttk.Treeview(
            self.schedule_frame,
            columns=columns,
            show="headings",
            height=22
        )

        self.schedule_tree.heading("id", text="ID")
        self.schedule_tree.heading("subject", text="Subject")
        self.schedule_tree.heading("date", text="Date")
        self.schedule_tree.heading("start", text="Start")
        self.schedule_tree.heading("end", text="End")
        self.schedule_tree.heading("room", text="Room")

        self.schedule_tree.column("id", width=50)
        self.schedule_tree.column("subject", width=160)
        self.schedule_tree.column("date", width=110)
        self.schedule_tree.column("start", width=100)
        self.schedule_tree.column("end", width=100)
        self.schedule_tree.column("room", width=100)

        self.schedule_tree.pack(
            fill="both", expand=True, padx=15, pady=10
        )

        button_frame = tk.Frame(self.schedule_frame)
        button_frame.pack(pady=10)

        tk.Button(
            button_frame,
            text="Refresh Schedules",
            width=20,
            command=self.load_schedules
        ).pack(side="left", padx=5)

        tk.Button(
            button_frame,
            text="Today's Schedule",
            width=20,
            command=self.load_today_schedules
        ).pack(side="left", padx=5)

        self.load_schedules()

    def load_schedules(self):
        for item in self.schedule_tree.get_children():
            self.schedule_tree.delete(item)

        schedules = self.db.fetch_all(
            """
            SELECT
                schedules.id,
                subjects.subject_code,
                schedules.schedule_date,
                schedules.start_time,
                schedules.end_time,
                schedules.room
            FROM schedules
            JOIN subjects ON schedules.subject_id = subjects.id
            ORDER BY schedules.schedule_date, schedules.start_time
            """
        )

        for schedule in schedules:
            self.schedule_tree.insert(
                "",
                "end",
                values=(
                    schedule["id"],
                    schedule["subject_code"],
                    schedule["schedule_date"],
                    schedule["start_time"],
                    schedule["end_time"],
                    schedule["room"]
                )
            )

    def load_today_schedules(self):
        for item in self.schedule_tree.get_children():
            self.schedule_tree.delete(item)

        today = date.today().strftime("%Y-%m-%d")

        schedules = self.db.fetch_all(
            """
            SELECT
                schedules.id,
                subjects.subject_code,
                schedules.schedule_date,
                schedules.start_time,
                schedules.end_time,
                schedules.room
            FROM schedules
            JOIN subjects ON schedules.subject_id = subjects.id
            WHERE schedules.schedule_date = ?
            ORDER BY schedules.start_time
            """,
            (today,)
        )

        for schedule in schedules:
            self.schedule_tree.insert(
                "",
                "end",
                values=(
                    schedule["id"],
                    schedule["subject_code"],
                    schedule["schedule_date"],
                    schedule["start_time"],
                    schedule["end_time"],
                    schedule["room"]
                )
            )

    # ==========================================================
    # STUDENT TAB
    # ==========================================================
    def create_student_tab(self):
        title = tk.Label(
            self.student_frame,
            text="Registered Students",
            font=("Arial", 16, "bold")
        )
        title.pack(pady=10)

        columns = ("id", "student_id", "name", "email", "qr")

        self.student_tree = ttk.Treeview(
            self.student_frame,
            columns=columns,
            show="headings",
            height=22
        )

        self.student_tree.heading("id", text="ID")
        self.student_tree.heading("student_id", text="Student ID")
        self.student_tree.heading("name", text="Name")
        self.student_tree.heading("email", text="Email")
        self.student_tree.heading("qr", text="QR Code")

        self.student_tree.column("id", width=50)
        self.student_tree.column("student_id", width=130)
        self.student_tree.column("name", width=250)
        self.student_tree.column("email", width=250)
        self.student_tree.column("qr", width=180)

        self.student_tree.pack(
            fill="both", expand=True, padx=15, pady=10
        )

        tk.Button(
            self.student_frame,
            text="Refresh Students",
            width=20,
            command=self.load_students
        ).pack(pady=10)

        self.load_students()

    def load_students(self):
        for item in self.student_tree.get_children():
            self.student_tree.delete(item)

        students = self.db.fetch_all(
            """
            SELECT
                id, student_id, first_name, last_name, email, qr_code
            FROM users
            WHERE role = 'student'
            ORDER BY last_name, first_name
            """
        )

        for student in students:
            full_name = (
                student["first_name"] + " " + student["last_name"]
            )

            self.student_tree.insert(
                "",
                "end",
                values=(
                    student["id"],
                    student["student_id"],
                    full_name,
                    student["email"],
                    student["qr_code"]
                )
            )

    # ==========================================================
    # ATTENDANCE TAB - FOLDER STYLE
    # ==========================================================
    def create_attendance_tab(self):
        title = tk.Label(
            self.attendance_frame,
            text="Attendance Records",
            font=("Arial", 16, "bold")
        )
        title.pack(pady=(10, 3))

        info = tk.Label(
            self.attendance_frame,
            text="Attendance is grouped by Subject, then by Date.",
            font=("Arial", 10)
        )
        info.pack(pady=(0, 8))

        tree_frame = tk.Frame(self.attendance_frame)
        tree_frame.pack(fill="both", expand=True, padx=15, pady=5)

        columns = (
            "student",
            "subject",
            "date",
            "time",
            "status"
        )

        self.attendance_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="tree headings",
            height=22
        )

        # Tree/folder column
        self.attendance_tree.heading(
            "#0",
            text="Attendance Folder"
        )
        self.attendance_tree.column(
            "#0",
            width=330,
            minwidth=250,
            stretch=False
        )

        self.attendance_tree.heading("student", text="Student")
        self.attendance_tree.heading("subject", text="Subject")
        self.attendance_tree.heading("date", text="Date")
        self.attendance_tree.heading("time", text="Time In")
        self.attendance_tree.heading("status", text="Status")

        self.attendance_tree.column("student", width=230)
        self.attendance_tree.column("subject", width=140)
        self.attendance_tree.column("date", width=110)
        self.attendance_tree.column("time", width=100)
        self.attendance_tree.column("status", width=100)

        y_scroll = ttk.Scrollbar(
            tree_frame,
            orient="vertical",
            command=self.attendance_tree.yview
        )
        self.attendance_tree.configure(yscrollcommand=y_scroll.set)

        self.attendance_tree.pack(
            side="left",
            fill="both",
            expand=True
        )
        y_scroll.pack(
            side="right",
            fill="y"
        )

        button_frame = tk.Frame(self.attendance_frame)
        button_frame.pack(pady=10)

        tk.Button(
            button_frame,
            text="Refresh Attendance",
            width=20,
            command=self.load_attendance
        ).pack(side="left", padx=5)

        tk.Button(
            button_frame,
            text="Today's Attendance",
            width=20,
            command=self.load_today_attendance
        ).pack(side="left", padx=5)

        self.load_attendance()

    # ==========================================================
    # LOAD ALL ATTENDANCE - SUBJECT > DATE > STUDENT
    # ==========================================================
    def load_attendance(self):
        self._load_attendance_grouped(today_only=False)

    # ==========================================================
    # LOAD TODAY'S ATTENDANCE - SUBJECT > DATE > STUDENT
    # ==========================================================
    def load_today_attendance(self):
        self._load_attendance_grouped(today_only=True)

    # ==========================================================
    # GROUPED ATTENDANCE
    # ==========================================================
    def _load_attendance_grouped(self, today_only=False):
        for item in self.attendance_tree.get_children():
            self.attendance_tree.delete(item)

        if today_only:
            today = date.today().strftime("%Y-%m-%d")

            records = self.db.fetch_all(
                """
                SELECT
                    attendance.id,
                    users.student_id,
                    users.first_name,
                    users.last_name,
                    subjects.subject_code,
                    subjects.subject_name,
                    attendance.attendance_date,
                    attendance.time_in,
                    attendance.status
                FROM attendance
                JOIN users
                    ON attendance.user_id = users.id
                JOIN schedules
                    ON attendance.schedule_id = schedules.id
                JOIN subjects
                    ON schedules.subject_id = subjects.id
                WHERE attendance.attendance_date = ?
                ORDER BY
                    subjects.subject_code,
                    attendance.attendance_date,
                    attendance.time_in
                """,
                (today,)
            )
        else:
            records = self.db.fetch_all(
                """
                SELECT
                    attendance.id,
                    users.student_id,
                    users.first_name,
                    users.last_name,
                    subjects.subject_code,
                    subjects.subject_name,
                    attendance.attendance_date,
                    attendance.time_in,
                    attendance.status
                FROM attendance
                JOIN users
                    ON attendance.user_id = users.id
                JOIN schedules
                    ON attendance.schedule_id = schedules.id
                JOIN subjects
                    ON schedules.subject_id = subjects.id
                ORDER BY
                    subjects.subject_code,
                    attendance.attendance_date,
                    attendance.time_in
                """
            )

        subject_nodes = {}
        date_nodes = {}

        for record in records:
            subject_code = record["subject_code"]
            subject_name = record["subject_name"] or ""
            attendance_date = record["attendance_date"]

            # --------------------------------------------------
            # SUBJECT FOLDER
            # --------------------------------------------------
            if subject_code not in subject_nodes:
                subject_nodes[subject_code] = self.attendance_tree.insert(
                    "",
                    "end",
                    text=f"📁 {subject_code} - {subject_name}",
                    values=("", "", "", "", ""),
                    open=False,
                    tags=("subject_folder",)
                )

            subject_node = subject_nodes[subject_code]

            # --------------------------------------------------
            # DATE FOLDER INSIDE SUBJECT
            # --------------------------------------------------
            date_key = (subject_code, attendance_date)

            if date_key not in date_nodes:
                date_nodes[date_key] = self.attendance_tree.insert(
                    subject_node,
                    "end",
                    text=f"📅 {self.format_date(attendance_date)}",
                    values=("", "", attendance_date, "", ""),
                    open=False,
                    tags=("date_folder",)
                )

            date_node = date_nodes[date_key]

            # --------------------------------------------------
            # STUDENT RECORD
            # --------------------------------------------------
            student_name = (
                record["student_id"]
                + " - "
                + record["first_name"]
                + " "
                + record["last_name"]
            )

            status = record["status"] or ""

            self.attendance_tree.insert(
                date_node,
                "end",
                text="👤 Student",
                values=(
                    student_name,
                    subject_code,
                    attendance_date,
                    record["time_in"] or "",
                    status
                ),
                tags=(self.status_tag(status),)
            )

        # If there are no records
        if not records:
            self.attendance_tree.insert(
                "",
                "end",
                text="No attendance records found.",
                values=("", "", "", "", ""),
                tags=("empty",)
            )

        self.attendance_tree.tag_configure(
            "subject_folder",
            font=("Arial", 10, "bold")
        )
        self.attendance_tree.tag_configure(
            "date_folder",
            font=("Arial", 10, "bold")
        )
        self.attendance_tree.tag_configure(
            "present",
            font=("Arial", 10)
        )
        self.attendance_tree.tag_configure(
            "late",
            font=("Arial", 10, "bold")
        )
        self.attendance_tree.tag_configure(
            "absent",
            font=("Arial", 10, "bold")
        )

    def status_tag(self, status):
        status = str(status).strip().lower()

        if status == "present":
            return "present"
        if status == "late":
            return "late"
        if status == "absent":
            return "absent"

        return "normal"

    def format_date(self, date_string):
        try:
            year, month, day = map(int, date_string.split("-"))
            return date(year, month, day).strftime("%B %d, %Y")
        except Exception:
            return date_string

    # ==========================================================
    # RUN
    # ==========================================================
    def run(self):
        self.root.mainloop()


# ==============================================================
# MAIN
# ==============================================================
if __name__ == "__main__":
    app = Admin()
    app.run()
