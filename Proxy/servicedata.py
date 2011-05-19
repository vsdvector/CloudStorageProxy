'''
Service data(credentials, share links etc)
Created on 10.04.2011

@author: VECTOR
'''
from google.appengine.ext import db
from uuid import uuid4
from  hashlib import sha1 

class ServiceData(db.Model):   
    ''' Class for storing data necessary for using storage service ''' 
    owner = db.StringProperty()
    service = db.StringProperty()
    credentials = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)
        
class ShareLink(db.Model):
    ''' Class for storing public access links '''
    data = db.ReferenceProperty(ServiceData)
    path = db.StringProperty()
    link = db.StringProperty()
    # created? expires?
    
    def regenerate_link(self):
        # if link is empty, generate new
        # otherwise do nothing        
        if self.link == None:
            self.generate_link()
            
        
    def generate_link(self):
        # generate link code
        from time import time
        link = str(uuid4()) + str(time())
        self.link = sha1(link).hexdigest();
        self.put()
        
        