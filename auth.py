from databasee import connection, c
from auth import session
from datetime import datetime

import sqlite3
import hashlib
from argon2 import PasswordHasher
from datetime import datetime
import json
import random
import pandas as pd
import os

ph = PasswordHasher()

current_user_token = None

from session import session
from school import add_school, add_class, add_teacher_to_class, add_student_to_class, approve_enrollment_request, add_period, add_teacher_to_school, approve_school_join_request, request_to_join_school
from tasks import add_homework_task, create_quiz_from_pool, add_topic, add_quiz_question, bulk_upload_questions, add_busy_time, request_to_join_class

def log_in():
    global current_user_token
    print("Welcome to the Revision App!")
    while True:
        choice = input("Are you an existing user (Y/N)? Or type 'Q' to quit: ").strip().lower()
        if choice == 'y':
            return login_flow()
        elif choice == 'n':
            return sign_up()
        elif choice == 'q':
            print("Exiting the application.")
            exit()
        else:
            print("Invalid option. Try again.")

def login_flow():
    global current_user_token
    while True:
        email = input("Email: ")
        row = c.execute("SELECT UserID, PasswordHash, UserRole FROM Users WHERE Email=?", (email,)).fetchone()
        if not row:
            print("Email not found. Please try again.")
            continue

        user_id, password_hash, role = row
        password = input("Password: ")
        try:
            ph.verify(password_hash, password)
            session.login(user_id, role)
            print(f"✅ Login successful! User ID: {session.get_user_id()}")
            return student_options() if role.lower() == "student" else teacher_options()
        except:
            print("❌ Incorrect password. Please try again.")

def sign_up():
    global current_user_token
    print("Please fill in the following details to sign up:")
    first_name = input("First Name: ")
    last_name = input("Last Name: ")

    # Email uniqueness
    while True:
        email = input("Email: ")
        if c.execute("SELECT 1 FROM Users WHERE Email=?", (email,)).fetchone():
            print("⚠️ Email already exists. Try a different one.")
        else:
            break

    # Password and Role
    password = input("Password: ")
    hashed_password = ph.hash(password)

    while True:
        user_role = input("User Role (Student/Teacher): ").strip().lower()
        if user_role in ["student", "teacher"]:
            break
        print("Invalid role. Please enter 'Student' or 'Teacher'.")

    # Optional School ID
    school_id = None
    school_input = input("School ID (leave blank if none): ").strip()
    if school_input:
        try:
            school_id = int(school_input)
            if not c.execute("SELECT 1 FROM Schools WHERE SchoolID=?", (school_id,)).fetchone():
                print("⚠️ Invalid school ID. Ignoring.")
                school_id = None
        except:
            print("⚠️ Invalid input. Ignoring school ID.")

    # Insert User
    c.execute("""INSERT INTO Users (FirstName, LastName, Email, PasswordHash, UserRole)
                 VALUES (?, ?, ?, ?, ?)""", (first_name, last_name, email, hashed_password, user_role))
    connection.commit()
    
    user_id = c.execute("SELECT UserID FROM Users WHERE Email=?", (email,)).fetchone()[0]
    current_user_token = user_id
    session.login(user_id, user_role)

    if school_id:
        c.execute("INSERT INTO SchoolJoinRequests (UserID, SchoolID) VALUES (?, ?)", (current_user_token, school_id))
    connection.commit()

    if user_role == "student":
        year_group = int(input("Year Group: "))
        c.execute("INSERT INTO Students (YearGroup, UserID) VALUES (?, ?)", (year_group, user_id))
    else:
        c.execute("INSERT INTO Teachers (UserID) VALUES (?)", (user_id,))

    connection.commit()
    print("🎉 Registration complete!")
    return student_options() if user_role == "student" else teacher_options()


def logout():
    global current_user_token
    if session.is_logged_in() is False:
        print("You are not logged in.")
        log_in()
        return
    print("Logging out...")
    current_user_token = None
    session.logout()
    print("You have been logged out successfully.")
    log_in()  # Redirect to login after logout

def student_options():
    actions = {
        "1": request_to_join_class,
        "2": add_busy_time,
        "3": request_to_join_school,
        "4": logout
    }
    while current_user_token:
        print("\n📘 Student Menu:")
        print("1. Request to join a class")
        print("2. Add busy time")
        print("3. Request to join a school")
        print("4. Log out")
        action = input("Choose an option: ")
        if action in actions:
            actions[action]()
        else:
            print("❌ Invalid option.")

def teacher_options():
    actions = {
        "1": add_school,
        "2": add_class,
        "3": add_teacher_to_class,
        "4": add_student_to_class,
        "5": approve_enrollment_request,
        "6": add_period,
        "7": add_teacher_to_school,
        "8": approve_school_join_request,
        "9": request_to_join_school,
        "10": add_homework_task,
        "11": create_quiz_from_pool,
        "12": add_topic,
        "13": add_quiz_question,
        "14": bulk_upload_questions,  # NEW
        "15": logout
    }
    while current_user_token:
        print("\n📗 Teacher Menu:")
        for k, v in actions.items():
            label = v.__name__.replace("_", " ").title()
            print(f"{k}. {label}")
        action = input("Choose an option: ")
        if action in actions:
            actions[action]()
        else:
            print("❌ Invalid option.")

def create_indexes():
    # Creating indexes to speed up queries
    try:
        c.execute("CREATE INDEX IF NOT EXISTS idx_school_id ON Users(SchoolID);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_class_id ON Enrollment(ClassID);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON Users(UserID);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_student_id ON Enrollment(StudentID);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_teacher_id ON ClassTeachers(TeacherID);")
        c.execute("CREATE INDEX IF NOT EXISTS idx_classes_class_id ON Classes(ClassID);")
        connection.commit()
        print("Indexes created successfully!")
    except sqlite3.DatabaseError as e:
        print(f"Error creating indexes: {e}")


create_indexes()
# Start the login process
log_in()