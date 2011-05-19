'''
Authorization

'''
# TODO: improve OAuth 2.0 support (use library?)
import forms
import clients
import uuid
import json
from hashlib import sha1
from google.appengine.ext import webapp
from google.appengine.api import users
from google.appengine.ext import db


class UserAuth(db.Model):   
    owner = db.StringProperty()
    client = db.ReferenceProperty(clients.ClientApp)
    sandbox = db.BooleanProperty()
    code = db.StringProperty()
    token = db.StringProperty()    
    created = db.DateTimeProperty(auto_now_add=True)
    
    
class RequestHandler(webapp.RequestHandler):               

    # example way to send an oauth error
    def send_error(self, err=None):
        # send a 401 error
        self.error(401)
        self.response.out.write(str(err.message))            
    
    def send_json_error(self, err=None):
        # send a 400 error
        self.error(400)
        response_obj = {'error': str(err.message)}
        self.response.headers.add_header("Content-Type", "application/json")
        self.response.headers.add_header("Cache-Control", "no-store")                
        json.dump(response_obj, self.response.out)        

    def get(self):

        # debug info
        #print self.command, self.path, self.headers
        
        # get cookies
        cookies = forms.cookies.Cookies(self) 
                    
        # user authorization        
        if self.request.path.endswith("/authorize"):
            try:
                # check client id
                clients.check_client(self.request.get('client_id'), self.request.get('redirect_uri'))
                user = users.get_current_user()
                if user:
                    if self.request.method == 'POST':
                        if self.request.get('request_id') != cookies['request_id']:
                            raise Exception("Invalid request id. Try again.")
                        # user can deny
                        if self.request.get('deny'):
                            if self.request.get('redirect_uri'):
                                redir = self.request.get('redirect_uri')
                                if self.request.get('redirect_uri').find("?") == -1:
                                    redir = redir + "?"
                                else: 
                                    redir = redir + "&"
                                redir = redir + "error=access_denied"
                                self.redirect(redir)
                            else:
                                self.response.out.write("Access denied for app: "+ self.request.get('client_id'))
                            return
                        # everything seems ok, generate authorization code
                        keyname = user.user_id() + "_" + self.request.get('client_id')
                        new_auth = UserAuth.get_or_insert(keyname)
                        # TODO: get ClientApp reference
                        new_auth.client = None
                        new_auth.owner = user.user_id()
                        new_auth.sandbox = False if self.request.get("root") else True
                        new_auth.code = generate_authorization_code();
                        new_auth.put()
                        
                        if self.request.get('redirect_uri'):
                            # redirect
                            redir = self.request.get('redirect_uri')
                            if self.request.get('redirect_uri').find("?") == -1:
                                redir = redir + "?"
                            else: 
                                redir = redir + "&"
                            redir = redir + "authorization_code="+new_auth.code
                            self.redirect(redir)
                        else:                            
                            self.response.out.write("Your authorization code: "+ new_auth.code)                        
                    else:        
                        # bring auth. form            
                        frm = forms.AuthForm()
                        frm.set_auth(self.request.get('client_id'), self.request.get('redirect_url'))
                        cookies['request_id'] = frm.get_request_id() # hidden field againts CSRF                
                        self.response.out.write(frm.html())
                else:
                    url = users.create_login_url(dest_url=self.request.url)
                    self.redirect(url)
            except Exception, err:
                self.send_error(err)
            return

        # access token
        if self.request.path.endswith("/access_token"):
            try:                
                client = clients.validate_client(self.request.get("client_id"), self.request.get("client_secret"))
                auth = UserAuth.gql("WHERE client = :1 AND code = :2", client, self.request.get("code")).get()
                if auth == None:
                    raise Exception("invalid_grant")
                generate_token(auth)
                auth.put()
                response_obj = {'access_token': auth.token, 'token_type' : 'OAuth2'}
                self.response.headers.add_header("Content-Type", "application/json")
                self.response.headers.add_header("Cache-Control", "no-store")                
                json.dump(response_obj, self.response.out)
            except Exception, err:                
                self.send_json_error(err)
            return                

    def post(self):
        self.get()


def generate_authorization_code():
    return str(uuid.uuid4())


def generate_token(auth):    
    auth.token = sha1(str(uuid.uuid4())).hexdigest();
    

def valid_token(request):
    # check if request contains valid token
    token = request.get("oauth_token")
    auth = UserAuth.gql("WHERE token = :1", token).get()
    return auth       