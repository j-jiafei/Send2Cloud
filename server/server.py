import cgi
import urllib2
import webapp2
import re
import jinja2
import os

from urlparse import urlparse

from google.appengine.ext import db
from google.appengine.api import users
from google.appengine.api import taskqueue

from dropbox import client, rest, session

APP_KEY = ''
APP_SECRET = ''
ACCESS_TYPE = 'app_folder'  # should be 'dropbox' or 'app_folder' as configured for your app

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

class AppToken(db.Model):
  app_key = db.StringProperty()
  app_secret = db.StringProperty()

class UserToken(db.Model):
  user = db.UserProperty(required=True)
  uid = db.StringProperty(required=True)
  access_token_key = db.StringProperty()
  access_token_secret = db.StringProperty()

class RequestToken(db.Model):
  request_key = db.StringProperty(required=True)
  request_secret = db.StringProperty(required=True)

def check_key_secret():
  if APP_KEY == '' or APP_SECRET == '':
    global APP_KEY
    global APP_SECRET
    app_token_query = db.GqlQuery('SELECT * '
                                   'FROM AppToken ')
    app_token = app_token_query.get()
    APP_KEY = app_token.app_key
    APP_SECRET = app_token.app_secret

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
  if url.endswith('/'):
    return url.split('/')[-2]
  else:
    return url.split('/')[-1]

class IndexHandler(webapp2.RequestHandler):
  def get(self):
    self.redirect('http://jeffjia.github.com/Send2Cloud/')
    return

class ConnectHandler(webapp2.RequestHandler):
  def display_connected_page(self, user):
    """
    Call this function to display the page when the user account is already connected
    """
    self.response.out.write(
      jinja_environment.get_template('connected.html').render( {
        'user': user.nickname()
      }))

  def get(self):
    user = users.get_current_user()
    if not user:
      self.redirect(users.create_login_url(self.request.uri))
      return

    user_token_query = db.GqlQuery("SELECT * "
                                   "FROM UserToken "
                                   "WHERE user = :1", user);
    user_token = user_token_query.get()

    from_bkl = self.request.get('from_bkl')
    from_bkl = False if not from_bkl or not bool(from_bkl) else True

    sess = get_session()
    request_token = sess.obtain_request_token()
    callback = "http://%s/connect-res?from_bkl=%s" % (self.request.host, from_bkl)
    request_token_value = RequestToken(request_key = request_token.key, 
      request_secret = request_token.secret);

    if not user_token:
      request_token_value.put()
      self.redirect(sess.build_authorize_url(request_token,
        oauth_callback=callback))
      return

    try:
      db_client = get_client(user_token.access_token_key, user_token.access_token_secret)
      info = db_client.account_info()
    except rest.ErrorResponse:
      request_token_value.put()
      self.redirect(sess.build_authorize_url(request_token,
        oauth_callback=callback))
      return

    self.display_connected_page(user)
    return

class CallbackHandler(webapp2.RequestHandler):
  def display_succ_page(self):
    """
    Display page when connection is successful
    """
    from_bkl = self.request.get('from_bkl')
    from_bkl = False if not from_bkl or not bool(from_bkl) else True
    if from_bkl:
      self.response.write("""
        <body>
          <script>
            (function() {
              window.opener.location.reload(true);
              window.close();
            })();
          </script>
        </body>
      """);
    else:
      self.response.out.write(
        jinja_environment.get_template('callback.html').render( {
          'succ': True,
          'url': users.create_logout_url(self.request.uri),
          'url_linktext': 'Sign Out',
        }))

  def display_fail_page(self):
    """
    Display page when connection fails
    """
    from_bkl = self.request.get('from_bkl')
    from_bkl = False if not from_bkl or not bool(from_bkl) else True
    self.response.out.write(
      jinja_environment.get_template('callback.html').render( {
        'succ': False,
        'url': users.create_logout_url(self.request.uri),
        'connect_url': '/connect?from_bkl=%s' % (from_bkl),
        'url_linktext': 'Sign Out',
      }))

  def get(self):
    user = users.get_current_user()

    if not user:
      self.redirect(users.create_login_url(self.request.uri))
      return

    not_approved = bool(self.request.get('not_approved'))
    
    if not_approved:
      self.display_fail_page()
      return

    uid = self.request.get('uid')
    oauth_key = self.request.get('oauth_token')
    
    request_token_query = db.GqlQuery('SELECT * '
                                   'FROM RequestToken '
                                   'WHERE request_key = :1', oauth_key);
    request_token_value = request_token_query.get()

    if not request_token_value:
      self.display_fail_page()
      return

    sess = get_session()
    sess.set_request_token(request_token_value.request_key,
      request_token_value.request_secret)
    access_token = sess.obtain_access_token()
    db.delete(request_token_value);

    if not access_token:
      self.display_fail_page()
      return

    user_token = UserToken(user = user, uid = uid)
    user_token.access_token_key = access_token.key
    user_token.access_token_secret = access_token.secret
    user_token.put()
    self.display_succ_page()

    return

