import sqlite3

exe = """DROP TABLE IF EXISTS seen_jobs;"""

with sqlite3.connect("jobs.sqlite3") as connection:
    connection.execute(exe)