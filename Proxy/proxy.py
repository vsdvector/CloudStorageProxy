'''
    Cloud storage proxy entry point
'''

import auth
from servicedata import ServiceData, ShareLink
from backend.dropbox_backend import DropboxBackend
from backend.united_backend import UnitedBackend
from backend.gdocs_backend import GDocsBackend
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from django.utils import simplejson as json
import mimetypes

class UCSPRequestHandler(webapp.RequestHandler):
    
    def __init__(self):
        ''' Initialize service adapters '''
        # TODO: this should be read from config file or something
        self.services = [('dropbox', DropboxBackend()), 
                         ('gdocs', GDocsBackend(True)),
                         ('united', UnitedBackend(True))]
        
        self.default_service, self.default_backend = self.get_service("dropbox")
        
        ''' add some mimetypes '''
        mimetypes.init()
        mimetypes.add_type('application/vnd.oasis.opendocument.text', '.odt')
           
    def detect_service(self):
        ''' Find requested service adapter '''
        srv = self.request.path_info_peek()
        found = self.get_service(srv)
        if found == None: # not found            
            return self.default_service, self.default_backend 
        else:
            self.request.path_info_pop()
            return found
                
    def get_service(self, service_name):
        # try to find service with given service_name         
        found = [e for e in self.services if e[0] == service_name]                
        if len(found):
            return found[0]
        else:
            # if not found, return empty
            return None
    
    def send_unauthorized(self, message = ""):
        # send a 401 error
        self.error(401)            
        self.response.headers.add_header("Cache-Control", "no-store")                
        self.response.out.write("Unauthorized: " + message)        
        
    def check_public_commands(self, command):
        ''' check and execute commands, 
            which are available without authorization 
        '''
        
        if command == 'link':
            # get file from link code
            code = self.request.path_info_pop()                
            link = ShareLink.gql('WHERE link = :1', code).get()            
            if link == None:
                # link not found
                self.error(404)
                return True            
            status, metadata = self.backend.get_metadata(link.path, link.data.credentials)
            type = mimetypes.guess_type(metadata['path'])
            if type[0]:
                self.response.headers['Content-Type'] = type[0]          
            # check if file is modified
            if status == 200:
                if self.request.headers.get('If-None-Match', '') == metadata['version']:
                    status = 304
                else:
                    # output file content
                    status = self.backend.get_file(self.response.out, link.path, link.data.credentials)
                    self.response.headers.add_header("ETag", metadata['version'])
                            
            self.response.set_status(status)            
            return True
            
        if command == 'extensions':
            # return list of supported extensions
            query = self.request.get('name',None)
            extensions = self.backend.get_extensions()
            if query:
                # if query parameter is supplied, 
                # then check only queried extension
                if query in extensions:
                    self.response.out.write('True')
                else: 
                    self.response.out.write('False')
            else: 
                json.dump(extensions, self.response.out)            
            return True            
        
        return False
        
    def get(self, command, service=None):
        ''' process GET request        
        '''
                
        if service == None:
            # select service adapter
            self.service, self.backend = self.detect_service()
            command = self.request.path_info_pop()            
  
        # not all commands need authorization
        if self.check_public_commands(command):
            return        
                
        # Check authorization
        user_auth = auth.valid_token(self.request)
        if user_auth == None:
            self.send_unauthorized()
            return
                     
        if command == 'files':            
            # pass whole file to user
            creds_key = user_auth.owner + "_" + self.service
            creds = ServiceData.get_by_key_name(creds_key)
            if creds == None:
                self.send_unauthorized('no authorization data for service '+self.service)
            else:
                if self.request.get('version'):
                    params = {'version' : self.request.get('version')}
                else:
                    params = None
                path = self.request.path_info                
                status = self.backend.get_file(self.response.out, path, creds.credentials, params)
                self.response.set_status(status)
            return                    
            
        if command == 'metadata':            
            # return metadata
            creds_key = user_auth.owner + "_" + self.service
            creds = ServiceData.get_by_key_name(creds_key)

            if creds == None:                
                self.send_unauthorized('no authorization data for service '+self.service)
            else:
                if self.request.get('list'):
                    params = {'list' : True if self.request.get('list') == 'true' else False }
                else:
                    params = None              
                path = self.request.path_info
                status, metadata = self.backend.get_metadata(path, creds.credentials, params)
                # output json
                json.dump(metadata, self.response.out, ensure_ascii=False)                
                self.response.set_status(status)                            
            return
        
        if command == 'addshare':
            # create public link to file
            creds_key = user_auth.owner + "_" + self.service
            creds = ServiceData.get_by_key_name(creds_key)
            if creds == None:
                self.send_unauthorized('no authorization data for service '+self.service)
            else:
                path = self.request.path_info
                link_key = creds_key + path
                link = ShareLink.get_or_insert(link_key, data=creds, path=path)
                link.regenerate_link() # generate link code                
                self.response.out.write(link.link)
            return
        
        if command == 'share':
            # return list of shares
            # get credentials            
            creds_key = user_auth.owner + "_" + self.service
            creds = ServiceData.get_by_key_name(creds_key)
            if creds == None:
                self.send_unauthorized('no authorization data for service '+self.service)
            else:
                links = ShareLink.gql('WHERE data = :1', creds)
                link_list = [(link.path, link.link) for link in links]
                # return json
                json.dump(link_list, self.response.out, ensure_ascii=False)                                
            return
        
        if command == 'unshare':
            # delete public link to file
            # get credentials
            creds_key = user_auth.owner + "_" + self.service
            creds = ServiceData.get_by_key_name(creds_key)
            if creds == None:
                self.send_unauthorized('no authorization data for service '+self.service)
            else:
                path = self.request.path_info
                link_key = creds_key + path
                link = ShareLink.get_by_key_name(link_key)
                if link == None:
                    self.error(404)
                else: 
                    link.delete()
            return
                        
        # if we got down here then command is not recognized
        # report error
        self.error(400)            
        self.response.headers.add_header("Cache-Control", "no-store")                
        self.response.out.write("Unsupported command")
        
    def post(self, command, service=None):
        ''' process POST request        
        '''
        
        if service == None:
            # select service adapter
            self.service, self.backend = self.detect_service()
            command = self.request.path_info_pop()
        
        # Check authorization
        user_auth = auth.valid_token(self.request)
        if user_auth == None:                    
            self.send_unauthorized()
            return
                     
        if command == 'files':            
            # pass whole file to user
            creds_key = user_auth.owner + "_" + self.service
            creds = ServiceData.get_by_key_name(creds_key)
            if creds == None:
                self.send_unauthorized('no authorization data for service '+self.service)
            else:                
                path = self.request.path_info
                # construct file-like object for backend
                import StringIO                
                # use raw post parameter
                buf = StringIO.StringIO(self.request.str_POST['file'])
                status = self.backend.put_file(path, creds.credentials, buf)
                self.response.set_status(status)                            
            return
        
        if command == 'share':
            # add public link
            # call addshare handler
            self.get('addshare', self.service)
    
    def delete(self, command, service=None):
        ''' process DELETE request
        '''
        
        if service == None:
            # select service adapter            
            self.service, self.backend = self.detect_service()
            command = self.request.path_info_pop()
        
        # Check authorization
        user_auth = auth.valid_token(self.request)
        if user_auth == None:            
            self.send_unauthorized()
            return
        
        if command == 'share':
            # delete public link
            # call unshare handler
            self.get('unshare', self.service)  
                
              
def main():
    application = webapp.WSGIApplication([(r'.*/authorize', auth.RequestHandler), 
                                          (r'.*/access_token', auth.RequestHandler),
                                          (r'/(.*)', UCSPRequestHandler)],
        debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()