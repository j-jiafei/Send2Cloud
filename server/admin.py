import webapp2
import jinja2
import os

from server import AppToken

jinja_environment = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))

class SetAppTokenHandler(webapp2.RequestHandler):
  def get(self):
    app_key = self.request.get('key')
    app_secret = self.request.get('secret')
    app_token_value = AppToken(app_key = app_key, app_secret = app_secret)
    app_token_value.put()
    self.response.write('App Token Updated');
    return

app = webapp2.WSGIApplication([('/set_app_token', SetAppTokenHandler)],
                              debug = True)