class MainHandler(webapp2.RequestHandler):
  """ 
    The handler to deal with /send request
    First, it will check whether the user has logged in. If not, login.html is used as a template to ask the user to login
    Then, once the user has logged in, it will check whether use needs to connect to dropbox. If so, login.html is used again
    If the first two steps are passed, the file is sent, and the succ.html is displayed to users
  """
  def display_connect_page(self, user, connect_linktext):
    """
    When user account is not connected to Dropbox, or key/secret for user account is invalid,
    the function is called to display the reconnect page
    """
    sess = get_session()
    request_token = sess.obtain_request_token()
    request_token_value = RequestToken(request_key = request_token.key,
        request_secret = request_token.secret)
    request_token_value.put()
    self.response.out.write(
      jinja_environment.get_template('login.html').render( {
        'user': user.nickname(),
        'need_to_connect': True,
        'connect_url': '/connect?from_bkl=True',
        'connect_linktext': connect_linktext,
        'need_to_login': False,
        'logout_url': users.create_logout_url(self.request.uri),
      }))

  def get(self):
    user = users.get_current_user()

    if not user:
      self.response.out.write(
        jinja_environment.get_template('login.html').render( {
          'need_to_connect': False,
          'need_to_login': True,
          'login_url': users.create_login_url('/login-succ'),
        }))
      return

    user_token_query = db.GqlQuery("SELECT * "
                                   "FROM UserToken "
                                   "WHERE user = :1", user);
    user_token = user_token_query.get()
    if not user_token:
      self.display_connect_page(user, "Connect to Dropbox")
      return

    access_token_key = user_token.access_token_key
    access_token_secret = user_token.access_token_secret

    try:
      db_client = get_client(access_token_key, access_token_secret)
      info = db_client.account_info()
    except rest.ErrorResponse:
      db.delete(user_token)
      self.display_connect_page(user, "Reconnect to Dropbox")
      return

    url = self.request.get('u')
    link = urllib2.urlopen(url)
    file_name = get_file_name(link)

    taskqueue.add(url='/work', params={'u': url, 'access_token_key': access_token_key, 'access_token_secret': access_token_secret})

    self.redirect('/succ?nickname=%s&file_name=%s' % (user.nickname(), file_name))

class SuccHandler(webapp2.RequestHandler):
  """ Called when the file is sent successfully """
  def get(self):
    self.response.out.write(
      jinja_environment.get_template('succ.html').render( {
        'user': self.request.get('nickname'),
        'file_name': self.request.get('file_name'),
      }))

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
      return

class ErrorHandler(webapp2.RequestHandler):
  def get(self):
    self.response.write("Page does not exist!")

class LoginSuccHandler(webapp2.RequestHandler):
  def get(self):
    self.response.write("""
      <body>
        <script>
          (function() {
            window.opener.location.reload(true);
            window.close();
          })();
        </script>
      </body>
    """);
    return

app = webapp2.WSGIApplication([('/', IndexHandler),
                               ('/login-succ', LoginSuccHandler),
                               ('/send', MainHandler),
                               ('/connect', ConnectHandler),
                               ('/connect-res', CallbackHandler),
                               ('/work', Worker),
                               ('/succ', SuccHandler),
                               ('/.*', ErrorHandler)],
                              debug = True)
