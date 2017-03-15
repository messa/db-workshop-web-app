from datetime import datetime
import flask
import sqlite3
import sqlalchemy

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


from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String

Base = declarative_base()


class Suggestion (Base):

    __tablename__ = 'suggestions'

    id = Column(Integer, primary_key=True)
    title = Column(String)
    date = Column(String)


class Vote (Base):
    __tablename__ = 'votes'

    id = Column(Integer, primary_key=True)
    suggestion_id = Column(Integer)
    date = Column(String)
    value = Column(Integer)


def get_conn():
    from sqlalchemy.orm import sessionmaker
    engine = sqlalchemy.create_engine('sqlite:///aneta.db', echo=True)
    Session = sessionmaker(bind=engine)
    session = Session()
    return session


def prepare_schema(session):
    '''
    Vytvoření tabulek, se kterými tato aplikace pracuje.
    Pokud tabulky už existují, tak se nic neděje.
    '''
    engine = session.get_bind()
    Base.metadata.create_all(engine)


def insert_suggestion(session, title, cookie, date=None):
    date = date or datetime.utcnow()
    sug = Suggestion(
        title=title,
        date=date)
    session.add(sug)
    session.commit()
    return sug.id


def insert_vote(session, suggestion_id, cookie, upvote, date=None):
    '''
    Vloží vote pro nějakou suggestion do DB.
    '''
    date = date or datetime.utcnow()
    vote = Vote(
        suggestion_id=int(suggestion_id),
        date=date.isoformat(),
        value=1 if upvote else -1)
    session.add(vote)
    session.commit()


def list_suggestions(session):
    '''
    Vrátí seznam suggestions z DB.
    Návratovou hodnotou je list dictů.
    '''
    from sqlalchemy.sql import func
    items = (session
        .query(
            Suggestion,
            func.sum(Vote.value))
        .outerjoin(Vote, Vote.suggestion_id == Suggestion.id)
        .group_by(Suggestion.id)
        .all())
    suggestions = []
    for suggestion, vote_count in items:
        suggestions.append({
            'id': suggestion.id,
            'title': suggestion.title,
            'vote_count': vote_count or 0,
        })
    return suggestions


if __name__ == '__main__':
    app.run(debug=True)
