import os
import uuid
import qrcode

from database import Database


# ============================================================
# ALL STUDENTS
# ============================================================

STUDENTS = [
    ("25-1-1-0583", "Kisha Andrea D. Lazo"),
    ("25-1-1-1035", "Owin A. Collado"),
    ("25-1-1-0726", "Allaizah Jamila Rio"),
    ("25-1-1-0675", "Jhon Nino A. Alinea"),
    ("25-1-1-0599", "Lara Franzene R. Rayman"),
    ("25-1-1-2885", "Jose Andrei A. Lazo"),
    ("25-1-1-0419", "Aika Danish Fernando"),
    ("25-1-1-1320", "Alshea Jean A. Montealegre"),
    ("25-1-1-2067", "Althea Carmen B. Domingo"),
    ("25-1-1-2345", "Angel Mae D. Leonillo"),
    ("25-1-1-1038", "Ayan Chloee E. Gallemit"),
    ("25-1-1-0661", "Brenz William A. Deguidoy"),
    ("25-1-1-0847", "Brian Clemente E. Manalili"),
    ("25-1-1-0428", "Cee Jay F Cunanan"),
    ("25-1-1-0400", "Charmaine Faith Pasmo"),
    ("25-1-1-0969", "Christian Jay M. Pablo"),
    ("25-1-1-0575", "Daniel S. Rubion"),
    ("25-1-1-0679", "Erl Cedrick Padlan"),
    ("25-1-1-2575", "Fatihara H. Abil"),
    ("25-1-1-0309", "Hannah Kathleen Elayba"),
    ("25-1-1-0324", "Jefferson D Elan"),
    ("25-1-1-1737", "John Patrick E. De leon"),
    ("25-1-1-2636", "Kherwin U Takaki"),
    ("25-1-1-0573", "Kris L. Vergara"),
    ("25-1-1-1255", "KRISTAN COLE NACUSPAG"),
    ("25-1-1-1074", "LOURIENE OLIPANE"),
    ("25-1-1-1362", "Lucky G Padrique Jr."),
    ("25-1-1-0804", "Nicole E. Ecaruan"),
    ("25-1-1-0671", "Ronnie M. Tolentino II"),
    ("25-1-1-1540", "Ryuki A. Acupido"),
    ("25-1-1-1132", "Samantha Jhoy S. Nemir"),
    ("25-1-1-0956", "Sandy U. Dullas"),
    ("25-1-1-0648", "Syrus M. Ambid"),
]


# ============================================================
# QR CODE FOLDER
# ============================================================

QR_FOLDER = "qr_codes"

os.makedirs(QR_FOLDER, exist_ok=True)


# ============================================================
# SPLIT NAME
# ============================================================

def split_name(full_name):
    parts = full_name.strip().split()

    if len(parts) == 0:
        return "", ""

    if len(parts) == 1:
        return parts[0], ""

    first_name = " ".join(parts[:-1])
    last_name = parts[-1]

    return first_name, last_name


# ============================================================
# CREATE QR CODE
# ============================================================

def create_qr(student_id, qr_code):
    filename = f"{student_id}.png"

    filepath = os.path.join(
        QR_FOLDER,
        filename
    )

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4
    )

    qr.add_data(qr_code)
    qr.make(fit=True)

    image = qr.make_image()

    image.save(filepath)

    return filepath


# ============================================================
# ADD ALL STUDENTS
# ============================================================

def add_students():

    db = Database()
    db.initialize()

    added = 0
    existing = 0
    errors = 0

    print()
    print("==============================================")
    print("          STUDENT REGISTRATION")
    print("==============================================")
    print()
    print(
        f"Total students: {len(STUDENTS)}"
    )
    print()


    for number, (student_id, full_name) in enumerate(
        STUDENTS,
        start=1
    ):

        print(
            f"[{number}/{len(STUDENTS)}] "
            f"{student_id} - {full_name}"
        )

        try:

            # ------------------------------------------------
            # CHECK IF STUDENT ALREADY EXISTS
            # ------------------------------------------------

            student = db.fetch_one(
                """
                SELECT
                    id,
                    student_id,
                    first_name,
                    last_name,
                    email,
                    password,
                    role,
                    qr_code

                FROM users

                WHERE student_id = ?
                """,
                (student_id,)
            )


            # ------------------------------------------------
            # IF ALREADY EXISTS
            # ------------------------------------------------

            if student:

                print(
                    "    Student already exists."
                )


                # Use the existing QR code
                existing_qr = student["qr_code"]


                if existing_qr:

                    qr_path = os.path.join(
                        QR_FOLDER,
                        f"{student_id}.png"
                    )


                    # Create QR image only if missing
                    if not os.path.exists(qr_path):

                        create_qr(
                            student_id,
                            existing_qr
                        )

                        print(
                            "    QR image created."
                        )

                    else:

                        print(
                            "    QR image already exists."
                        )


                existing += 1

                print()

                continue


            # ------------------------------------------------
            # SPLIT NAME
            # ------------------------------------------------

            first_name, last_name = split_name(
                full_name
            )


            # ------------------------------------------------
            # CREATE UNIQUE QR CODE
            # ------------------------------------------------

            qr_code = (
                "STUDENT:"
                + student_id
                + ":"
                + uuid.uuid4().hex
            )


            # ------------------------------------------------
            # INSERT INTO DATABASE
            # ------------------------------------------------

            db.execute(
                """
                INSERT INTO users
                (
                    student_id,
                    first_name,
                    last_name,
                    email,
                    password,
                    role,
                    qr_code
                )

                VALUES
                (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                )
                """,
                (
                    student_id,
                    first_name,
                    last_name,
                    None,
                    None,
                    "student",
                    qr_code
                )
            )


            # ------------------------------------------------
            # CREATE QR IMAGE
            # ------------------------------------------------

            qr_path = create_qr(
                student_id,
                qr_code
            )


            added += 1


            print(
                "    Added successfully."
            )

            print(
                f"    QR: {qr_path}"
            )

            print()


        except Exception as error:

            errors += 1

            print(
                "    ERROR:"
            )

            print(
                f"    {error}"
            )

            print()


    # ========================================================
    # CLOSE DATABASE
    # ========================================================

    db.close()


    # ========================================================
    # SUMMARY
    # ========================================================

    print()
    print("==============================================")
    print("              FINISHED")
    print("==============================================")
    print()
    print(
        f"Total students : {len(STUDENTS)}"
    )
    print(
        f"Added          : {added}"
    )
    print(
        f"Already exists : {existing}"
    )
    print(
        f"Errors         : {errors}"
    )
    print()
    print(
        "QR folder:"
    )
    print(
        os.path.abspath(QR_FOLDER)
    )
    print()
    print("==============================================")


# ============================================================
# START PROGRAM
# ============================================================

if __name__ == "__main__":
    add_students()