import cgi
import urllib
import os


from google.appengine.api import users
from google.appengine.ext import ndb

import webapp2
import jinja2

JINJA_ENVIRONMENT = jinja2.Environment(
     loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
     extensions=['jinja2.ext.autoescape'],
     autoescape=True)

SERVER_NAME = 'http://d357rxfqtl15q4.cloudfront.net/'

DEFAULT_FILE = 'dramatic.mp4'

class MainPage(webapp2.RequestHandler):

     def get(self):
          template_values = {
               #'server': SERVER_NAME,
               'file': SERVER_NAME+DEFAULT_FILE,
          }

          template = JINJA_ENVIRONMENT.get_template('index.html')
          self.response.write(template.render(template_values))


application = webapp2.WSGIApplication([
     ('/', MainPage),
     #('/add', VideoPlayer),
], debug=True)
