import cgi
import urllib2
import webapp2
import re

from urlparse import urlparse

from google.appengine.ext import db
from google.appengine.api import users

from dropbox import client, rest, session

APP_KEY = 'nskj5878rk0xdl1'
APP_SECRET = '512gnvtpyfbu5h0'
ACCESS_TYPE = 'app_folder'  # should be 'dropbox' or 'app_folder' as configured for your app

TOKEN_STORE = {}

def get_session():
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
  

class UserToken(db.Model):
  user = db.UserProperty(required=True)
  access_token_key = db.StringProperty()
  access_token_secret = db.StringProperty()

class IndexHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect('http://jeffjia.github.com/Send2Cloud/')
    return

class ConnectHandler(webapp2.RequestHandler):
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
      sess = get_session()
      request_token = sess.obtain_request_token()
      TOKEN_STORE[request_token.key] = request_token
      callback = "http://%s/connect-res" % (self.request.host)
      self.redirect(sess.build_authorize_url(request_token,
        oauth_callback=callback))
    else:
      self.response.write('You are already connected!')

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
      self.response.write('<a href=\'connect\'>Connect</a>')
      return

    access_token_key = user_token.access_token_key
    access_token_secret = user_token.access_token_secret

    url = self.request.get('url')
    link = urllib2.urlopen(url)
    file_name = get_file_name(link)
    db_client = get_client(access_token_key, access_token_secret)
    try:
      result = db_client.put_file('/' + file_name, link)
    except rest.ErrorResponse:
      db.delete(user_token)
      self.response.write('<a href=\'connect\'>You need to reconnect</a>')
      return

    dest_path = result['path']

    self.response.out.write('<html><body>Link: ')
    self.response.out.write(cgi.escape(self.request.get('url')))
    self.response.out.write(dest_path)
    self.response.out.write('</body></html>')

class ErrorHandler(webapp2.RequestHandler):
  def get(self):
    self.response.write("Page does not exist!")

app = webapp2.WSGIApplication([('/', IndexHandler),
                               ('/connect', ConnectHandler),
                               ('/connect-res', CallbackHandler),
                               ('/login', LoginHandler),
                               ('/send', SendHandler),
                               ('/.*', ErrorHandler)],
                              debug = True)
