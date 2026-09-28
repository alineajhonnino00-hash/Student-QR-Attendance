import tkinter as tk
from tkinter import messagebox
import sqlite3

from database import Database


# ============================================================
# STUDENT LIST
# Student ID -> Complete Student Name
# ============================================================

STUDENTS = {
    "25-1-1-0583": "Kisha Andrea D. Lazo",
    "25-1-1-1035": "Owin A. Collado",
    "25-1-1-0726": "Allaizah Jamila Rio",
    "25-1-1-0675": "Jhon Nino A. Alinea",
    "25-1-1-0599": "Lara Franzene R. Rayman",
    "25-1-1-2885": "Jose Andrei A. Lazo",

    "25-1-1-0419": "Aika Danish Fernando",
    "25-1-1-1320": "Alshea Jean A. Montealegre",
    "25-1-1-2067": "Althea Carmen B. Domingo",
    "25-1-1-2345": "Angel Mae D. Leonillo",
    "25-1-1-1038": "Ayan Chloee E. Gallemit",
    "25-1-1-0661": "Brenz William A. Deguidoy",
    "25-1-1-0847": "Brian Clemente E. Manalili",
    "25-1-1-0428": "Cee Jay F Cunanan",
    "25-1-1-0400": "Charmaine Faith Pasmo",
    "25-1-1-0969": "Christian Jay M. Pablo",
    "25-1-1-0575": "Daniel S. Rubion",
    "25-1-1-0679": "Erl Cedrick Padlan",
    "25-1-1-2575": "Fatihara H. Abil",
    "25-1-1-0309": "Hannah Kathleen Elayba",
    "25-1-1-0324": "Jefferson D Elan",
    "25-1-1-1737": "John Patrick E. De leon",
    "25-1-1-2636": "Kherwin U Takaki",
    "25-1-1-0573": "Kris L. Vergara",
    "25-1-1-1255": "KRISTAN COLE NACUSPAG",
    "25-1-1-1074": "LOURIENE OLIPANE",
    "25-1-1-1362": "Lucky G Padrique Jr.",
    "25-1-1-0804": "Nicole E. Ecaruan",
    "25-1-1-0671": "Ronnie M. Tolentino II",
    "25-1-1-1540": "Ryuki A. Acupido",
    "25-1-1-1132": "Samantha Jhoy S. Nemir",
    "25-1-1-0956": "Sandy U. Dullas",
    "25-1-1-0648": "Syrus M. Ambid",
}


