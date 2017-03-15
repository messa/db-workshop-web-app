from datetime import datetime
import flask
import sqlite3

# Flask docs: http://flask.pocoo.org/docs/0.12/
# SQLite docs: https://docs.python.org/3/library/sqlite3.html

app = flask.Flask(__name__)


@app.route('/')
def index():
    '''
    Titulní strana webovky
    '''
    conn = get_conn()
    prepare_schema(conn)
    return flask.render_template('index.html',
        suggestions=list_suggestions(conn))


@app.route('/add-suggestion', methods=['POST'])
def add_suggestion():
    '''
    Vložení návrhu (suggestion).
    Redirectuje zpět na index.
    '''
    title = flask.request.form['suggestion']
    conn = get_conn()
    insert_suggestion(conn, title, None)
    # https://en.wikipedia.org/wiki/Post/Redirect/Get
    return flask.redirect('/')


@app.route('/vote', methods=['POST'])
def vote():
    '''
    Vložení hlasu (vote).
    Redirectuje zpět na index.
    '''
    sug_id = flask.request.form['suggestion_id']
    action = flask.request.form['action']
    conn = get_conn()
    if action == 'upvote':
        is_upvote = True
    elif action == 'downvote':
        is_upvote = False
    else:
        raise Exception('Unknown action {!r}'.format(action))
    insert_vote(conn, sug_id, None, is_upvote)
    return flask.redirect('/')


def get_conn():
    return sqlite3.connect('anketa.db')


def prepare_schema(conn):
    '''
    Vytvoření tabulek, se kterými tato aplikace pracuje.
    Pokud tabulky už existují, tak se nic neděje.
    '''
    c = conn.cursor()
    # https://www.sqlite.org/lang_createtable.html
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
    '''
    Vloží vote pro nějakou suggestion do DB.
    '''
    date = date or datetime.utcnow()
    c = conn.cursor()
    # https://www.sqlite.org/lang_insert.html
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
    '''
    Vrátí seznam suggestions z DB.
    Návratovou hodnotou je list dictů.
    '''
    c = conn.cursor()
    # https://www.sqlite.org/lang_select.html
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
