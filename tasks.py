from databasee import get_school_id, get_teacher_id, get_student_id
from session import session
from main import c, connection
from datetime import datetime
from databasee import get_school_id, get_teacher_id, get_student_id, get_user_role, ensure_logged_in

import sqlite3
import hashlib
from argon2 import PasswordHasher
from datetime import datetime
import json
import random
import pandas as pd
import os
import sqlite3


def add_homework_task():
    global current_user_token
    if session.is_logged_in() is False:
        print("You must be logged in to add a homework task.")
        return
    
    if not session.require_role("teacher"):
        print("Entry denied! Only teachers can add homework tasks.")
        return False
    
    teacher_id = get_teacher_id(session.get_user_id())
    classes = c.execute("SELECT ClassID, LocalClassIdentifier FROM Classes WHERE SchoolID=(SELECT SchoolID FROM Users WHERE UserID=?)", (session.get_user_id(),)).fetchall()

    if not classes:
        print("You are not associated with any classes. Please create a class first.")
        return False
    
    print("Classes you are associated with:")
    for index, (class_id, local_class_identifier) in enumerate(classes, start=1):
        print(f"{index}. Class ID: {class_id}, Local Class Identifier: {local_class_identifier}")

    class_choice_verified = False
    while not class_choice_verified:
        class_choice = int(input("Select the class by number: ")) - 1
        if class_choice < 0 or class_choice >= len(classes):
            print("Invalid choice. Please try again.")
        else:
            class_choice_verified = True
    
    selected_class_id = classes[class_choice][0]

    title = input("Enter the homework task title: ")
    description = input("Enter the homework task description: ")

    while True:
        try:
            time_to_complete = int(input("Enter the estimated time to complete (in minutes): "))
            if time_to_complete <= 0:
                raise ValueError("Time must be a positive integer.")
            break
        except ValueError as e:
            print(f"Invalid input: {e}. Please enter a valid number.")
            continue

        

    due_date_verified = False

    while not due_date_verified:
        due_date_input = input("Enter the due date (DD-MM-YYYY): ")
        try:
            due_date = datetime.strptime(due_date_input, "%d-%m-%Y").date()
            if due_date < datetime.now().date():
                print("Due date cannot be in the past. Please enter a valid date.")
                continue
            due_date_verified = True
        except ValueError:
            print("Invalid date format. Please use DD-MM-YYYY format.")
            continue
    
    homework_type_choice_verified = False
    homework_types = ["Quiz", "Assignment", "Project", "Other"]
    
    while not homework_type_choice_verified:
        print("Select the type of homework task:")
        for index, homework_type in enumerate(homework_types, start=1):
            print(f"{index}. {homework_type}")
        
        try:
            homework_type_choice = int(input("Enter the number corresponding to the homework type: ")) - 1
            if homework_type_choice < 0 or homework_type_choice >= len(homework_types):
                raise ValueError("Invalid choice. Please select a valid option.")
            homework_type_choice = homework_types[homework_type_choice]
            homework_type_choice_verified = True
        except ValueError as e:
            print(f"Error: {e}. Please try again.")

    if homework_type_choice == "Quiz":
        assignment_id = input("Enter the Quiz ID (or leave blank to create a new quiz): ").strip()
        if assignment_id:
            try:
                assignment_id = int(assignment_id)
                c.execute("SELECT AssignmentID FROM QuizQuestionAssignmnts WHERE QuizID=?", (assignment_id,))
                if c.fetchone() is None:
                    print("Quiz ID does not exist. Creating a new quiz.")
                    assignment_id = None
            except ValueError:
                print("Invalid Quiz ID. Creating a new quiz.")
                assignment_id = None
        if not assignment_id:
            print("Create a new quiz first then come back to add the homework task.")
            return False
    
    c.execute("INSERT INTO HomeworkTasks(Title, Description, TimeToComplete, DueDate, HomeworkType, ClassID, TeacherID, AssignmentID) VALUES(?, ?, ?, ?, ?, ?, ?, ?);",
                  (title, description, time_to_complete, due_date, homework_type_choice, selected_class_id, teacher_id, assignment_id))


    connection.commit()
    return True 
    




