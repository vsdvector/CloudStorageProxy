from google.appengine.api.memcache import set as memcache_set
from google.appengine.api.memcache import get as memcache_get

'''
    Abstract backend class    
'''
class Backend():    
            
    def get_file(self, fp, path, credentials, params):
        ''' Serve file from backend
    
        fp - a .write()-supporting file-like object
        path - path to file to serve
        credentials - credentials object for backend storage
        params - other params
        
        returns http status code
        '''        
        raise NotImplementedError
        
    def put_file(self, path, credentials, content, params=None):
        ''' Save file to backend
                
        path - path to file to serve
        credentials - credentials object for backend storage
        content - a .read()-supporting file-like object
        
        returns http status code
        '''        
        raise NotImplementedError
        
    def get_metadata(self, path, credentials, params=None):
        ''' Get file or folder metadata
           
        path - path to file or folder
        credentials - credentials object for backend storage
        params - other params        
        
        returns http status code and metadata
        '''   
        raise NotImplementedError
        
    def copy_file(self, from_path, to_path, credentials, params=None):
        ''' Copy file or directory
        from_path - source
        to_path - destination
        credentials - credentials object for backend storage
        params - other params        
        
        returns http status code and new metadata
        '''    
        raise NotImplementedError   
    
    def move_file(self, from_path, to_path, credentials, params=None):
        ''' Move file or directory
        from_path - source
        to_path - destination
        credentials - credentials object for backend storage
        params - other params        
        
        returns http status code and new metadata
        '''    
        raise NotImplementedError
    
    def new_directory(self, path, credentials, params=None):
        ''' Create directory
        path - path to new directory        
        credentials - credentials object for backend storage
        params - other params        
        
        returns http status code and new metadata
        '''    
        raise NotImplementedError
    
    def delete_file(self, path, credentials, params=None):
        ''' Delete file or directory
        path - path to file or directory        
        credentials - credentials object for backend storage
        params - other params        
        
        returns http status code
        '''    
        raise NotImplementedError
        
    def get_extensions(self):
        ''' Return list of supported extension        
        '''
        return []
        
    # other functions 
    
    def get_filename_and_path(self, path):
        ''' Split full path into file name and path '''
        path = path.split('/')
        return path[-1], '/'.join(path[:-1])
    
    # caching functions, can depend on platform
    
    def _cache_set(self, key, value, namespace=None):
        ''' Store value in cache '''
        memcache_set(key, value, namespace=namespace)
        
    def _cache_get(self, key, namespace=None):
        ''' Get value from cache '''
        memcache_get(key, namespace=namespace)
        