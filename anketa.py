import flask


app = flask.Flask(__name__)


@app.route('/')
def index():
    suggestions = [
        {
            "title": "Tvorba webu",
            "vote_count": 8,
        }, {
            "title": "Statistika",
            "vote_count": 5,
        }, {
            "title": "Lineární algebra",
            "vote_count": 3,
        },
    ]
    return flask.render_template('index.html', suggestions=suggestions)


@app.route('/add-suggestion', methods=['POST'])
def add_suggestion():
    suggestion = flask.request.form['suggestion']
    return flask.redirect('/')


@app.route('/vote', methods=['POST'])
def vote():
    return flask.redirect('/')


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


if __name__ == '__main__':
    app.run(debug=True)
