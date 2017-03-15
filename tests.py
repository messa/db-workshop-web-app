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
    anketa.prepare_schema(conn)
    sug1_id = anketa.insert_suggestion(
        conn, 'Tvorba webu', 'cookie1', date=datetime(2017, 3, 15, 12, 0))
    sug2_id = anketa.insert_suggestion(
        conn, 'Statistika', 'cookie1', date=datetime(2017, 3, 15, 13, 0))
    # add some upvotes
    anketa.insert_upvote(conn, sug1_id, 'cookie1', upvote=True, date=datetime(2017, 3, 15, 13, 0))
    anketa.insert_upvote(conn, sug1_id, 'cookie2', upvote=True, date=datetime(2017, 3, 15, 13, 0))
    anketa.insert_upvote(conn, sug1_id, 'cookie3', upvote=False, date=datetime(2017, 3, 15, 13, 0))
    # the most important query :)
    rows = anketa.list_suggestions(conn)
    assert rows == [
        {'title': 'Tvorba webu', 'vote_count': 1},
        {'title': 'Statistika',  'vote_count': 0},
    ]
