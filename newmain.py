import sqlite3
import hashlib
from argon2 import PasswordHasher
from datetime import datetime
import json
import random
import pandas as pd
import os

from auth import log_in, logout, student_options, teacher_options
from tasks import add_homework_task, create_quiz_from_pool, add_topic, add_quiz_question, bulk_upload_questions
from school import add_school, add_class, add_teacher_to_class, add_student_to_class, approve_enrollment_request, add_period, add_teacher_to_school, approve_school_join_request, request_to_join_school
from databasee import create_indexes


# Connect to the SQLite database
connection = sqlite3.connect("tables.db")
c = connection.cursor()
c.execute("PRAGMA foreign_keys = ON;")

connection.commit()


global current_user_token
current_user_token = None

# Helper functions
def get_user_role(user_id):
    return c.execute("SELECT UserRole FROM Users WHERE UserID=?", (user_id,)).fetchone()[0].lower()

def get_school_id(user_id):
    return c.execute("SELECT SchoolID FROM Users WHERE UserID=?", (user_id,)).fetchone()[0]

def get_teacher_id(user_id):
    return c.execute("SELECT TeacherID FROM Teachers WHERE UserID=?", (user_id,)).fetchone()[0]

def get_student_id(user_id):
    return c.execute("SELECT StudentID FROM Students WHERE UserID=?", (user_id,)).fetchone()[0]





create_indexes()
log_in()