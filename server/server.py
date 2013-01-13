import cgi
import webapp2
import urllib2

from google.appengine.ext import db

def getFileType(url):
  ""

class LocalFile(db.Model):
  file_name = db.StringProperty(required=True)
  blob = db.BlobProperty()


class Receive(webapp2.RequestHandler):
  def get(self):
    self.response.out.write('<html><body>Link: ')
    self.response.out.write(cgi.escape(self.request.get('url')))
    self.response.out.write('</body></html>')
    url = self.request.get('url')
    link = urllib2.urlopen(url)
    local_file = LocalFile(file_name = 'test_file')
    local_file.blob = link.read()
    local_file.put()

app = webapp2.WSGIApplication([('/receive', Receive)],
                              debug = True)
