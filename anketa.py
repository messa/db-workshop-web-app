from datetime import datetime
import flask
import sqlite3


app = flask.Flask(__name__)


@app.before_request
def before():
    flask.g.conn = get_conn()


@app.before_first_request
def before_first():
    conn = get_conn()
    prepare_schema(conn)


@app.route('/')
def index():
    return flask.render_template('index.html',
        suggestions=list_suggestions(flask.g.conn))


@app.route('/add-suggestion', methods=['POST'])
def add_suggestion():
    title = flask.request.form['suggestion']
    insert_suggestion(flask.g.conn, title, None)
    return flask.redirect('/')


@app.route('/vote', methods=['POST'])
def vote():
    sug_id = flask.request.form['suggestion_id']
    if flask.request.form['action'] == 'upvote':
        insert_vote(flask.g.conn, sug_id, None, True)
    elif flask.request.form['action'] == 'downvote':
        insert_vote(flask.g.conn, sug_id, None, False)
    return flask.redirect('/')


def get_conn():
    return sqlite3.connect('anketa.db')


def prepare_schema(conn):
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS suggestions (
            id INTEGER PRIMARY KEY,
            title TEXT,
            date DATE,
            cookie TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY,
            suggestion_id TEXT,
            date DATE,
            cookie TEXT,
            value INTEGER
        )
    ''')


def insert_suggestion(conn, title, cookie, date=None):
    date = date or datetime.utcnow()
    c = conn.cursor()
    c.execute(
        "INSERT INTO suggestions (title, date, cookie) VALUES (?, ?, ?)",
        (title, date.isoformat(), cookie))
    conn.commit()
    return c.lastrowid


def insert_vote(conn, suggestion_id, cookie, upvote, date=None):
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
    conn.commit()


def list_suggestions(conn):
    c = conn.cursor()
    c.execute('''
        SELECT
            suggestions.id,
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
            'id': row[0],
            'title': row[1],
            'vote_count': row[2],
        })
    return suggestions


if __name__ == '__main__':
    app.run(debug=True)
