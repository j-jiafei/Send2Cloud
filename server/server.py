import cgi
import urllib2
import webapp2
import re

from urlparse import urlparse

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import taskqueue

from dropbox import client, rest, session

APP_KEY = ''
APP_SECRET = ''
ACCESS_TYPE = 'app_folder'  # should be 'dropbox' or 'app_folder' as configured for your app

APP_STATUS = 0 # 0 for dev, 1 for production

TOKEN_STORE = {}

def check_key_secret():
  if APP_KEY == '' or APP_SECRET == '':
    global APP_KEY
    global APP_SECRET
    key_secret_query = db.GqlQuery('SELECT * '
                                   'FROM KeySecret '
                                   'WHERE status = :1', APP_STATUS)
    key_secret = key_secret_query.get()
    APP_KEY = key_secret.app_key
    APP_SECRET = key_secret.app_secret

def get_session():
  check_key_secret()
  return session.DropboxSession(APP_KEY, APP_SECRET, ACCESS_TYPE)

def get_client(access_token_key, access_token_secret):
  sess = get_session()
  sess.set_token(access_token_key, access_token_secret)
  return client.DropboxClient(sess)

def get_file_name(link):
  headers = link.info().headers
  for header in headers:
    m = re.match('^filename=(.*)$', header)
    if m:
      return m.group(1)
  url = link.url
  return url.split('/')[-1]

class KeySecret(db.Model):
  status = db.IntegerProperty(required=True)
  app_key = db.StringProperty()
  app_secret = db.StringProperty()

class UserToken(db.Model):
  user = db.UserProperty(required=True)
  access_token_key = db.StringProperty()
  access_token_secret = db.StringProperty()

class IndexHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect('http://jeffjia.github.com/Send2Cloud/')
    return

class TryHandler(webapp2.RequestHandler):
  def get(self):
    self.response.write('Hello');
    return

class ConnectHandler(webapp2.RequestHandler):
  def get(self):
    user = users.get_current_user()
    if not user:
      self.redirect(users.create_login_url(self.request.uri))
      return

    origin = self.request.get('origin')
    user_token_query = db.GqlQuery("SELECT * "
                                   "FROM UserToken "
                                   "WHERE user = :1", user);
    user_token = user_token_query.get()
    if not user_token:
      sess = get_session()
      request_token = sess.obtain_request_token()
      TOKEN_STORE[request_token.key] = request_token
      callback = "http://%s/connect-res" % (self.request.host)
      if origin:
        callback = callback + '?origin=%s' % (origin)
      self.redirect(sess.build_authorize_url(request_token,
        oauth_callback=callback))
    else:
      self.response.write('You are already connected!')
      if origin:
        self.response.write('<a href="%s">Back</a>' % (origin));

    return

class CallbackHandler(webapp2.RequestHandler):
  def get(self):
    user = users.get_current_user()

    if not user:
      self.redirect(users.create_login_url(self.request.uri))
      return

    not_approved = bool(self.request.get('not_approved'))
    
    if not_approved:
      self.response.write('The connection to Dropbox request is not'
      'successful.')
      return

    request_token_key = self.request.get("oauth_token")
    if not request_token_key:
      self.response.write('The connection to Dropbox request is not'
      'successful.')
      return

    else:
      sess = get_session()

      request_token = TOKEN_STORE[request_token_key]
      access_token = sess.obtain_access_token(request_token)

      if not access_token:
        self.response.write('The connection to Dropbox request is not'
        'successful.')
        return
      else:
        TOKEN_STORE[access_token.key] = access_token

        user_token = UserToken(user = user)
        user_token.access_token_key = access_token.key
        user_token.access_token_secret = access_token.secret
        user_token.put()
        self.response.write('You are connected successfully!')
        origin = self.request.get('origin')
        if origin:
          self.response.write('<a href="%s">Back</a>' % (origin));

        return

class LoginHandler(webapp2.RequestHandler):
  def get(self):
    a = 0

class SendHandler(webapp2.RequestHandler):
  def get(self):
    user = users.get_current_user()

    if not user:
      self.redirect(users.create_login_url(self.request.uri))
      return

    user_token_query = db.GqlQuery("SELECT * "
                                   "FROM UserToken "
                                   "WHERE user = :1", user);
    user_token = user_token_query.get()
    if not user_token:
      self.response.write('<a href=\'connect?origin=%s\'>Connect</a>' % (self.request.uri))
      return

    access_token_key = user_token.access_token_key
    access_token_secret = user_token.access_token_secret
    url = self.request.get('u')

    taskqueue.add(url='/work', params={'u': url, 'access_token_key': access_token_key, 'access_token_secret': access_token_secret})

    self.response.out.write('<html><body>The file is sent')
    self.response.out.write('</body></html>')

class Worker(webapp2.RequestHandler):
  def post(self):
    access_token_key = self.request.get('access_token_key')
    access_token_secret = self.request.get('access_token_secret')
    url = self.request.get('u')
    link = urllib2.urlopen(url)
    file_name = get_file_name(link)
    db_client = get_client(access_token_key, access_token_secret)
    try:
      result = db_client.put_file('/' + file_name, link)
    except rest.ErrorResponse:
      db.delete(user_token)
      return
    

class ErrorHandler(webapp2.RequestHandler):
  def get(self):
    self.response.write("Page does not exist!")

class SetKeySecretHandler(webapp2.RequestHandler):
  def get(self):
    status = APP_STATUS
    app_key = self.request.get('APP_KEY')
    app_secret = self.request.get('APP_SECRET')
    key_secret = KeySecret(status = status)
    key_secret.app_key = app_key
    key_secret.app_secret = app_secret
    key_secret.put()
    self.response.out.write('Key Secret Stored')
    

app = webapp2.WSGIApplication([('/', IndexHandler),
                               ('/try', TryHandler),
                               ('/connect', ConnectHandler),
                               ('/connect-res', CallbackHandler),
                               ('/login', LoginHandler),
                               ('/send', SendHandler),
                               ('/work', Worker),
                               ('/set_key_secret', SetKeySecretHandler),
                               ('/.*', ErrorHandler)],
                              debug = True)
