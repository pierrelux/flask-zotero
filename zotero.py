# coding: utf-8

from flask import Flask
from flask import g, session, request, url_for, flash
from flask import redirect, render_template
from flask_oauthlib.client import OAuth
import feedparser


app = Flask(__name__)
app.debug = True
app.secret_key = 'development'

# Hack from pyzotero
def ib64_patched(self, attrsD, contentparams):
    """ Patch isBase64 to prevent Base64 encoding of JSON content
    """
    if attrsD.get('mode', '') == 'base64':
        return 0
    if self.contentparams['type'].startswith('text/'):
        return 0
    if self.contentparams['type'].endswith('+xml'):
        return 0
    if self.contentparams['type'].endswith('/xml'):
        return 0
    if self.contentparams['type'].endswith('/json'):
        return 0
    return 0
feedparser._FeedParserMixin._isBase64 = ib64_patched

oauth = OAuth(app)

zotero = oauth.remote_app(
    'zotero',
    consumer_key='consumerkey',
    consumer_secret='secretkey',
    base_url='https://api.zotero.org',
    request_token_url='https://www.zotero.org/oauth/request',
    access_token_url='https://www.zotero.org/oauth/access',
    authorize_url='https://www.zotero.org/oauth/authorize'
)


@zotero.tokengetter
def get_zotero_token():
    if 'zotero_oauth' in session:
        resp = session['zotero_oauth']
        return resp['oauth_token'], resp['oauth_token_secret']


@app.before_request
def before_request():
    g.user = None
    if 'zotero_oauth' in session:
        g.user = session['zotero_oauth']

@app.route('/')
def index():
    titles = None
    if g.user is not None:
        resp = zotero.get('users/'+g.user['userID']+'/items?q=delay&format=atom&content=json&key='+g.user['oauth_token_secret'])
        if resp.status == 200:
            feed = resp.data
            d = feedparser.parse(resp.data)
            titles = [entry.title for entry in d.entries]
        else:
            flash('Unable to load tweets from zotero.')
    return render_template('index.html', titles=titles)

@app.route('/login')
def login():
    callback_url = url_for('oauthorized', next=request.args.get('next'))
    return zotero.authorize(callback=callback_url or request.referrer or None)


@app.route('/logout')
def logout():
    session.pop('zotero_oauth', None)
    return redirect(url_for('index'))


@app.route('/oauthorized')
@zotero.authorized_handler
def oauthorized(resp):
    if resp is None:
        flash('You denied the request to sign in.')
    else:
        session['zotero_oauth'] = resp
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run()
