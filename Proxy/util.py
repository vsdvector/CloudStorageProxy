'''
    Cloud storage proxy entry point
'''

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from dropbox import auth
from forms import cookies
from oauth import oauth
from django.utils import simplejson as json
import backend.dropbox_backend
from servicedata import ServiceData
from google.appengine.api import users
import atom.url
import gdata.alt.appengine
import gdata.docs.service

class UtilRequestHandler(webapp.RequestHandler):
    
        
    def get(self, command):
        ''' process GET request        
        '''
        # get cookies
        user_cookies = cookies.Cookies(self)
        user = users.get_current_user()
        if user == None:
            url = users.create_login_url(dest_url=self.request.url)
            self.redirect(url)
            return         
        if command == 'dropbox_auth':                        
            # make an authenticator
            dba = auth.Authenticator(backend.dropbox_backend.DropboxBackend.config)
            
            if self.request.get('oauth_token'):
                # get access token            
                token = oauth.OAuthToken.from_string(user_cookies['token'])
                access_token = dba.obtain_access_token(token, '')                        
                keyname = user.user_id() + "_dropbox"
                creds = ServiceData.get_or_insert(keyname)
                creds.owner = user.user_id()
                creds.service = "dropbox"
                creds.credentials = access_token.to_string()
                creds.put()
                self.response.out.write("done!")
            else:
                # grab the request token
                token = dba.obtain_request_token()
                user_cookies['token'] = token.to_string()
                # make the user log in and authorize this token                    
                self.redirect(dba.build_authorize_url(token, self.request.url))
        elif command == 'unite':
            keyname = user.user_id() + "_dropbox"
            creds_dbox = ServiceData.get_or_insert(keyname)
            keyname = user.user_id() + "_gdocs"
            creds_gdocs = ServiceData.get_or_insert(keyname)
            if creds_dbox == None:
                self.response.out.write("Error: not authorized to use Dropbox")
                return
            if creds_gdocs == None:
                self.response.out.write("Error: not authorized to use GDocs")
                return
            keyname = user.user_id() + "_united"
            creds = ServiceData.get_or_insert(keyname)
            creds.owner = user.user_id()
            creds.service = "united"
            united_creds = [creds_dbox.credentials, creds_gdocs.credentials]
            creds.credentials = json.dumps(united_creds) 
            creds.put()
            self.response.out.write("done!")


class GDataAuth(webapp.RequestHandler):

    def get(self):
        # Write our pages title
        self.response.out.write("""<html><head><title>
            Authorization</title>""")
        self.response.out.write('</head><body>')
        # Allow the user to sign in or sign out
        next_url = atom.url.Url('http', self.request.host, path='/util/gdata_auth')
        if users.get_current_user():
            self.response.out.write('<a href="%s">Sign Out</a><br>' % (
                users.create_logout_url(str(next_url))))
        else:
            self.response.out.write('<a href="%s">Sign In</a><br>' % (
                users.create_login_url(str(next_url))))

        # Initialize a client
        client = gdata.docs.service.DocsService(source='vsd-cloudstorageproxy')
        gdata.alt.appengine.run_on_appengine(client)

        session_token = None
        # Find the AuthSub token and upgrade it to a session token.
        auth_token = gdata.auth.extract_auth_sub_token_from_url(self.request.uri)        
        if auth_token:
            # Upgrade the single-use AuthSub token to a multi-use session token.
            session_token = client.upgrade_to_session_token(auth_token)
        if session_token and users.get_current_user():
            # If there is a current user, store the token in the datastore and
            # associate it with the current user.
            user = users.get_current_user()                                             
            keyname = user.user_id() + "_gdocs"
            creds = ServiceData.get_or_insert(keyname)
            creds.owner = user.user_id()
            creds.service = "gdocs"
            creds.credentials = session_token.get_token_string()
            creds.put()
        elif session_token:
            # Since there is no current user, we will put the session token
            # in a property of the client. We will not store the token in the
            # datastore, since we wouldn't know which user it belongs to.
            # Since a new client object is created with each get call, we don't
            # need to worry about the anonymous token being used by other users.
            client.current_token = session_token

        self.response.out.write('<div id="main"></div>')
        self.response.out.write(
            '<div id="sidebar"><div id="scopes"><h4>Request a token</h4><ul>')
        self.response.out.write('<li><a href="%s">Google Documents</a></li>' % (
            client.GenerateAuthSubURL(
                next_url,
                ('http://docs.google.com/feeds/',), secure=False, session=True)))
        self.response.out.write('</ul></div><br/><div id="tokens">')
                                              
def main():
    application = webapp.WSGIApplication([(r'/util/gdata_auth', GDataAuth),
                                          (r'/util/(.*)', UtilRequestHandler)],                                                                                 
        debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()    