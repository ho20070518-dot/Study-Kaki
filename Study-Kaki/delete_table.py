import sqlite3

conn = sqlite3.connect("database.db")

conn.execute("DROP TABLE IF EXISTS question_votes")

conn.commit()
conn.close()

print("question_votes table deleted successfully.")