def create_quiz_from_pool():
    global current_user_token
    if session.is_logged_in() is False:
        print("You must be logged in to create a quiz.")
        return
    if get_user_role(session.get_user_id()) != "teacher":
        print("Only teachers can create quizzes.")
        return
    
    teacher_id = get_teacher_id(session.get_user_id())
    school_id = get_school_id(session.get_user_id())

    # Select class
    classes = c.execute("""
        SELECT ClassID, LocalClassIdentifier
        FROM Classes
        WHERE SchoolID = ?
    """, (school_id,)).fetchall()
    
    if not classes:
        print("No classes found in your school.")
        return
    
    print("Select a class for the quiz:")
    for i, (class_id, name) in enumerate(classes, start=1):
        print(f"{i}. {name} (Class ID: {class_id})")
    choice = int(input("Enter number: ")) - 1
    class_id = classes[choice][0]
    
    quiz_title = input("Enter quiz title: ")
    c.execute("INSERT INTO Quizzes (Title, ClassID, TeacherID) VALUES (?, ?, ?)", (quiz_title, class_id, teacher_id))
    c.execute("""
    SELECT QuizID
    FROM Quizzes
    WHERE Title = ? AND ClassID = ? AND TeacherID = ?
    ORDER BY QuizID ASC
""", (quiz_title, class_id, teacher_id))
    quiz_id = c.fetchone()[-1]

    # Select topic
    topics = c.execute("SELECT TopicID, TopicName FROM QuestionTopics WHERE SchoolID=?", (school_id,)).fetchall()
    if not topics:
        print("No topics found for your school.")
        return
    print("Available Topics:")
    for tid, tname in topics:
        print(f"{tid}. {tname}")
    topic_id = int(input("Enter topic ID: "))

    # Select questions from topic
    questions = c.execute("""
        SELECT QuestionID, QuestionText, DifficultyLevel
        FROM QuizQuestions
        WHERE SchoolID=? AND TopicID=?
    """, (school_id, topic_id)).fetchall()
    if not questions:
        print("No questions found for that topic.")
        return
    for qid, text, diff in questions:
        print(f"QID {qid} [{diff}]: {text}")
    
    selected_ids = input("Enter question IDs to add (comma-separated): ").split(",")
    for qid in selected_ids:
        c.execute("INSERT INTO QuizQuestionAssignments (QuizID, QuestionID) VALUES (?, ?)", (quiz_id, int(qid)))
    
    connection.commit()

    print(f"✅ Quiz '{quiz_title}' created successfully with ID {quiz_id}")

def get_next_question(student_id, quiz_id):
    # Get last answered question
    last_result = c.execute("""
        SELECT sr.QuestionID, q.DifficultyLevel, q.CorrectAnswer, sr.AnswerGiven
        FROM StudentQuizResults sr
        JOIN QuizQuestions q ON sr.QuestionID = q.QuestionID
        WHERE sr.StudentID = ? AND sr.HomeworkID = ?
        ORDER BY sr.ResultID DESC LIMIT 1
    """, (student_id, quiz_id)).fetchone()
    
    if last_result is None:
        # Start with Medium difficulty
        return c.execute("""
            SELECT q.QuestionID, q.QuestionText, q.AnswerOptions
            FROM QuizQuestionAssignments qa
            JOIN QuizQuestions q ON qa.QuestionID = q.QuestionID
            WHERE qa.QuizID = ? AND q.DifficultyLevel = 'Medium'
            LIMIT 1
        """, (quiz_id,)).fetchone()
    
    last_qid, last_diff, correct_answer, answer_given = last_result
    was_correct = (correct_answer.strip().lower() == (answer_given or "").strip().lower())
    
    # Difficulty adjustment
    diff_levels = ["Easy", "Medium", "Hard"]
    idx = diff_levels.index(last_diff)
    if was_correct and idx < 2:
        next_diff = diff_levels[idx + 1]
    elif not was_correct and idx > 0:
        next_diff = diff_levels[idx - 1]
    else:
        next_diff = last_diff
    
    # Get next unused question of adjusted difficulty
    return c.execute("""
        SELECT q.QuestionID, q.QuestionText, q.AnswerOptions
        FROM QuizQuestionAssignments qa
        JOIN QuizQuestions q ON qa.QuestionID = q.QuestionID
        WHERE qa.QuizID = ?
          AND q.DifficultyLevel = ?
          AND q.QuestionID NOT IN (
              SELECT QuestionID
              FROM StudentQuizResults
              WHERE StudentID = ? AND HomeworkID = ?
          )
        LIMIT 1
    """, (quiz_id, next_diff, student_id, quiz_id)).fetchone()

