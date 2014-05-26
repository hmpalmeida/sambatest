import cgi
import urllib
import os

from google.appengine.ext import ndb

import webapp2
import jinja2

######################################################
# "Constant" Definitions
######################################################

JINJA_ENVIRONMENT = jinja2.Environment(
     loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
     extensions=['jinja2.ext.autoescape'],
     autoescape=True)

SERVER_NAME = 'http://d357rxfqtl15q4.cloudfront.net/'

#DEFAULT_VIDEO = 'dramatic.mp4'
DEFAULT_VIDEO = 'file:///home/helio/Videos/dramatic.mp4'

DEFAULT_STORE = 'videolist'

#####################################################
# Classes and definitions for the ndb store
######################################################

def video_key():
     """Constructs a Datastore key for a Videos entity within DEFAULT_STORE."""
     return ndb.Key('Videos', DEFAULT_STORE)

class Video(ndb.Model):
     """Stores information on a video."""
     url = ndb.StringProperty()
     name = ndb.StringProperty(indexed=False)
     date = ndb.DateTimeProperty(auto_now_add=True)
     
     #@classmethod
     #def query_url(cls, ancestor_key):
     #     return cls.query(ancestor=ancestor_key).order(-cls.date)
     

#####################################################
# Main class that will work on all requests
######################################################

class MainPage(webapp2.RequestHandler):

     def get(self):
          video_url = self.request.get('video_name', DEFAULT_VIDEO).strip()
          tmp = video_url.rpartition('/')
          video_name = tmp[2]
          if (video_url == DEFAULT_VIDEO):
               # If the default video isn't yet on the Store,
               # than store it
               video_query = Video.query(Video.url == video_url)
               if (video_query.count() == 0):
                    v = Video(parent=video_key())
                    v.url = video_url
                    v.name = video_name
                    v.put()
          
          template_values = {
               #'server': SERVER_NAME,
               'file': SERVER_NAME+video_name,
          }

          template = JINJA_ENVIRONMENT.get_template('index.html')
          self.response.write(template.render(template_values))

     def post(self):
          new_video = self.request.get('video_url').strip()
          # Check if this file was already processed
          video_query = Video.query(Video.url == new_video)
          #video_query = Video.query(ancestor=video_key()).order(-Greeting.date)
          if (video_query.count() == 0):
               # TODO Convert new video to a suitable format
               # Add the new video to the store
               v = Video(parent=video_key())
               v.url = new_video
               # Get the video name from the url
               tmp = v.url.rpartition('/')
               v.name = tmp[2]
               v.put()
          #else:
          # Redirect to the "/" get path to open the desired file
          query_params = {'video_name': new_video}
          self.redirect('/?' + urllib.urlencode(query_params))

#####################################################
# Request handler
######################################################

application = webapp2.WSGIApplication([
     ('/', MainPage),
     ('/add', MainPage),
], debug=True)
