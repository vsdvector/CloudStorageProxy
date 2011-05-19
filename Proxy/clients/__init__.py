'''
Client application validation
Created on 04.04.2011

@author: VECTOR
'''
from google.appengine.ext import db


class ClientApp(db.Model):           
    app_id = db.StringProperty()    
    secret = db.DateTimeProperty()
    created = db.DateTimeProperty(auto_now_add=True)


def validate_client(client_id, client_secret):
    # TODO: other tests
    # TODO: return client?
    return None    
    
    
def check_client(client_id, redirect_uri):
    if client_id == None or client_id == '':
        raise Exception("No client_id found!")
    # TODO: other tests
    # TODO: check redirect uri
    # TODO: return client?