class Register:

    def __init__(self, parent=None, show_login_callback=None):

        self.parent = parent
        self.show_login_callback = show_login_callback

        self.db = Database()
        self.db.initialize()

        # Use existing window if available
        if parent is not None:
            self.window = parent
        else:
            self.window = tk.Tk()

        self.window.title("Student Registration")
        self.window.geometry("400x450")
        self.window.resizable(False, False)

        # Automatically fix names of students already registered
        self.sync_student_names()

        self.create_register_screen()

    # ============================================================
    # CLEAR WINDOW
    # ============================================================

    def clear_window(self):

        for widget in self.window.winfo_children():
            widget.destroy()

    # ============================================================
    # REGISTER SCREEN
    # ============================================================

    def create_register_screen(self):

        self.clear_window()

        tk.Label(
            self.window,
            text="Student Registration",
            font=("Arial", 20, "bold")
        ).pack(pady=25)

        # --------------------------------------------------------
        # Student ID
        # --------------------------------------------------------

        tk.Label(
            self.window,
            text="Student ID",
            font=("Arial", 11)
        ).pack()

        self.student_id_entry = tk.Entry(
            self.window,
            width=30,
            font=("Arial", 11)
        )
        self.student_id_entry.pack(pady=5)

        # --------------------------------------------------------
        # Password
        # --------------------------------------------------------

        tk.Label(
            self.window,
            text="Password",
            font=("Arial", 11)
        ).pack(pady=(10, 0))

        self.password_entry = tk.Entry(
            self.window,
            width=30,
            font=("Arial", 11),
            show="*"
        )
        self.password_entry.pack(pady=5)

        # --------------------------------------------------------
        # Confirm Password
        # --------------------------------------------------------

        tk.Label(
            self.window,
            text="Confirm Password",
            font=("Arial", 11)
        ).pack(pady=(10, 0))

        self.confirm_password_entry = tk.Entry(
            self.window,
            width=30,
            font=("Arial", 11),
            show="*"
        )
        self.confirm_password_entry.pack(pady=5)

        # --------------------------------------------------------
        # Register Button
        # --------------------------------------------------------

        tk.Button(
            self.window,
            text="Register",
            width=20,
            font=("Arial", 11),
            command=self.register
        ).pack(pady=20)

        # --------------------------------------------------------
        # Login Button
        # --------------------------------------------------------

        tk.Button(
            self.window,
            text="Go to Login",
            width=20,
            font=("Arial", 11),
            command=self.go_to_login
        ).pack()

        # Enter key
        self.window.bind(
            "<Return>",
            lambda event: self.register()
        )

    # ============================================================
    # SPLIT NAME
    # ============================================================

    def split_name(self, full_name):

        parts = full_name.strip().split()

        if len(parts) == 1:
            return parts[0], ""

        first_name = " ".join(parts[:-1])
        last_name = parts[-1]

        return first_name, last_name

    # ============================================================
    # SYNC EXISTING STUDENT NAMES
    # ============================================================

    def sync_student_names(self):

        """
        Automatically fixes students that were previously
        registered as:

        Student 25-1-1-0419
        Student 25-1-1-1320
        etc.

        Their correct names will be taken from STUDENTS.
        """

        for student_id, full_name in STUDENTS.items():

            user = self.db.fetch_one(
                """
                SELECT *
                FROM users
                WHERE student_id = ?
                """,
                (student_id,)
            )

            if user:

                first_name, last_name = self.split_name(full_name)

                try:

                    self.db.execute(
                        """
                        UPDATE users
                        SET
                            first_name = ?,
                            last_name = ?
                        WHERE student_id = ?
                        """,
                        (
                            first_name,
                            last_name,
                            student_id
                        )
                    )

                except Exception:
                    pass

    # ============================================================
    # REGISTER
    # ============================================================

    def register(self):

        student_id = self.student_id_entry.get().strip()
        password = self.password_entry.get()
        confirm_password = self.confirm_password_entry.get()

        # --------------------------------------------------------
        # Check empty fields
        # --------------------------------------------------------

        if not student_id or not password or not confirm_password:

            messagebox.showwarning(
                "Missing Information",
                "Please fill in all fields."
            )

            return

        # --------------------------------------------------------
        # Check password
        # --------------------------------------------------------

        if password != confirm_password:

            messagebox.showerror(
                "Password Error",
                "Passwords do not match."
            )

            return

        # --------------------------------------------------------
        # Check if Student ID is in our student list
        # --------------------------------------------------------

        if student_id not in STUDENTS:

            messagebox.showerror(
                "Invalid Student ID",
                "Student ID is not in the registered student list."
            )

            return

        # --------------------------------------------------------
        # Get correct student name
        # --------------------------------------------------------

        full_name = STUDENTS[student_id]

        first_name, last_name = self.split_name(full_name)

        # --------------------------------------------------------
        # Check existing student
        # --------------------------------------------------------

        existing_student = self.db.fetch_one(
            """
            SELECT *
            FROM users
            WHERE student_id = ?
            """,
            (student_id,)
        )

        if existing_student:

            messagebox.showerror(
                "Registration Failed",
                "Student ID is already registered."
            )

            return

        # ========================================================
        # CREATE STUDENT
        # ========================================================

        try:

            self.db.create_student(
                student_id=student_id,
                first_name=first_name,
                last_name=last_name,
                email=f"{student_id}@student.local",
                password=password
            )

            # ----------------------------------------------------
            # Success
            # ----------------------------------------------------

            messagebox.showinfo(
                "Registration Successful",
                f"Registration successful!\n\n"
                f"Student ID: {student_id}\n"
                f"Name: {full_name}\n\n"
                f"You can now login."
            )

            # Clear fields
            self.clear_fields()

            # Automatically go to Login
            self.go_to_login()

        except sqlite3.IntegrityError:

            messagebox.showerror(
                "Registration Failed",
                "Unable to register this Student ID."
            )

        except Exception as error:

            messagebox.showerror(
                "Registration Error",
                f"An error occurred:\n\n{error}"
            )

    # ============================================================
    # CLEAR FIELDS
    # ============================================================

    def clear_fields(self):

        self.student_id_entry.delete(
            0,
            tk.END
        )

        self.password_entry.delete(
            0,
            tk.END
        )

        self.confirm_password_entry.delete(
            0,
            tk.END
        )

    # ============================================================
    # GO TO LOGIN
    # ============================================================

    def go_to_login(self):

        self.clear_window()

        from login import Login

        Login(
            parent=self.window,
            show_register_callback=self.create_register_screen
        )

    # ============================================================
    # RUN
    # ============================================================

    def run(self):

        self.window.mainloop()


# ================================================================
# START PROGRAM
# ================================================================

if __name__ == "__main__":

    app = Register()
    app.run()