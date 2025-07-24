import sqlite3
import hashlib
from argon2 import PasswordHasher

ph = PasswordHasher()

connection = sqlite3.connect("Users.db")
c = connection.cursor()
print(c)

c.execute("""
    CREATE TABLE IF NOT EXISTS
Users (
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




def hash(input_text):
    hashed = ph.hash("input_text")
    return hashed

#c.execute("INSERT INTO Users(FirstName, LastName, Email, PasswordHash, UserRole, SchoolID) VALUES(?, ?, ?, ?, ?, ?);", ("Yog", "Nungra", "yognungra@gmail.com", ph.hash("yognungra"), "Student", 1))
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
            password = input("Password: ")
            databaseHash = c.execute("SELECT passwordHash FROM Users WHERE email=?", (email,))
            data = databaseHash.fetchone()
            try:
                print(ph.verify(data[0], password))
            except Exception as e:
                print("ERROR:", e)

log_in()