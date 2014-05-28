import cgi
import urllib
import urllib2
import os
import json
import time

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
# Helper functions to create Zencoder requests
#####################################################

def create_zencoder_job_request(input_url, output_file):
     zenc_input = {'input' : input_url, 
          'output' : {'url': 's3://sambatest/'+output_file, 
          'public': 'true'} } 
     enc_input = json.dumps(zenc_input)
     header = {'Zencoder-Api-Key': ZENCODER_KEY, 
          'Content-Type': 'application/json'}
     req = urllib2.Request('https://app.zencoder.com/api/v2/jobs', 
          enc_input, header)
     return req

#####################################################
# Main class that will work on all requests
######################################################

class MainPage(webapp2.RequestHandler):
     
     def get_zencoder_job_status(self, job_id):
          request = urllib2.Request('https://app.zencoder.com/api/v2/jobs/'+job_id+'.json?api_key='+ZENCODER_KEY)
          try:
               f = urllib2.urlopen(request)
          except urllib2.HTTPError as e:
               # Raise an error
               query_params = {'error': e.code , 
                    'message': e}
               self.redirect('/error?' + urllib.urlencode(query_params))
               return
          status = json.loads(f.read())
          # Possible states are: pending, waiting, processing, 
          # finished, failed, and cancelled
          if (status['job']['state'] == 'failed' or 
               status['job']['state'] == 'cancelled'):
               # Raise an error
               query_params = {}
               # Get Error Class
               if ('error_class' in status['job']):
                    query_params['error'] = status['job']['error_class']
               elif ('error_class' in status['job']['input_media_file']):
                    query_params['error'] = status['job']['input_media_file']['error_class']
               else:
                    query_params['error'] = '?'
               # Get Error Message
               if ('error_message' in status['job']):
                    query_params['message'] = status['job']['error_message']
               elif ('error_message' in status['job']['input_media_file']):
                    query_params['message'] = status['job']['input_media_file']['error_message']
               else:
                    query_params['message'] = '?'
               self.redirect('/error?' + urllib.urlencode(query_params))
          else:
               # Any other case, simply return it
               return status['job']['state']


     def get(self):
          video_url = self.request.get('url', DEFAULT_VIDEO).strip()
          video_name = self.request.get('name', DEFAULT_VIDEO).strip()
          job_id = self.request.get('jobid', '-1').strip()
          status = '????'
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
          # In case an encoding job is running...
          if (job_id != '-1'):
               status = self.get_zencoder_job_status(job_id)
               template_values['status'] = status
          # Call the template
          template = JINJA_ENVIRONMENT.get_template('index.html')
          self.response.write(template.render(template_values))
     
     ###################

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
          #FIXME this checking is useless at the moment!
          if (video_query.count() >= 0):
               # Convert new video to a suitable format
               req = create_zencoder_job_request(v.url, v.name)
               try:
                    f = urllib2.urlopen(req)
               except urllib2.HTTPError as e:
                    query_params = {'error': e.code , 
                         'message': e}
                    self.redirect('/error?' + urllib.urlencode(query_params))
                    return
               # Request submitted, now control job status
               response = json.loads(f.read())
               query_params = {'name': v.name , 'url': v.url,
                     'jobid': str(response['id']) }
               self.redirect('/?' + urllib.urlencode(query_params))
               return
          # Redirect to the "/" get path to open the desired file
          query_params = {'name': v.name , 'url': v.url }
          self.redirect('/?' + urllib.urlencode(query_params))

#####################################################
# Error handler
######################################################

class ErrorPage(webapp2.RequestHandler):

     def get(self):
          print 'Future Error Page!'
          error_code = self.request.get('error').strip()
          error_message = self.request.get('message').strip()
          template_values = {
               'error': error_code,
               'message': error_message
          }
          # Call the template
          template = JINJA_ENVIRONMENT.get_template('error.html')
          self.response.write(template.render(template_values))
          


#####################################################
# Request handler
######################################################

application = webapp2.WSGIApplication([
     ('/', MainPage),
     ('/add', MainPage),
     ('/error', ErrorPage),
], debug=True)
