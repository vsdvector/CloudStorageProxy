'''
Dropbox backend
Created on 10.04.2011

@author: VECTOR
'''
import backend
from dropbox import client, auth
from oauth import oauth
import datetime


class DropboxBackend(backend.Backend):
    
    config = {'consumer_key': 'hnbwqql0f0pr70c', 
              'consumer_secret': 'rfniknyvzb4wkby',
              'server' : 'api.dropbox.com',
              'content_server' : 'api-content.dropbox.com',
              'port' : '80', 
              'request_token_url' : 'https://api.dropbox.com/0/oauth/request_token',
              'access_token_url' : 'https://api.dropbox.com/0/oauth/access_token',
              'authorization_url' : 'https://www.dropbox.com/0/oauth/authorize',
              'trusted_access_token_url' : 'https://api.dropbox.com/0/oauth/token',
              'root': 'dropbox',
              'verifier': ''}      
    
    def _get_client(self, credentials):
        # init 
        dba = auth.Authenticator(DropboxBackend.config)
        # convert credentials to token
        access_token = oauth.OAuthToken.from_string(credentials)
        # get client object
        db_client = client.DropboxClient(DropboxBackend.config['server'],
                                         DropboxBackend.config['content_server'], 
                                         DropboxBackend.config['port'], 
                                         dba, access_token)
        return db_client
        
    def get_file(self, fp, path, credentials, params=None):
        # init 
        db = self._get_client(credentials)
                
        if params and params['version']:            
            # check if not modified
            status, metadata = self.get_metadata(path, credentials)
            
            if status == 200: 
                if metadata['version'] == params['version']:
                    return 304
            else:
                return status
        # TODO: byte range support
        resp = db.get_file(DropboxBackend.config['root'], path)
                        
        if resp.status == 200:
            fp.write(resp.read())
        elif resp.status == 400:
            return 401
        
        return resp.status
    
    def _datetime(self, dt):
        if dt == '':
            return ''
        dt = datetime.datetime.strptime( dt[:-6] , '%a, %d %b %Y %H:%M:%S')        
        return dt.isoformat(' ')
        
    def _read_metadata(self, db_metadata):
        ''' convert metadata from dropbox representation to our representation
        '''
        version = str(db_metadata.get('revision',0))
        metadata = {"bytes": db_metadata['bytes'],
                    "modified": self._datetime(db_metadata.get('modified', '')),
                    "path": db_metadata['path'],
                     "version": version,
                     "is_dir": db_metadata['is_dir']}
        return metadata
    
    def get_metadata(self, path, credentials, params=None):
        # init 
        db = self._get_client(credentials)
        # list and version parameters
        hash = None
        list = True
        if params:                 
                hash = params.get('version', hash)
                list = params.get('list', list)            
        
        resp = db.metadata(DropboxBackend.config['root'], path)
        if resp.status == 200:
            metadata = self._read_metadata(resp.data)
            if list and metadata['is_dir']:
                metadata['content'] = []
                for data in resp.data['contents']:
                    metadata['content'].append(self._read_metadata(data))            
        else:
            metadata = {}
            
        status = resp.status if resp.status != 400 else 401 # use correct status code
        return status, metadata
    
    def put_file(self, path, credentials, content, params=None):
        db = self._get_client(credentials)
        content.name, path = self.get_filename_and_path(path)
        
        resp = db.put_file(DropboxBackend.config['root'], path, content)        
        
        return resp.status if resp.status != 400 else 401 # use correct status code    
        

        
        
        
