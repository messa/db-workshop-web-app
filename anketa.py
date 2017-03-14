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


if __name__ == '__main__':
    app.run(debug=True)
