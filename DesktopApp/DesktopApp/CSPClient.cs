using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Runtime.Serialization.Json;
using System.Runtime.Serialization;
using Microsoft.Http;
using System.IO;

namespace CSP
{
    /**
     * <summary>
     * Cloud storage proxy client
     * </summary>
     **/
    class CSPClient
    {
        Uri baseUri = new Uri("https://vsd-storage.appspot.com/");
        const string client_id = "DesktopApp";
        const string client_secret = "secret";

        bool auth = false; // is client authorized
        AccessToken token; // access token        
        //Dictionary<string, Metadata> gdocs_links = new Dictionary<string,Metadata>();
        Cache<Metadata> metadataCache = new Cache<Metadata>();

        public void setBaseUri(string uri)
        {
            baseUri = new Uri(uri);
        }

        public bool isAuthorized { get {return auth;} }
        public bool gdocsLinkExtension { get; set; }        

        /**
         * Return file name from path
         */
        public string getFileName(string path)
        {
            string[] parts = path.Split('/');
            if (parts.Length == 0)
            {
                return "";
            }
            else
            {
                return parts[parts.Length - 1];
            }
        }

        #region FileContent
        /**
         *  Get file content
         *  TODO: range query?
         */
        public Stream getFile(string path)
        {
            // remove leading slash
            path = stripLeadingSlash(path);
            
            if (gdocsLinkExtension )
            {
                Metadata metadata = metadataCache[path];
                if (metadata != null && metadata.gdocs_link!=null)
                {
                    return createUrlFileContent(metadata.gdocs_link);
                }
            }
            HttpClient http = new HttpClient(baseUri);
            HttpQueryString query = new HttpQueryString();            
            query.Add("oauth_token", token.access_token);
            Uri contentUri = new Uri(string.Format("files/{0}", Uri.EscapeUriString(path)), UriKind.Relative);
            HttpResponseMessage resp = http.Get(contentUri, query);
            if (resp.StatusCode == System.Net.HttpStatusCode.OK)
            {                
                return new MemoryStream(resp.Content.ReadAsByteArray(), false);                
            }
            else if (resp.StatusCode == System.Net.HttpStatusCode.NotFound)
            {
                throw new NotFoundException();
            }
            else
            {
                throw new BadRequestException();
            }
        }

        private Stream createUrlFileContent(string p)
        {            
            String content = "[InternetShortcut]\r\nURL=" + p;
            return new MemoryStream(ASCIIEncoding.Default.GetBytes(content));
        }
        #endregion

        #region Metadata

        /**
         * Remove leading slash
         **/
        private string stripLeadingSlash(string path) 
        {
            // remove leading slash
            while (path.Length > 0 && (path[0] == '/' || path[0] == '\\'))
            {
                path = path.Substring(1);
            }
            return path;
        }
        /**
         * Retrieve metadata from CSP
         * includes simple caching
         */
        public Metadata getMetadata(string path, bool list=true)
        {
            path = stripLeadingSlash(path);   
            // check metadata cache
            Metadata metadata = metadataCache[path];
            if (metadata != null)
            {
                System.Diagnostics.Debug.Print("MetadataCache hit! {0}", path);
                return metadata;
            }
        
            HttpClient http = new HttpClient(baseUri);
            HttpQueryString query = new HttpQueryString();
            if (list)
            {
                query.Add("list", list.ToString());
            }
            query.Add("oauth_token", token.access_token);
            Uri metadataUri = new Uri(string.Format("metadata/{0}", Uri.EscapeUriString(path)),UriKind.Relative);
            HttpResponseMessage resp = http.Get(metadataUri, query);
            if (resp.StatusCode == System.Net.HttpStatusCode.OK)
            {
                if (gdocsLinkExtension)
                {
                    metadata = resp.Content.ReadAsJsonDataContract<Metadata>();                    
                    PlaceUrlFiles(metadata);                    
                }
                else
                {
                    metadata = resp.Content.ReadAsJsonDataContract<Metadata>();                    
                }
                metadataCache[path] = metadata;
                return metadata;
            }
            else if (resp.StatusCode == System.Net.HttpStatusCode.NotFound)
            {
                throw new NotFoundException();
            }
            else
            {
                throw new BadRequestException();
            }
        }

        /**
         * Replace GDocs with .url files
         */
        private void PlaceUrlFiles(Metadata metadata) 
        {    
            if (metadata.gdocs_link != null && !metadata.is_dir)
            {                
                metadata.path = metadata.path + ".url";
                metadata.bytes = 24 + (ulong)metadata.gdocs_link.Length;
                metadataCache[stripLeadingSlash(metadata.path)] = metadata;
            }
            
            if (metadata.content != null)
            {
                foreach (var item in metadata.content)
                {
                    PlaceUrlFiles(item);
                }
            }
        }

        #endregion

        #region Authorization
        public void dropToken()
        {
            token = null;
            auth = false;
        }

        public Uri getAuthorizeUri(String redirectUri) 
        {
            Uri auth = new Uri(string.Format("{0}authorize?client_id={1}&redirect_uri={2}",baseUri, client_id, redirectUri));
            return auth;
        }

        public bool authorize(String authCode)
        {
            // get the access token
            HttpClient http = new HttpClient(baseUri);
            HttpUrlEncodedForm req = new HttpUrlEncodedForm();
            req.Add("code", authCode);
            req.Add("client_secret", client_secret);
            req.Add("client_id", client_id);
            HttpResponseMessage resp = http.Post("access_token", req.CreateHttpContent());
            if (resp.StatusCode == System.Net.HttpStatusCode.OK)
            {
                token = resp.Content.ReadAsJsonDataContract<AccessToken>();
                auth = true;
                return true;
            }
            auth = false;
            return false;
        }
        #endregion
    }


    [DataContract]
    public class Metadata
    {
        [DataMember]
        public string gdocs_link { get; set; }

        [DataMember]
        public string path { get; set; }

        [DataMember]
        public bool is_dir { get; set; }

        [DataMember]
        public ulong bytes { get; set; }

        [DataMember]
        public string version { get; set; }

        [DataMember]
        public string modified { get; set; }

        [DataMember]
        public List<Metadata> content { get; set; }
    }

    [DataContract]
    public class AccessToken
    {
        [DataMember]
        public string access_token { get; set; }

        [DataMember]
        public string token_type { get; set; }
    }

    #region Exception classes
    public class NotFoundException : Exception { }
    public class BadRequestException : Exception { }    
    #endregion
}
