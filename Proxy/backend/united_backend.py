'''
United gdocs and dbox backend
Created on 14.05.2011

@author: VECTOR
'''

import backend.gdocs_backend;
import backend.dropbox_backend;
import json;


class UnitedBackend(backend.Backend):    
    
    def __init__(self, appengine=False):
        self.dbox = backend.dropbox_backend.DropboxBackend()
        self.gdocs = backend.gdocs_backend.GDocsBackend()
        
    def put_file(self, path, credentials, content, params=None):
        if path.startswith('/documents'):
            # process with gdocs
            return 400        
        else:
            return self.dbox.put_file( path, self._db_credentials(credentials), content)
    
    def get_file(self, fp, path, credentials, params):
        ''' Serve file from backend
        
        fp - a .write()-supporting file-like object
        path - path to file to serve
        credentials - credentials object for backend storage
        params - other params
        
        returns http status code
        '''
        if path.startswith('/documents'):
            # process with gdocs
            return self.gdocs.get_file(fp, path[10:], self._gd_credentials(credentials), params)        
        else:
            return self.dbox.get_file(fp, path, self._db_credentials(credentials), params)
    
    def _gd_credentials(self, credentials):
        ''' return gdocs credentials '''
        creds_obj = json.loads(credentials)        
        return creds_obj[1] 
    
    def _db_credentials(self, credentials):
        ''' return dropbox credentials '''
        creds_obj = json.loads(credentials)        
        return creds_obj[0]
            
    def get_metadata(self, path, credentials, params=None):
        ''' Get file or folder metadata
               
        path - path to file or folder
        credentials - credentials object for backend storage
        params - other params        
        
        returns http status code and metadata
        '''
        if path.startswith('/documents'):
            # process with gdocs
            return self.gdocs.get_metadata(path[10:], self._gd_credentials(credentials), params)
        else:
            # process with dropbox
            res, metadata = self.dbox.get_metadata(path, self._db_credentials(credentials), params)
            if res == 200 and path == '/':
                metadata['content'].append({"bytes": 0,
                                 "modified": '',
                                 "path": '/documents',
                                 "version": 0,
                                 "is_dir": True})
            return res, metadata
    
    def get_extensions(self):
        # return all extensions
        extensions = []       
        extensions = extensions + self.dbox.get_extensions()
        extensions = extensions + self.gdocs.get_extensions()
    
    #TODO: other functions 