def add_topic():
    if session.is_logged_in() is False:
        print("You must be logged in to add a topic.")
        return
    if not session.require_role("teacher"):
        print("Only teachers can add topics.")
        return

    school_id = get_school_id(session.get_user_id())
    topic_name = input("Enter topic name: ").strip()

    try:
        c.execute("""
            INSERT INTO QuestionTopics (SchoolID, TopicName)
            VALUES (?, ?)
        """, (school_id, topic_name))
        connection.commit()
        print(f"✅ Topic '{topic_name}' added to your school’s pool.")
    except sqlite3.IntegrityError:
        print(f"⚠️ Topic '{topic_name}' already exists in your school.")


def add_quiz_question():
    if session.is_logged_in() is False:
        print("You must be logged in to add a quiz question.")
        return
    if not session.require_role("teacher"):
        print("Only teachers can add quiz questions.")
        return

    school_id = get_school_id(session.get_user_id())

    # Select topic
    topics = c.execute("""
        SELECT TopicID, TopicName
        FROM QuestionTopics
        WHERE SchoolID = ?
    """, (school_id,)).fetchall()

    if not topics:
        print("⚠️ No topics available. Please add a topic first.")
        return

    print("\nAvailable Topics:")
    for tid, tname in topics:
        print(f"{tid}. {tname}")

    topic_id = int(input("Enter Topic ID: "))

    # Question details
    question_text = input("Enter the question text: ").strip()
    difficulty = input("Enter difficulty (Easy, Medium, Hard): ").capitalize()
    if difficulty not in ["Easy", "Medium", "Hard"]:
        print("❌ Invalid difficulty.")
        return

    options = []
    print("Enter 4 answer options:")
    for i in range(4):
        options.append(input(f"Option {i+1}: ").strip())

    correct_answer = input("Enter the correct answer exactly as written above: ").strip()

    # Store as JSON
    answer_options_json = json.dumps(options)

    c.execute("""
        INSERT INTO QuizQuestions (
            SchoolID, TopicID, QuestionText, DifficultyLevel, AnswerOptions, CorrectAnswer
        ) VALUES (?, ?, ?, ?, ?, ?)
    """, (school_id, topic_id, question_text, difficulty, answer_options_json, correct_answer))

    connection.commit()
    print("✅ Question added successfully to your school’s question pool.")

