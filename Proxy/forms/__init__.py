'''
HTML Forms
Created on 03.04.2011

@author: VECTOR
'''

from google.appengine.api import users
import uuid
import cookies


class Form(object):
    def __init__(self):
        self._title="Form"
        self._content=""
        
    def html(self):
        return """<html> 
                    <head> 
                        <title>"""+self._title+"""</title> 
                    </head> 
                    <body>
                        """ + self.content() + """
                    </body> 
                  </html>"""
                  

class AuthForm(Form):
    def __init__(self):
        Form.__init__(self)
        self._title = "Authorize"
        self._id = str(uuid.uuid4())
    
    def set_auth(self, client_id, redir_url):
        self.client_id =client_id
        self.redir_url =redir_url
        
    def get_request_id(self):
        return self._id
        
    def content(self):                
        c = "<form method=\"POST\">"
        c = c + users.get_current_user().nickname()+" please authorize or deny app: " + self.client_id  
        c = c + "<input type=\"hidden\" name=\"client_id\" value=\""+self.client_id+"\">"
        c = c + "<input type=\"hidden\" name=\"redirect_uri\" value=\""+self.redir_url+"\">"
        c = c + "<input type=\"hidden\" name=\"request_id\" value=\""+self._id+"\">"
        c = c + "<input type=\"checkbox\" name=\"root\" value=\"1\"> Root"
        c = c + "<input type=\"submit\" name=\"allow\" value=\"Allow\">"
        c = c + "<input type=\"submit\" name=\"deny\" value=\"Deny\">"
        c = c + "</form>"
        return c
