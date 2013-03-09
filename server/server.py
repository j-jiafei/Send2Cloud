import cgi
import urllib2
import webapp2
import re
import jinja2
import os

from urlparse import urlparse

from google.appengine.ext import db
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
  """
  The handler to deal with Dropbox connection request
  """
  def get(self):
    """
    A dropbox connection request is initialized.
    The request key and secret are stored in cookies
    """
    sess = get_session()
    request_token = sess.obtain_request_token()
    self.response.headers.add_header('Set-Cookie', 'request_key=%s' % (request_token.key))
    self.response.headers.add_header('Set-Cookie', 'request_secret=%s' % (request_token.secret))
    callback = "http://%s/connect-res" % (self.request.host)
    self.redirect(sess.build_authorize_url(request_token,
      oauth_callback=callback))
    return


class CallbackHandler(webapp2.RequestHandler):
  """
  The handler to deal with callback request from Dropbox connection
  If the connection is successful, reload the page to send the file
  If failed, show the callback.html
  """
  def _display_succ_page(self):
    """
    Reload page when connection is successful
    """
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

  def _display_fail_page(self):
    """
    Display page when connection fails
    """
    self.response.out.write(
      jinja_environment.get_template('callback.html').render( {
        'succ': False,
        'connect_url': '/connect',
      }))

  def get(self):
    not_approved = bool(self.request.get('not_approved'))
    if not_approved:
      self._display_fail_page()
      return
    uid = self.request.get('uid')
    oauth_key = self.request.get('oauth_token')
    request_key = self.request.cookies.get('request_key')
    request_secret = self.request.cookies.get('request_secret')
    if request_key is None or request_secret is None:
      self._display_fail_page()
      return
    sess = get_session()
    sess.set_request_token(request_key, request_secret)
    access_token = sess.obtain_access_token()
    if not access_token:
      self._display_fail_page()
      return
    self.response.headers.add_header('Set-Cookie', 'access_key=%s' % (access_token.key))
    self.response.headers.add_header('Set-Cookie', 'access_secret=%s' % (access_token.secret))
    self._display_succ_page()
    return


class MainHandler(webapp2.RequestHandler):
  """
    The handler to deal with /send request
    First, it will check whether use needs to connect to dropbox. If so, login.html is used again
    If the first two steps are passed, the file is sent, and the succ.html is displayed to users
  """
  def _display_connect_page(self, connect_linktext):
    """
    When user account is not connected to Dropbox, or key/secret for user account is invalid,
    the function is called to display the reconnect page
    """
    self.response.out.write(
      jinja_environment.get_template('login.html').render( {
        'need_to_connect': True,
        'connect_url': '/connect',
        'connect_linktext': connect_linktext,
      }))

  def get(self):
    """
    First, the server tries reading app_key and app_secret from cookies.
    If successfully, the app_key and app_secret is used to send the file.
    Otherwise, connecting to dropbox is required.
    """
    access_token_key = self.request.cookies.get('access_key')
    access_token_secret = self.request.cookies.get('access_secret')
    if access_token_key is None or access_token_secret is None:
      self._display_connect_page("Connect to Dropbox")
      return
    try:
      db_client = get_client(access_token_key, access_token_secret)
      info = db_client.account_info()
    except rest.ErrorResponse:
      self._display_connect_page("Connect to Dropbox")
      return
    url = self.request.get('u')
    link = urllib2.urlopen(url)
    file_name = get_file_name(link)
    taskqueue.add(url='/work', params={'u': url, 'access_token_key': access_token_key, 'access_token_secret': access_token_secret})
    self.redirect('/succ?file_name=%s' % (file_name))


class SuccHandler(webapp2.RequestHandler):
  """ Called when the file is sent successfully """
  def get(self):
    self.response.out.write(
      jinja_environment.get_template('succ.html').render( {
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


app = webapp2.WSGIApplication([('/', IndexHandler),
                               ('/send', MainHandler),
                               ('/connect', ConnectHandler),
                               ('/connect-res', CallbackHandler),
                               ('/work', Worker),
                               ('/succ', SuccHandler),
                               ('/.*', ErrorHandler)],
                              debug = True)
