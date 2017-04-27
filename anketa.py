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

app.secret_key = cfg['secret_key']


@app.route('/')
def index():
    '''
    Titulní strana webovky
    '''
    conn = get_conn()
    prepare_schema(conn)
    return flask.render_template('index.html',
        email=get_session_email(),
        suggestions=list_suggestions(conn))


def get_session_email():
    if flask.session.get('auth'):
        return flask.session['auth'].get('email')
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
        flask.session['auth']['email'] = r.json()['email']
        return flask.redirect('/')
    except Exception as e:
        flask.session['auth'] = None
        raise e


@app.route('/add-suggestion', methods=['POST'])
def add_suggestion():
    '''
    Vložení návrhu (suggestion).
    Redirectuje zpět na index.
    '''
    title = flask.request.form['suggestion']
    email = get_session_email()
    if not email:
        flask.abort(403) # Forbidden
    conn = get_conn()
    insert_suggestion(conn, title, email)
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
    email = get_session_email()
    if not email:
        flask.abort(403) # Forbidden
    conn = get_conn()
    if action == 'upvote':
        is_upvote = True
    elif action == 'downvote':
        is_upvote = False
    else:
        raise Exception('Unknown action {!r}'.format(action))
    insert_vote(conn, sug_id, email, is_upvote)
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


def insert_suggestion(conn, title, email, date=None):
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
        (title, date.isoformat(), email))
    conn.commit()


def insert_vote(conn, suggestion_id, email, upvote, date=None):
    '''
    Vloží vote pro nějakou suggestion do DB.
    '''
    date = date or datetime.utcnow()
    c = conn.cursor()
    # https://www.sqlite.org/lang_insert.html
    c.execute(
        "DELETE FROM votes WHERE suggestion_id = ? AND email = ?",
        (int(suggestion_id), email))
    c.execute(
        "INSERT INTO votes (suggestion_id, date, email, value) "
        "VALUES (?, ?, ?, ?)", (
            int(suggestion_id),
            date.isoformat(),
            email,
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
