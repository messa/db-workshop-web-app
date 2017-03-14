import anketa

# BTW: http://flask.pocoo.org/docs/0.12/testing/


def test_render_index():
    tc = anketa.app.test_client()
    rv = tc.get('/')
    assert b'Anketa' in rv.data
