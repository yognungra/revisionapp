import sqlite3
import hashlib
from argon2 import PasswordHasher

ph = PasswordHasher()

connection = sqlite3.connect("Users.db")
c = connection.cursor()
c.execute("PRAGMA foreign_keys = ON;")
print(c)

# Create tables
c.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        UserID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        FirstName TEXT NOT NULL,
        LastName TEXT NOT NULL,
        Email TEXT NOT NULL,
        PasswordHash TEXT NOT NULL,
        UserRole TEXT NOT NULL,
        SchoolID INTEGER NOT NULL,
        DateCreated DATE DEFAULT current_date NOT NULL
    );
""")

c.execute("""
    CREATE TABLE IF NOT EXISTS Students (
        StudentID INTEGER PRIMARY KEY NOT NULL,
        YearGroup INTEGER NOT NULL,
        UserID INTEGER NOT NULL,
        FOREIGN KEY(UserID) REFERENCES Users(UserID) ON DELETE CASCADE ON UPDATE CASCADE
    );
""")

c.execute("""
    CREATE TABLE IF NOT EXISTS Teachers (
        TeacherID INTEGER PRIMARY KEY NOT NULL,
        UserID INTEGER NOT NULL,
        FOREIGN KEY(UserID) REFERENCES Users(UserID) ON DELETE CASCADE ON UPDATE CASCADE
    );
""")

c.execute("""
    CREATE TABLE IF NOT EXISTS Classes (
        ClassID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        LocalClassIdentifier TEXT NOT NULL,
        SchoolID INTEGER NOT NULL,
        FOREIGN KEY(SchoolID) REFERENCES Schools(SchoolID) ON DELETE CASCADE ON UPDATE CASCADE
    );
""")

c.execute("""
    CREATE TABLE IF NOT EXISTS ClassTeachers (
        ClassTeacherID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        ClassID INTEGER NOT NULL,
        TeacherID INTEGER NOT NULL,
        FOREIGN KEY(ClassID) REFERENCES Classes(ClassID) ON DELETE CASCADE ON UPDATE CASCADE,
        FOREIGN KEY(TeacherID) REFERENCES Teachers(TeacherID) ON DELETE CASCADE ON UPDATE CASCADE
    );
""")

c.execute("""
    CREATE TABLE IF NOT EXISTS Enrollment (
        EnrollmentID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        StudentID INTEGER NOT NULL,
        ClassID INTEGER NOT NULL,
        DateEnrolled DATE DEFAULT current_date NOT NULL,
        FOREIGN KEY(StudentID) REFERENCES Students(StudentID) ON DELETE CASCADE ON UPDATE CASCADE,
        FOREIGN KEY(ClassID) REFERENCES Classes(ClassID) ON DELETE CASCADE ON UPDATE CASCADE
    );
""")

c.execute("""
    CREATE TABLE IF NOT EXISTS StudentAvailability (
        AvailabilityID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        StudentID INTEGER NOT NULL,
        TimeID INTEGER NOT NULL,
        FOREIGN KEY(StudentID) REFERENCES Students(StudentID) ON DELETE CASCADE ON UPDATE CASCADE,
        FOREIGN KEY(TimeID) REFERENCES Times(TimeID) ON DELETE CASCADE ON UPDATE CASCADE
    );
""")

c.execute("""
    CREATE TABLE IF NOT EXISTS Times (
        TimeID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        StartTime TEXT NOT NULL,
        EndTime TEXT NOT NULL
    );
""")

c.execute("""
    CREATE TABLE IF NOT EXISTS Schools (
        SchoolID INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
        SchoolName TEXT NOT NULL
    );
""")

connection.commit()

def log_in():
    valid_option = False
    while not valid_option:
        existing_user = input("Are you an existing user Y/N: ")
        if existing_user.lower() == "y" or existing_user.lower() == "yes":
            existing_user = True
            valid_option = True
        elif existing_user.lower() == "n" or existing_user.lower() == "no":
            existing_user = False
            valid_option = True
        else:
            print("Invalid Option! Try again.")

    if existing_user:
        verified = False

        while not verified:
            email = input("Email: ")
            databaseHash = c.execute("SELECT passwordHash FROM Users WHERE email=?", (email,))
            data = databaseHash.fetchone()

            if data is None:
                print("Email not found. Please try again.")
                continue

            password_checked = False
            while not password_checked:
                password = input("Password: ")
                try:
                    if ph.verify(data[0], password):
                        print("Login successful!")
                        password_checked = True
                        verified = True
                except Exception:
                    print("Incorrect password. Please try again.")

    if not existing_user:
        first_name = input("First Name: ")
        last_name = input("Last Name: ")
        email = input("Email: ")
        password = input("Password: ")
        user_role = input("User Role (e.g., Student, Teacher): ")
        school_id = int(input("School ID: "))

        hashed_password = ph.hash(password)
        c.execute("INSERT INTO Users(FirstName, LastName, Email, PasswordHash, UserRole, SchoolID) VALUES(?, ?, ?, ?, ?, ?);", 
                  (first_name, last_name, email, hashed_password, user_role, school_id))
        connection.commit()
        print("Registration successful!")

log_in()