def bulk_upload_questions():
    if session.is_logged_in() is False:
        print("You must be logged in to upload questions.")
        return
    if not session.require_role("teacher"):
        print("Only teachers can upload questions.")
        return

    school_id = get_school_id(session.get_user_id())
    file_path = input("Enter path to your CSV or Excel file: ").strip()

    if not os.path.exists(file_path):
        print("❌ File not found.")
        return

    try:
        if file_path.lower().endswith(".csv"):
            df = pd.read_csv(file_path)
        elif file_path.lower().endswith((".xlsx", ".xls")):
            df = pd.read_excel(file_path)
        else:
            print("❌ Unsupported file format. Use CSV or Excel.")
            return
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return

    required_cols = ["TopicName", "Difficulty", "QuestionText",
                     "Option1", "Option2", "Option3", "Option4", "CorrectAnswer"]

    if not all(col in df.columns for col in required_cols):
        print(f"❌ Missing required columns. Must include: {', '.join(required_cols)}")
        return

    added_count = 0
    updated_count = 0

    for _, row in df.iterrows():
        topic_name = str(row["TopicName"]).strip()
        difficulty = str(row["Difficulty"]).capitalize()
        if difficulty not in ["Easy", "Medium", "Hard"]:
            print(f"⚠️ Skipping invalid difficulty '{difficulty}' for question: {row['QuestionText']}")
            continue

        # Ensure topic exists
        topic_row = c.execute("""
            SELECT TopicID FROM QuestionTopics
            WHERE SchoolID = ? AND TopicName = ?
        """, (school_id, topic_name)).fetchone()

        if topic_row:
            topic_id = topic_row[0]
        else:
            c.execute("""
                INSERT INTO QuestionTopics (SchoolID, TopicName) VALUES (?, ?)
            """, (school_id, topic_name))
            topic_id = c.lastrowid

        options = [str(row[f"Option{i}"]).strip() for i in range(1, 5)]
        correct_answer = str(row["CorrectAnswer"]).strip()

        # Check if question already exists
        existing_question = c.execute("""
            SELECT QuestionID FROM QuizQuestions
            WHERE SchoolID = ? AND TopicID = ? AND QuestionText = ?
        """, (school_id, topic_id, row["QuestionText"])).fetchone()

        if existing_question:
            # Update existing question
            c.execute("""
                UPDATE QuizQuestions
                SET DifficultyLevel = ?, AnswerOptions = ?, CorrectAnswer = ?
                WHERE QuestionID = ?
            """, (difficulty, json.dumps(options), correct_answer, existing_question[0]))
            updated_count += 1
        else:
            # Insert new question
            c.execute("""
                INSERT INTO QuizQuestions (
                    SchoolID, TopicID, QuestionText, DifficultyLevel, AnswerOptions, CorrectAnswer
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (school_id, topic_id, row["QuestionText"], difficulty, json.dumps(options), correct_answer))
            added_count += 1

    connection.commit()
    print(f"✅ Bulk upload complete — Added: {added_count}, Updated: {updated_count}")

def generate_question_template():
    import pandas as pd

    template_data = {
        "TopicName": ["Example: Algebra"],
        "Difficulty": ["Easy"],  # Options: Easy, Medium, Hard
        "QuestionText": ["Example: What is 2+2?"],
        "Option1": ["3"],
        "Option2": ["4"],
        "Option3": ["5"],
        "Option4": ["6"],
        "CorrectAnswer": ["4"]
    }

    df = pd.DataFrame(template_data)

    # Ask teacher for file format
    file_type = input("Save as CSV or Excel? (csv/xlsx): ").strip().lower()
    file_name = input("Enter file name (without extension): ").strip()

    if file_type == "csv":
        file_path = f"{file_name}.csv"
        df.to_csv(file_path, index=False)
    elif file_type == "xlsx":
        file_path = f"{file_name}.xlsx"
        df.to_excel(file_path, index=False)
    else:
        print("❌ Invalid file type. Please choose 'csv' or 'xlsx'.")
        return

    print(f"✅ Template saved as {file_path}. Fill it out and use Bulk Upload Questions.")

from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation

def generate_upload_template():
    global current_user_token
    if session.is_logged_in() is False:
        print("❌ You must be logged in to generate the template.")
        return

    role = session.role.lower()
    if role != "teacher":
        print("❌ Only teachers can generate the upload template.")
        return

    school_id = get_school_id(session.get_user_id())

    # Get topic names for dropdown
    topic_rows = c.execute("SELECT TopicName FROM QuestionTopics WHERE SchoolID=?", (school_id,)).fetchall()
    topics = [row[0] for row in topic_rows]

    wb = Workbook()
    ws = wb.active
    ws.title = "Upload Template"

    headers = ["TopicName", "Difficulty", "QuestionText",
               "Option1", "Option2", "Option3", "Option4", "CorrectAnswer"]
    ws.append(headers)

    # Dropdown for TopicName
    if topics:
        dv_topics = DataValidation(type="list", formula1=f'"{",".join(topics)}"', allow_blank=False)
        ws.add_data_validation(dv_topics)
        dv_topics.add("A2:A1048576")  # entire TopicName column

    # Dropdown for Difficulty
    difficulties = ["Easy", "Medium", "Hard"]
    dv_diff = DataValidation(type="list", formula1=f'"{",".join(difficulties)}"', allow_blank=False)
    ws.add_data_validation(dv_diff)
    dv_diff.add("B2:B1048576")

    filename = f"upload_template_school_{school_id}.xlsx"
    wb.save(filename)
    print(f"✅ Upload template generated: {filename}")
