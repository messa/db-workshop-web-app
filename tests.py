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


def prepare_schema(conn):
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


def test_workflow_prototype(temp_dir):
    conn = sqlite3.connect(str(temp_dir / 'workflow.db'))
    prepare_schema(conn)
    sug1_id = insert_suggestion(
        conn, 'Tvorba webu', 'cookie1', date=datetime(2017, 3, 15, 12, 0))
    sug2_id = insert_suggestion(
        conn, 'Statistika', 'cookie1', date=datetime(2017, 3, 15, 13, 0))
    # add some upvotes
    insert_upvote(conn, sug1_id, 'cookie1', upvote=True, date=datetime(2017, 3, 15, 13, 0))
    insert_upvote(conn, sug1_id, 'cookie2', upvote=True, date=datetime(2017, 3, 15, 13, 0))
    insert_upvote(conn, sug1_id, 'cookie3', upvote=False, date=datetime(2017, 3, 15, 13, 0))
    # the most important query :)
    rows = list_suggestions(conn)
    assert rows == [
        {'title': 'Tvorba webu', 'vote_count': 1},
        {'title': 'Statistika',  'vote_count': 0},
    ]


def insert_suggestion(conn, title, cookie, date=None):
    date = date or datetime.utcnow()
    c = conn.cursor()
    c.execute(
        "INSERT INTO suggestions (title, date, cookie) VALUES (?, ?, ?)",
        (title, date.isoformat(), cookie))
    return c.lastrowid


def insert_upvote(conn, suggestion_id, cookie, upvote, date=None):
    date = date or datetime.utcnow()
    c = conn.cursor()
    c.execute(
        "INSERT INTO votes (suggestion_id, date, cookie, value) "
        "VALUES (?, ?, ?, ?)", (
            int(suggestion_id),
            date.isoformat(),
            cookie,
            1 if upvote else -1,
        ))


def list_suggestions(conn):
    c = conn.cursor()
    c.execute('''
        SELECT
            suggestions.title,
            COALESCE(SUM(votes.value), 0) AS vote_count
        FROM suggestions
        LEFT JOIN votes ON (votes.suggestion_id = suggestions.id)
        GROUP BY suggestions.id
        ORDER BY vote_count DESC
    ''')
    suggestions = []
    for row in c:
        suggestions.append({
            'title': row[0],
            'vote_count': row[1],
        })
    return suggestions
