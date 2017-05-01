#!/usr/bin/env python3

from datetime import datetime
import flask
import os
import requests
from requests_oauthlib import OAuth2Session
import sqlite3
import yaml
from uuid import uuid4

# Flask docs: http://flask.pocoo.org/docs/0.12/
# SQLite docs: https://docs.python.org/3/library/sqlite3.html

app = flask.Flask(__name__)

cfg_path = os.environ['ANKETA_CONF']
with open(cfg_path) as f:
    cfg = yaml.safe_load(f)['anketa']

# secret_key je potřeba pro fungování flask.session
app.secret_key = cfg['secret_key']


@app.route('/')
def index():
    '''
    Titulní strana webovky
    '''
    conn = get_conn()
    prepare_schema(conn)
    return flask.render_template('index.html',
        github_id=get_session_github_id(),
        github_login=get_session_github_login(),
        suggestions=list_suggestions(conn, get_session_github_id()))


def get_session_github_id():
    if flask.session.get('auth'):
        return flask.session['auth'].get('github_id')
    else:
        return None


def get_session_github_login():
    if flask.session.get('auth'):
        return flask.session['auth'].get('github_login')
    else:
        return None


@app.route('/logout')
def logout():
    flask.session['auth'] = None
    return flask.redirect('/')


@app.route('/login/via-github')
def login_via_github():
    from urllib.parse import urlencode
    state = uuid4().hex
    flask.session['auth'] = None
    flask.session['github_login_state'] = state
    url = 'https://github.com/login/oauth/authorize?'
    url += urlencode({
        'client_id': cfg['github']['client_id'],
        'redirect_uri': cfg['github']['callback_url'],
        'scope': 'user:email',
        'state': state,
    })
    return flask.redirect(url)


@app.route('/login/github/oauth-callback')
def login_github_callback():
    # check state
    if flask.request.args['state'] != flask.session['github_login_state']:
        raise Exception('State mismatch')
    # retrieve oauth2 token
    r = requests.post('https://github.com/login/oauth/access_token', data={
        'client_id': cfg['github']['client_id'],
        'client_secret': cfg['github']['client_secret'],
        'code': flask.request.args['code'],
        'state': flask.session['github_login_state'],
        'redirect_uri': cfg['github']['callback_url'],
    }, headers={'accept': 'application/json'})
    try:
        print(r.content)
        r.raise_for_status()
        if not r.json().get('access_token'):
            raise Exception('No access_token')
        flask.session['auth'] = {
            'github_token': r.json(),
        }
    except Exception as e:
        print(e, r.content)
        flask.session['auth'] = None
        return flask.redirect('/login/via-github')
    try:
        # retrieve user info
        # https://github.com/requests/requests-oauthlib/blob/master/docs/examples/real_world_example.rst
        gh_sess = OAuth2Session(
            cfg['github']['client_id'],
            token=flask.session['auth']['github_token'])
        r = gh_sess.get('https://api.github.com/user')
        print(r.content)
        flask.session['auth'].update({
            'github_id': r.json()['id'],
            'github_login': r.json()['login'],
            'email': r.json().get('email'),
        })
        return flask.redirect('/')
    except Exception as e:
        print(e)
        flask.session['auth'] = None
        raise e


@app.route('/add-suggestion', methods=['POST'])
def add_suggestion():
    '''
    Vložení návrhu (suggestion).
    Redirectuje zpět na index.
    '''
    title = flask.request.form['suggestion']
    github_id = get_session_github_id()
    if not github_id:
        flask.abort(403) # Forbidden
    conn = get_conn()
    insert_suggestion(conn, title, github_id)
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
    github_id = get_session_github_id()
    if not github_id:
        flask.abort(403) # Forbidden
    conn = get_conn()
    if action == 'upvote':
        vote_value = 1
    elif action == 'downvote':
        vote_value = -1
    elif action == 'reset':
        vote_value = 0
    else:
        raise Exception('Unknown action {!r}'.format(action))
    save_vote(conn, sug_id, github_id, vote_value)
    return flask.redirect('/')


def get_conn():
    db_path = cfg['sqlite_db']
    try:
        return sqlite3.connect(db_path)
    except Exception as e:
        raise Exception('Failed to open db {r}: {!r}'.format(db_path, e)) from e


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
            email TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY,
            suggestion_id TEXT,
            date DATE,
            email TEXT,
            value INTEGER
        )
    ''')


def insert_suggestion(conn, title, github_id, date=None):
    if not title:
        # prázdný návrh přidávat nechceme
        return
    date = date or datetime.utcnow()
    c = conn.cursor()
    c.execute(
        "SELECT 1 FROM suggestions WHERE title = ?", (title, ))
    if c.fetchall():
        # pokud to něco vrátilo, tak návrh s tímto title již v DB existuje
        return
    c.execute(
        "INSERT INTO suggestions (title, date, email) VALUES (?, ?, ?)",
        (title, date.isoformat(), github_id))
    conn.commit()


def save_vote(conn, suggestion_id, github_id, vote_value, date=None):
    '''
    Vloží vote pro nějakou suggestion do DB.
    '''
    if not github_id:
        return
    date = date or datetime.utcnow()
    c = conn.cursor()
    # https://www.sqlite.org/lang_insert.html
    c.execute(
        "DELETE FROM votes WHERE suggestion_id = ? AND email = ?",
        (int(suggestion_id), github_id))
    if vote_value:
        c.execute(
            "INSERT INTO votes (suggestion_id, date, email, value) "
            "VALUES (?, ?, ?, ?)", (
                int(suggestion_id),
                date.isoformat(),
                github_id,
                vote_value,
            ))
    conn.commit()


def list_suggestions(conn, github_id):
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
            COALESCE(SUM(votes.value), 0) AS vote_count,
            COALESCE(SUM(my_votes.value), 0) AS my_vote
        FROM suggestions
        LEFT JOIN votes ON (votes.suggestion_id = suggestions.id)
        LEFT JOIN votes my_votes ON (my_votes.suggestion_id = suggestions.id AND my_votes.email = ?)
        GROUP BY suggestions.id
        ORDER BY vote_count DESC
    ''', (github_id, ))
    suggestions = []
    for row in c:
        suggestions.append({
            'id': row[0],
            'title': row[1],
            'vote_count': row[2],
            'my_vote': row[3] if github_id else 0,
        })
    return suggestions


if __name__ == '__main__':
    app.run(debug=True)
