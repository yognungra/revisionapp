import sqlite3
import hashlib
from argon2 import PasswordHasher

ph = PasswordHasher()

connection = sqlite3.connect("Users.db")
c = connection.cursor()
c.execute("PRAGMA foreign_keys = ON;")

connection.commit()

global current_user_token
current_user_token = None

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

c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email ON Users(Email);")


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
                        c.execute("SELECT userID FROM Users WHERE email=?", (email,))  # Set the current user token
                        current_user_token = c.fetchone()[0]
                        print(f"Current User Token: {current_user_token}")
                except Exception:
                    print("Incorrect password. Please try again.")
    else:
        sign_up()


def sign_up():
    print("Please fill in the following details to sign up:")
    # Additional sign-up logic can be added here if needed
    first_name = input("First Name: ")
    last_name = input("Last Name: ")
    email = input("Email: ")

    # Check if email already exists
    while True:
        email_check = c.execute("SELECT Email FROM Users WHERE Email=?", (email,))
        if email_check.fetchone() is not None:
            print("Email already exists. Please try a different email.")
            email = input("Email: ")
        else:
            break

    password = input("Password: ")
    user_role_verified = False

    while not user_role_verified:
        user_role = input("User Role (Student/Teacher): ").strip().capitalize()
        if user_role.lower() in ["student", "teacher"]:
            user_role_verified = True
        else:
            print("Invalid role. Please enter 'Student' or 'Teacher'.")
    school_id = int(input("School ID (provided by your teacher): "))
    hashed_password = ph.hash(password)
    c.execute("INSERT INTO Users(FirstName, LastName, Email, PasswordHash, UserRole, SchoolID) VALUES(?, ?, ?, ?, ?, ?);", 
              (first_name, last_name, email, hashed_password, user_role, school_id))
    
    if user_role.lower() == "student":
        year_group = int(input("Year Group: "))
        c.execute("INSERT INTO Students(YearGroup, UserID) VALUES(?, (SELECT UserID FROM Users WHERE Email=?));", 
                  (year_group, email))
    elif user_role.lower() == "teacher":
        c.execute("INSERT INTO Teachers(UserID) VALUES((SELECT UserID FROM Users WHERE Email=?));", 
                  (email,))
        
    connection.commit()
    print("Registration successful!")

def add_school():
    school_name = input("Enter the school name: ")
    c.execute("INSERT INTO Schools(SchoolName) VALUES(?);", (school_name,))
    connection.commit()
    print("School added successfully!")

def add_class():
    if current_user_token is None:
        print("You must be logged in to add a class.")
        return
    
    if c.execute("SELECT UserRole FROM Users WHERE UserID=?", (current_user_token,)).fetchone()[0].lower() != "teacher":
        print("Entry denied! Only teachers can add classes.")
        return False
    
    local_class_identifier = input("Enter the local class identifier: ")
    school_id = int(input("Enter the school ID: "))
    c.execute("INSERT INTO Classes(LocalClassIdentifier, SchoolID) VALUES(?, ?);", 
              (local_class_identifier, school_id))
    connection.commit()
    print("Class added successfully!")

    return True

def add_teacher_to_class():
    if current_user_token is None:
        print("You must be logged in to add a teacher to a class.")
        return
    
    if c.execute("SELECT UserRole FROM Users WHERE UserID=?", (current_user_token,)).fetchone()[0].lower() != "teacher":
        print("Entry denied! Only teachrs can add teachers to classes.")
        return False
    class_id = int(input("Enter the class ID: "))
    teacher_id = int(input("Enter the teacher ID: "))
    c.execute("INSERT INTO ClassTeachers(ClassID, TeacherID) VALUES(?, ?);", 
              (class_id, teacher_id))
    connection.commit()
    print("Teacher added to class successfully!")
    return True

def add_student_to_class():
    if current_user_token is None:
        print("You must be logged in to add a student to a class.")
        return
    
    if c.execute("SELECT UserRole FROM Users WHERE UserID=?", (current_user_token,)).fetchone()[0].lower() != "teacher":
        print("Entry denied! Only teachers can add students to classes.")
        return False
    
    student_id = int(input("Enter the student ID: "))
    class_id = int(input("Enter the class ID: "))
    c.execute("INSERT INTO Enrollment(StudentID, ClassID) VALUES(?, ?);", 
              (student_id, class_id))
    connection.commit()
    print("Student added to class successfully!")
    return True

def add_student_availability():
    if current_user_token is None:
        print("You must be logged in to add student availability.")
        return
    
    student_id = int(input("Enter the student ID: "))
    start_time = input("Enter the start time (HH:MM) of when you : ")
    end_time = input("Enter the end time (HH:MM): ")
    c.execute("INSERT INTO StudentAvailability(StudentID, TimeID) VALUES(?, ?);", 
              (student_id, time_id))
    connection.commit()
    print("Student availability added successfully!")

log_in()