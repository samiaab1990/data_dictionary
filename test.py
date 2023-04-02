import sqlite3

conn = sqlite3.connect('dictionary.db', check_same_thread=False)
cur = conn.cursor()

username = 'samia'
rows = cur.execute("SELECT username FROM USERS WHERE username = ?", [username])

print(rows.fetchone()[0])
