from datetime import datetime
from pathlib import Path
from pytest import fixture
import sqlite3

import anketa

# BTW: http://flask.pocoo.org/docs/0.12/testing/


@fixture
def test_client():
    return anketa.app.test_client()


def test_render_index(test_client):
    rv = test_client.get('/')
    assert b'Anketa' in rv.data


@fixture
def temp_dir(tmpdir):
    # I like standard pathlib.Path more than py.path :)
    return Path(str(tmpdir))


def test_smoke_sqlite3(temp_dir):
    # just an example of sqlite3 usage from Python docs:
    # https://docs.python.org/3.6/library/sqlite3.html
    conn = sqlite3.connect(str(temp_dir / 'example.db'))
    c = conn.cursor()
    c.execute('''CREATE TABLE stocks
                 (date text, trans text, symbol text, qty real, price real)''')
    c.execute("INSERT INTO stocks VALUES ('2006-01-05','BUY','RHAT',100,35.14)")
    conn.commit()
    conn.close()


def test_workflow_prototype(temp_dir):
    conn = sqlite3.connect(str(temp_dir / 'workflow.db'))
    c = conn.cursor()
    c.execute('''
        CREATE TABLE suggestions (
            id INTEGER PRIMARY KEY,
            title TEXT,
            date DATE,
            cookie TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE votes (
            id INTEGER PRIMARY KEY,
            suggestion_id TEXT,
            date DATE,
            cookie TEXT,
            value INTEGER
        )
    ''')
    c.execute(
        "INSERT INTO suggestions (title, date, cookie) VALUES (?, ?, ?)",
        ('Tvorba webu', datetime(2017, 3, 15, 12, 0).isoformat(), 'cookie1'))
    sug1_id = c.lastrowid
    c.execute(
        "INSERT INTO suggestions (title, date, cookie) VALUES (?, ?, ?)",
        ('Statistika', datetime(2017, 3, 15, 12, 10).isoformat(), 'cookie1'))
    # add some upvotes
    c.execute(
        "INSERT INTO votes (suggestion_id, date, cookie, value) VALUES (?, ?, ?, ?)",
        (sug1_id, datetime(2017, 3, 15, 13, 0).isoformat(), 'cookie1', 1))
    c.execute(
        "INSERT INTO votes (suggestion_id, date, cookie, value) VALUES (?, ?, ?, ?)",
        (sug1_id, datetime(2017, 3, 15, 13, 0).isoformat(), 'cookie2', 1))
    # add some downvote
    c.execute(
        "INSERT INTO votes (suggestion_id, date, cookie, value) VALUES (?, ?, ?, ?)",
        (sug1_id, datetime(2017, 3, 15, 13, 0).isoformat(), 'cookie3', -1))

    # the most important query :)
    c.execute('''
        SELECT
            suggestions.title,
            COALESCE(SUM(votes.value), 0) AS vote_count
        FROM suggestions
        LEFT JOIN votes ON (votes.suggestion_id = suggestions.id)
        GROUP BY suggestions.id
        ORDER BY vote_count DESC
    ''')
    rows = c.fetchall()
    assert rows == [
        ('Tvorba webu', 1),
        ('Statistika', 0),
    ]
