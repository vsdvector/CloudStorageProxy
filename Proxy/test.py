# -*- coding: utf8 -*-
'''
Proxy and dropbox latency tests
Created on 17.05.2011

@author: VECTOR
'''

import time
import httplib
from dropbox import client, auth
from oauth import oauth
import StringIO
import poster
import simplejson

token = "?oauth_token=<token>"
db_token = "oauth_token_secret=<token>"
    
def get_db():
    db_config = {'consumer_key': 'key', 
              'consumer_secret': 'secret',
              'server' : 'api.dropbox.com',
              'content_server' : 'api-content.dropbox.com',
              'port' : '80', 
              'request_token_url' : 'https://api.dropbox.com/0/oauth/request_token',
              'access_token_url' : 'https://api.dropbox.com/0/oauth/access_token',
              'authorization_url' : 'https://www.dropbox.com/0/oauth/authorize',
              'trusted_access_token_url' : 'https://api.dropbox.com/0/oauth/token',
              'root': 'dropbox',
              'verifier': ''}
    # init 
    dba = auth.Authenticator(db_config)
    # convert credentials to token
    access_token = oauth.OAuthToken.from_string(db_token)
    # get client object
    db_client = client.DropboxClient(db_config['server'],
                                         db_config['content_server'], 
                                         db_config['port'], 
                                         dba, access_token)
    return db_client
 

def print_timing(func):
    def wrapper(*arg):
        t1 = time.time()
        res = func(*arg)
        t2 = time.time()
        print '%s took %0.3f ms' % (func.func_name, (t2-t1)*1000.0)
        return res
    return wrapper


def db_getFile(file):
    db = get_db() 
    resp = db.get_file("dropbox", file)
    tmp = resp.read()
    if resp.status == 200:
        print 'Got ' + file + ' successfully'
    else:
        print 'Error getting file ' + file + ' ' + str(resp.status)
        print 'Content: ' + tmp;
    return tmp
        
def proxy_getFile(file):    
    con = httplib.HTTPConnection("vsd-storage.appspot.com")
    con.request("GET", "/files"+file+token)
    resp = con.getresponse()
    tmp = resp.read() 
    if resp.status == 200:
        print 'Got ' + file + ' successfully'
    else:
        print 'Error getting file ' + file + ' ' + str(resp.status)
        print 'Content: ' + tmp
    return tmp

@print_timing
def db_latency(file):
    db = get_db() 
    resp = db.get_file("dropbox", file)
    
@print_timing
def proxy_latency(file):    
    con = httplib.HTTPConnection("vsd-storage.appspot.com")
    con.request("GET", "/files"+file+token)
    resp = con.getresponse()    
        
@print_timing
def db_get6mbFile():
    db_getFile("/tests/6mb.rar")    
        
@print_timing
def proxy_get6mbFile():
    proxy_getFile("/tests/6mb.rar")    
        
@print_timing
def proxy_getSmallFile():
    return proxy_getFile("/tests/small.bmp")
        
@print_timing
def db_getSmallFile():
    return db_getFile("/tests/small.bmp")
    
@print_timing
def proxy_get13mbFile():
    proxy_getFile("/tests/13mb.pdf")
        
@print_timing
def db_get13mbFile():
    db_getFile("/tests/13mb.pdf")   
        
@print_timing
def proxy_getPublic():
    con = httplib.HTTPConnection("vsd-storage.appspot.com")
    con.request("GET", "/link/533eb997d9d6b5167c5ea678108f4861537c5112")
    resp = con.getresponse()
    tmp = resp.read() 
    if resp.status == 200:
        print 'Got public file successfully'
    else:
        print 'Error getting public file from proxy ' + str(resp.status)
        print 'Content: ' + tmp 
        
@print_timing
def db_getPublic():
    con = httplib.HTTPConnection("dl.dropbox.com")
    con.request("GET", "/u/4309027/6mb.rar")
    resp = con.getresponse()
    tmp = resp.read() 
    if resp.status == 200:
        print 'Got public file successfully'
    else:
        print 'Error getting public file ' + str(resp.status)
        print 'Content: ' + tmp    

@print_timing
def db_put6mbFile(file):
    db = get_db()     
    buf = StringIO.StringIO(file)
    buf.name = "up.rar"
    resp = db.put_file("dropbox", "/tests", buf)    
    if resp.status == 200:
        print 'Uploaded successfully'
    else:
        print 'Error uploading file to dropbox ' + str(resp.status)
        
@print_timing
def proxy_put6mbFile(file):
    params = {}    
    params['file'] = file    
    data, mp_headers = poster.encode.multipart_encode(params)
    if 'Content-Length' in mp_headers:
        mp_headers['Content-Length'] = str(mp_headers['Content-Length'])
    con = httplib.HTTPConnection("vsd-storage.appspot.com")    
    con.request("POST", "/files/tests/up.rar"+token, "".join(data), mp_headers)
    resp = con.getresponse()    
    if resp.status == 200:
        print 'Uploaded successfully'
    else:
        print 'Error uploading file to proxy ' + str(resp.status)
        
@print_timing
def proxy_list(file):
    con = httplib.HTTPConnection("vsd-storage.appspot.com")
    con.request("GET", "/metadata"+file+token)
    resp = con.getresponse()
    # emulate reading and parsing
    tmp = resp.read()
    obj = simplejson.loads(tmp)
    if resp.status == 200:
        print 'Got file list successfully'
    else:
        print 'Error getting file list proxy ' + str(resp.status)
        print 'Content: ' + tmp
        
@print_timing
def db_list(file):
    db = get_db() 
    resp = db.metadata("dropbox", file)            
    if resp.status == 200:
        print 'Got ' + file + ' successfully'
    else:
        print 'Error getting file ' + file + ' ' + str(resp.status)
        print 'Content: ' + resp.body;               
      
    
if __name__ == "__main__":   
    print "Small(<1mb) file test:"
    proxy_getSmallFile()   
    content = db_getSmallFile()
    print "6mb file test:"    
    proxy_get6mbFile()   
    db_get6mbFile()
    print "13mb file test:"
    proxy_get13mbFile()   
    db_get13mbFile()
    print "Test public link:"
    proxy_getPublic()   
    db_getPublic()
    print "Upload test:"
    proxy_put6mbFile(content)
    db_put6mbFile(content)
    print "Directory list test:"
    proxy_list("/OMG!!!/src/gdata")
    db_list("/OMG!!!/src/gdata")
    print "Latency test:"
    proxy_latency("/test.txt")
    db_latency("/test.txt")
    
