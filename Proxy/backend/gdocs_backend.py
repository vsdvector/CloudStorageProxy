'''
Google Docs backend
Created on 16.04.2011

@author: VECTOR
'''

import backend
import gdata.docs.client
import gdata.gauth
from datetime import datetime
from base64 import b64encode


class GDocsBackend(backend.Backend):    
    
    def __init__(self, appengine=False):
        self.appengine = appengine
        
    def get_client(self, credentials):
        gd_client = gdata.docs.client.DocsClient(source='vsd-cloudstorageproxy')        
        gd_client.auth_token = gdata.gauth.AuthSubToken(credentials) 
        self.scope = credentials           
        return gd_client
        
    def get_file(self, fp, path, credentials, params):
        ''' Serve file from backend
        
        fp - a .write()-supporting file-like object
        path - path to file to serve
        credentials - credentials object for backend storage
        params - other params
        
        returns http status code
        '''
        client = self.get_client(credentials)
        path = path[1:]         
        id = self._get_path_id(client, path)        
        if id:
            entry = client.GetDoc(id)
            content = client.GetFileContent(uri=entry.content.src)
            fp.write(content)
            return 200                             
        else:                              
            return 404
    
    def _datetime(self,dt):
        dt = datetime.strptime( dt.text[:-5], "%Y-%m-%dT%H:%M:%S" )        
        return dt
        
        
    def _read_metadata(self, gd_metadata):
        ''' get metadata from GDocs entry
        '''

        dt = self._datetime(gd_metadata.updated)
        version = gd_metadata.etag
        is_dir = True if gd_metadata.get_document_type() == "folder" else False    
        bytes = gd_metadata.FindExtensions("quotaBytesUsed")
        if bytes:
            bytes = bytes[0].text
        else:
            bytes = 0        
                                        
        metadata = {"bytes": bytes,
                    "modified": dt.isoformat(' '),
                    "path": gd_metadata.title.text,                    
                    "version": version,                    
                    "gdocs_link": gd_metadata.GetAlternateLink().href,
                    "is_dir": is_dir}        
        return metadata    
    
    def _path_encode(self, path):
        return b64encode(path)
    
    def _get_path_id(self, client, path):        
        id = self._cache_get(self._path_encode(path),namespace=self.scope)        
        if id:
            return id
                                
        feed = client.GetDocList(uri='/feeds/default/private/full?title='+path+'&title-exact=true&showfolders=true')
        if feed.entry:              
            return feed.entry[0].resource_id.text                
        else:              
            return None;
        
    def get_metadata(self, path, credentials, params=None):
        ''' Get file or folder metadata
               
        path - path to file or folder
        credentials - credentials object for backend storage
        params - other params        
        
        returns http status code and metadata
        '''
        # TODO: caching(304 headers)  
        path = path[1:]        
        client = self.get_client(credentials)
        # list and version parameters        
        list = True
        if params:                                 
                list = params.get('list', list)
                 
        if path:                
            id = self._get_path_id(client, path)
            if id:
                metadata = self._read_metadata(client.GetDoc(id))                            
                content_uri = '/feeds/default/private/full/'+id+'/contents'                 
            else:                              
                return 404, None;
        else:
            # return root folder metadata
            metadata = {"bytes": 0,
                        "modified": '',
                        "path": '/',
                        "version": 0,
                        "is_dir": True} 
            content_uri = '/feeds/default/private/full/folder%3Aroot/contents'        
        if list and metadata['is_dir']:
            feed = client.GetDocList(content_uri)
            metadata['content'] = []
            for doc in feed.entry:
                metadata['content'].append(self._read_metadata(doc))                                    
                self._cache_set(self._path_encode(doc.title.text.encode("utf-8")), 
                                doc.resource_id.text,
                                namespace=self.scope)
        return 200, metadata 
    
    def get_extensions(self):
        return ['gdocs-links']
    
    #TODO: other functions 