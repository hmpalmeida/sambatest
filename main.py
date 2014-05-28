import cgi
import urllib
import urllib2
import os
import json

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

ZENCODER_KEY = '93d453aa7de28c6645a88b5df3dd59a1'

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
     

#####################################################
# Main class that will work on all requests
######################################################

class MainPage(webapp2.RequestHandler):

     def get(self):
          # TESTING ONLY
          #queries = Video.query()
          #for q in queries:
          #     print q
          # END TESTING
          video_url = self.request.get('url', DEFAULT_VIDEO).strip()
          video_name = self.request.get('name', DEFAULT_VIDEO).strip()
          if (video_url == DEFAULT_VIDEO):
               # If the default video isn't yet on the Store,
               # than store it
               tmp = video_name.rpartition('/')
               video_name = tmp[2]
               video_query = Video.query(Video.url == video_url)
               if (video_query.count() == 0):
                    v = Video(parent=video_key())
                    v.url = video_url
                    v.name = video_name
                    v.put()
          # Prepare template parameters
          template_values = {
               'file': SERVER_NAME+video_name,
          }
          # Call the template
          template = JINJA_ENVIRONMENT.get_template('index.html')
          self.response.write(template.render(template_values))

     def post(self):
          v = Video(parent=video_key())
          v.url = self.request.get('video_url').strip()
          # Get the video name from the url
          tmp = v.url.rpartition('/')
          v.name = tmp[2]
          # Create name for output file
          tmp = v.name.rpartition('.')
          v.name = tmp[0]+'.mp4'
          # Check if this file was already processed
          video_query = Video.query(Video.url == v.url)
          if (video_query.count() == 0):
               # Convert new video to a suitable format
               zenc_input = {'input' : v.url, \
                    'output' : {'url': 's3://sambatest/'+v.name, \
                    'public': 'true'} } 
               enc_input = json.dumps(zenc_input)
               header = {'Zencoder-Api-Key': ZENCODER_KEY, \
                    'Content-Type': 'application/json'}
               req = urllib2.Request('https://app.zencoder.com/api/v2/jobs', \
                    enc_input, header)
               try:
                    f = urllib2.urlopen(req)
               except urllib2.HTTPError as e:
                    err = json.loads(e.read())
                    query_params = {'error': e.code , \
                         'message': err['errors'][0]}
                    self.redirect('/error?' + urllib.urlencode(query_params))
               # Testing response from Zencoder
               response = json.loads(f.read())
               job_id = response['id']
               if (not response['test']):
                    # Job denied by Zencoder
                    #TODO Get error codes instead of those parameters
                    query_params = {'name': v.name , 'url': v.url }
                    self.redirect('/error?' + urllib.urlencode(query_params))
               else:
                    # TODO Wait and check if the encoding is ready before
                    # loading page
                    req = urllib2.Request('https://app.zencoder.com/api/v2/jobs/'+job_id+'.json?api_key='+ZENCODER_KEY)
                    f = urllib2.urlopen(req)
                    status = json.loads(f.read())
                    # Possible states are: pending, waiting, processing, 
                    # finished, failed, and cancelled
                    if (status['job']['state'] == 'finished'):
                         # Everything went ok, add info to the store
                         v.put()
          # Redirect to the "/" get path to open the desired file
          query_params = {'name': v.name , 'url': v.url }
          self.redirect('/?' + urllib.urlencode(query_params))

#####################################################
# Error handler
######################################################

class ErrorPage(webapp2.RequestHandler):

     def get(self):
          print 'Future Error Page!'

#####################################################
# Request handler
######################################################

application = webapp2.WSGIApplication([
     ('/', MainPage),
     ('/add', MainPage),
     ('/error', ErrorPage),
], debug=True)
