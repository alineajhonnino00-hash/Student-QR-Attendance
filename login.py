import tkinter as tk
from tkinter import messagebox
import qrcode
import os
from PIL import Image, ImageTk
from database import Database


class Login:

    def __init__(self, parent=None, show_register_callback=None):
        self.db = Database()
        self.db.initialize()

        self.show_register_callback = show_register_callback

        if parent is None:
            self.window = tk.Tk()
            self.is_main_window = True
        else:
            self.window = parent
            self.is_main_window = False

        self.window.title("Student QR Attendance System")
        self.window.geometry("500x600")
        self.window.resizable(False, False)

        self.create_login_screen()

    # =========================
    # LOGIN SCREEN
    # =========================
    def create_login_screen(self):
        for widget in self.window.winfo_children():
            widget.destroy()

        title = tk.Label(
            self.window,
            text="Student QR Attendance System",
            font=("Arial", 20, "bold")
        )
        title.pack(pady=30)

        tk.Label(
            self.window,
            text="Student ID",
            font=("Arial", 12)
        ).pack(pady=(10, 5))

        self.student_id_entry = tk.Entry(
            self.window,
            font=("Arial", 12),
            width=30
        )
        self.student_id_entry.pack()

        tk.Label(
            self.window,
            text="Password",
            font=("Arial", 12)
        ).pack(pady=(15, 5))

        self.password_entry = tk.Entry(
            self.window,
            font=("Arial", 12),
            width=30,
            show="*"
        )
        self.password_entry.pack()

        login_button = tk.Button(
            self.window,
            text="LOGIN",
            font=("Arial", 12, "bold"),
            width=20,
            command=self.login
        )
        login_button.pack(pady=25)

        forgot_button = tk.Button(
            self.window,
            text="Forgot Password?",
            font=("Arial", 10),
            fg="blue",
            bd=0,
            cursor="hand2",
            command=self.forgot_password
        )
        forgot_button.pack()

        register_button = tk.Button(
            self.window,
            text="Back to Register",
            font=("Arial", 10),
            width=20,
            command=self.go_to_register
        )
        register_button.pack(pady=20)

    # =========================
    # LOGIN
    # =========================
    def login(self):
        student_id = self.student_id_entry.get().strip()
        password = self.password_entry.get().strip()

        if not student_id or not password:
            messagebox.showwarning(
                "Missing Information",
                "Please enter Student ID and Password."
            )
            return

        user = self.db.fetch_one(
            """
            SELECT *
            FROM users
            WHERE student_id = ?
            AND role = 'student'
            """,
            (student_id,)
        )

        if user is None:
            messagebox.showerror(
                "Login Failed",
                "Student ID not found."
            )
            return

        if user["password"] != password:
            messagebox.showerror(
                "Login Failed",
                "Incorrect password."
            )
            return

        self.open_qr_screen(user)

    # =========================
    # FORGOT PASSWORD
    # =========================
    def forgot_password(self):
        for widget in self.window.winfo_children():
            widget.destroy()

        title = tk.Label(
            self.window,
            text="Forgot Password",
            font=("Arial", 20, "bold")
        )
        title.pack(pady=35)

        instruction = tk.Label(
            self.window,
            text="Enter your Student ID",
            font=("Arial", 12)
        )
        instruction.pack(pady=10)

        self.forgot_student_id_entry = tk.Entry(
            self.window,
            font=("Arial", 12),
            width=30
        )
        self.forgot_student_id_entry.pack(pady=10)

        verify_button = tk.Button(
            self.window,
            text="VERIFY STUDENT ID",
            font=("Arial", 11, "bold"),
            width=22,
            command=self.verify_student_id
        )
        verify_button.pack(pady=20)

        back_button = tk.Button(
            self.window,
            text="Back to Login",
            font=("Arial", 10),
            width=22,
            command=self.create_login_screen
        )
        back_button.pack()

    # =========================
    # VERIFY STUDENT ID
    # =========================
    def verify_student_id(self):
        student_id = self.forgot_student_id_entry.get().strip()

        if not student_id:
            messagebox.showwarning(
                "Missing Student ID",
                "Please enter your Student ID."
            )
            return

        user = self.db.fetch_one(
            """
            SELECT *
            FROM users
            WHERE student_id = ?
            AND role = 'student'
            """,
            (student_id,)
        )

        if user is None:
            messagebox.showerror(
                "Student ID Not Found",
                "The Student ID does not exist."
            )
            return

        self.show_new_password_screen(user)

    # =========================
    # NEW PASSWORD SCREEN
    # =========================
    def show_new_password_screen(self, user):
        for widget in self.window.winfo_children():
            widget.destroy()

        title = tk.Label(
            self.window,
            text="Reset Password",
            font=("Arial", 20, "bold")
        )
        title.pack(pady=30)

        name = f"{user['first_name']} {user['last_name']}"

        tk.Label(
            self.window,
            text=f"Student: {name}",
            font=("Arial", 11)
        ).pack(pady=5)

        tk.Label(
            self.window,
            text=f"Student ID: {user['student_id']}",
            font=("Arial", 11)
        ).pack(pady=5)

        tk.Label(
            self.window,
            text="New Password",
            font=("Arial", 12)
        ).pack(pady=(25, 5))

        self.new_password_entry = tk.Entry(
            self.window,
            font=("Arial", 12),
            width=30,
            show="*"
        )
        self.new_password_entry.pack()

        tk.Label(
            self.window,
            text="Confirm New Password",
            font=("Arial", 12)
        ).pack(pady=(15, 5))

        self.confirm_password_entry = tk.Entry(
            self.window,
            font=("Arial", 12),
            width=30,
            show="*"
        )
        self.confirm_password_entry.pack()

        change_button = tk.Button(
            self.window,
            text="CHANGE PASSWORD",
            font=("Arial", 11, "bold"),
            width=22,
            command=lambda: self.change_password(user["id"])
        )
        change_button.pack(pady=25)

        back_button = tk.Button(
            self.window,
            text="Back",
            font=("Arial", 10),
            width=22,
            command=self.create_login_screen
        )
        back_button.pack()

    # =========================
    # CHANGE PASSWORD
    # =========================
    def change_password(self, user_id):
        new_password = self.new_password_entry.get().strip()
        confirm_password = self.confirm_password_entry.get().strip()

        if not new_password or not confirm_password:
            messagebox.showwarning(
                "Missing Information",
                "Please enter and confirm your new password."
            )
            return

        if len(new_password) < 4:
            messagebox.showwarning(
                "Invalid Password",
                "Password must be at least 4 characters."
            )
            return

        if new_password != confirm_password:
            messagebox.showerror(
                "Password Mismatch",
                "The passwords do not match."
            )
            return

        self.db.execute(
            """
            UPDATE users
            SET password = ?
            WHERE id = ?
            """,
            (new_password, user_id)
        )

        messagebox.showinfo(
            "Success",
            "Your password has been changed successfully."
        )

        self.create_login_screen()

    # =========================
    # CREATE QR IMAGE
    # =========================
    def create_qr_image(self, user):
        qr_folder = "qr_codes"

        if not os.path.exists(qr_folder):
            os.makedirs(qr_folder)

        student_id = user["student_id"]

        qr_path = os.path.join(
            qr_folder,
            f"{student_id}.png"
        )

        if not os.path.exists(qr_path):
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4
            )

            qr.add_data(user["qr_code"])
            qr.make(fit=True)

            qr_image = qr.make_image(
                fill_color="black",
                back_color="white"
            )

            qr_image.save(qr_path)

        return qr_path

    # =========================
    # QR SCREEN
    # =========================
    def open_qr_screen(self, user):
        for widget in self.window.winfo_children():
            widget.destroy()

        title = tk.Label(
            self.window,
            text="Login Successful!",
            font=("Arial", 20, "bold")
        )
        title.pack(pady=15)

        student_name = f"{user['first_name']} {user['last_name']}"

        tk.Label(
            self.window,
            text=f"Student ID: {user['student_id']}",
            font=("Arial", 12)
        ).pack(pady=5)

        tk.Label(
            self.window,
            text=f"Student Name: {student_name}",
            font=("Arial", 12)
        ).pack(pady=5)

        tk.Label(
            self.window,
            text="Your Personal QR Code",
            font=("Arial", 14, "bold")
        ).pack(pady=(15, 5))

        tk.Label(
            self.window,
            text="Show this QR code to the scanner.",
            font=("Arial", 10)
        ).pack(pady=5)

        qr_path = self.create_qr_image(user)

        try:
            qr_image = Image.open(qr_path)
            qr_image = qr_image.resize(
                (300, 300),
                Image.Resampling.LANCZOS
            )

            self.qr_photo = ImageTk.PhotoImage(qr_image)

            qr_label = tk.Label(
                self.window,
                image=self.qr_photo
            )
            qr_label.pack(pady=10)

        except Exception as e:
            messagebox.showerror(
                "QR Error",
                f"Unable to display QR code.\n\n{e}"
            )

        logout_button = tk.Button(
            self.window,
            text="LOGOUT",
            font=("Arial", 11, "bold"),
            width=20,
            command=self.logout
        )
        logout_button.pack(pady=15)

    # =========================
    # LOGOUT
    # =========================
    def logout(self):
        self.create_login_screen()

    # =========================
    # GO TO REGISTER
    # =========================
    def go_to_register(self):
        if self.show_register_callback:
            self.show_register_callback()
        else:
            try:
                from register import Register

                self.window.destroy()

                register_window = Register()
                register_window.run()

            except Exception as e:
                messagebox.showerror(
                    "Error",
                    f"Unable to open registration.\n\n{e}"
                )

    # =========================
    # RUN
    # =========================
    def run(self):
        self.window.mainloop()

        try:
            self.db.close()
        except Exception:
            pass


if __name__ == "__main__":
    app = Login()
    app.run()