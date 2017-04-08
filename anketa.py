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
    # TODO
    # c.execute('CREATE TABLE ...')


def insert_suggestion(conn, title, cookie, date=None):
    # TODO
    pass


def insert_vote(conn, suggestion_id, cookie, upvote, date=None):
    '''
    Vloží vote pro nějakou suggestion do DB.
    '''
    # TODO
    pass


def list_suggestions(conn):
    '''
    Vrátí seznam suggestions z DB.
    Návratovou hodnotou je list dictů.
    '''
    # TODO
    return [
        {
            'id': 1,
            'title': 'Tvorba webu',
            'vote_count': 10,
        }, {
            'id': 1,
            'title': 'Statistika',
            'vote_count': 8,
        }, {
            'id': 1,
            'title': 'Lineární algebra',
            'vote_count': 5,
        },
    ]


if __name__ == '__main__':
    app.run(debug=True)
