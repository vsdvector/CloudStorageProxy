using System;
using System.IO;
using System.Collections;
using System.Collections.Concurrent;
using System.Threading;
using System.Threading.Tasks;
using Dokan;
using System.Diagnostics;
using DesktopApp;

namespace CSP
{
    /**
     * <summary>
     * Dokan FS for Cloud Storage Proxy
     * </summary>
     **/
    class CSPDokanFS : DokanOperations
    {
        private CSPClient client;        
        // caching        
        // cache buffers
        ConcurrentDictionary<string, FileCache> fileCaches = new ConcurrentDictionary<string, FileCache>();
        const int precache_bytes = 1024 * 1024; // cache files in 1mb blocks
        const int bufferRemoveDelay = 30000; // wait 30 sec, before deleting file buffer
        bool enableCache;

        public CSPDokanFS(CSPClient client, bool enableCache = true)
        {
            this.client = client;
            this.enableCache = enableCache;
        }      

        public int CreateFile(String filename, FileAccess access, FileShare share,
            FileMode mode, FileOptions options, DokanFileInfo info)
        {                        
            Debug.WriteLine("CreateFile {0} {1}", filename, info.Context);
            // retrieve metadata
            try
            {
                Metadata meta = client.getMetadata(filename, false);
                info.Context = meta;
                info.IsDirectory = meta.is_dir;

                if (meta.is_dir == false)
                {
                    // create file cache
                    FileCache fc = fileCaches.GetOrAdd(meta.path, new FileCache());
                    Interlocked.Increment(ref fileCaches[meta.path].refs);
                }
                return 0;
            }
            catch (NotFoundException)
            {                
                return -DokanNet.ERROR_PATH_NOT_FOUND;
            } 
        }

        public int OpenDirectory(String filename, DokanFileInfo info)
        {                     
            Debug.WriteLine("OpenD {0} {1}", filename, info.Context);
            // retrieve metadata
            try
            {
                Metadata dir = client.getMetadata(filename, false);
                info.Context = dir;
                if (dir.is_dir)
                {
                    return 0;
                }
                else
                {
                    return -DokanNet.ERROR_INVALID_NAME;
                }
            }
            catch (NotFoundException)
            {                
                return -DokanNet.ERROR_PATH_NOT_FOUND;
            }     
        }

        public int CreateDirectory(String filename, DokanFileInfo info)
        {
            return -1;
        }

        public int Cleanup(String filename, DokanFileInfo info)
        {
            //Console.WriteLine("%%%%%% count = {0}", info.Context);
            return 0;
        }

        public int CloseFile(String filename, DokanFileInfo info)
        {
            // close file handle
            Metadata meta = info.Context as Metadata;
            Debug.Print("CloseFile {0}", filename);
            if (meta.is_dir == false && fileCaches.ContainsKey(meta.path))
            {
                // remove file cache buffer 
                // task is used to do it without blocking FS thread
                var task = Task.Factory.StartNew((obj) =>
                {
                    string key = obj as string;
                    Debug.Print("Trying to close {0}", key);
                    Thread.Sleep(bufferRemoveDelay); // wait a little, maybe buffer will be reused
                    lock (fileCaches[key])
                    {
                        fileCaches[key].refs--;
                        if (fileCaches[key].refs <= 0)
                        {
                            FileCache del;
                            fileCaches.TryRemove(key, out del);
                        }
                    }
                }, meta.path);
            }
            return 0;
        }

        private bool ReadFromCache(String filename, Byte[] buffer, ref int readBytes,
            long offset, int offset_buf, Metadata meta) {                
            // get block number
            int block = (int)(offset / precache_bytes);                
            // get cache buffer
            byte[] cbuf = fileCaches[meta.path][block.ToString()];
            if (cbuf != null)
            {
                // block is cached, no need to make expensive network calls
                Debug.WriteLine("CacheHit! ReadFile {0} {1}", filename, offset);
                // calculate how many bytes can be read from cache
                int toCopy = cbuf.Length - (int)(offset % precache_bytes);
                if ((buffer.Length-offset_buf) < toCopy)
                {
                    toCopy = (buffer.Length - offset_buf);
                }
                // read bytes from cache
                Buffer.BlockCopy(cbuf, (int)(offset % precache_bytes), buffer, offset_buf, toCopy);
                readBytes = toCopy;
                if (offset_buf + toCopy < buffer.Length && cbuf.Length == precache_bytes)
                {
                    // still have data to read                        
                    return false;
                }
                else
                {
                    // done!
                    return true;
                }
            }
            readBytes = 0;
            return false;
        }
        public int ReadFile(String filename, Byte[] buffer, ref uint readBytes,
            long offset, DokanFileInfo info)
        {
            Debug.WriteLine("ReadFile {0} {1}", filename, offset);
            readBytes = 0;
            try
            {
                Metadata meta = info.Context as Metadata;                
                if ((ulong)offset >= meta.bytes)
                {
                    // offset out of bound, no bytes read
                    return 0;
                }
                int offset_buf = 0; // offset inside buffer
                int readCache = 0;
                // First, try reading from cache
                if (enableCache) {
                    do
                    {
                        if (ReadFromCache(filename, buffer, ref readCache, offset, offset_buf, meta))
                        {
                            // request satisfied, return
                            readBytes += (uint)readCache;
                            return 0;
                        }
                        offset += readCache;
                        offset_buf += readCache;
                        readBytes += (uint)readCache;
                    }
                    while (readCache != 0);
                }
                // Done reading from cache, read from CSP
                // get file stream
                Stream fs = client.getFile(filename);
                fs.Seek(offset, SeekOrigin.Begin);
                // read bytes to buffer
                readBytes += (uint)fs.Read(buffer, offset_buf, buffer.Length - offset_buf);
                if (enableCache)
                {
                    long remaining = offset + readBytes;
                    // if caching is enabled, write blocks to cache                                        
                    var cacheTask = Task.Factory.StartNew(() =>
                    {
                        int read;
                        offset -= offset % precache_bytes;
                        fs.Seek(offset, SeekOrigin.Begin);
                        do 
                        {
                            byte[] cbuf;                            
                            if(meta.bytes - (ulong)offset < precache_bytes) 
                            {
                                cbuf = new byte[remaining - offset];
                            }
                            else {
                                cbuf = new byte[precache_bytes];
                            }
                            // get block number
                            int block = (int)(offset / precache_bytes);
                            read = fs.Read(cbuf, 0, cbuf.Length);
                            if (fileCaches.ContainsKey(meta.path))
                            {
                                fileCaches[meta.path][block.ToString()] = cbuf;
                            }
                            offset += read;
                        }
                        while(read==precache_bytes && offset < remaining);
                    });
                }
                return 0;
            }
            catch (Exception)
            {
                return -1;
            }
        }      

        public int WriteFile(String filename, Byte[] buffer,
            ref uint writtenBytes, long offset, DokanFileInfo info)
        {
            return -1;
        }

        public int FlushFileBuffers(String filename, DokanFileInfo info)
        {
            return -1;
        }

        public int GetFileInformation(String filename, FileInformation fileinfo, DokanFileInfo info)
        {
            Debug.WriteLine("FileInf {0} {1}", filename, info.Context);
            try
            {                                
                Metadata data = info.Context as Metadata;
                fileinfo.Attributes = data.is_dir ? FileAttributes.Directory : FileAttributes.Normal;
                if (data.modified != "")
                {
                    fileinfo.LastWriteTime = DateTime.Parse(data.modified);                  
                }
                else
                {
                    fileinfo.LastWriteTime = DateTime.Today;         
                }
                fileinfo.CreationTime = fileinfo.LastWriteTime;                
                fileinfo.LastAccessTime = fileinfo.LastWriteTime;
                fileinfo.Length = (long)data.bytes;                
                return 0;
            }
            catch (NotFoundException)
            {
                return -DokanNet.ERROR_PATH_NOT_FOUND;
            }         
        }

        public int FindFiles(String filename, ArrayList files, DokanFileInfo info)
        {
            Debug.WriteLine("FindFiles {0} {1}", filename, info.Context);
            try 
	        {                
                Metadata dir = client.getMetadata(filename);
                if (!dir.is_dir)
                {
                    return -1;
                }
                foreach (Metadata entry in dir.content)
                {
                    FileInformation fi = new FileInformation();
                    fi.Attributes = entry.is_dir ? FileAttributes.Directory : FileAttributes.Normal;
                    if (entry.modified != "")
                        fi.LastWriteTime = DateTime.Parse(entry.modified);
                    else
                        fi.LastWriteTime = DateTime.Now;
                    fi.CreationTime = fi.LastWriteTime;
                    fi.LastAccessTime = fi.LastWriteTime;
                    fi.Length = (long)entry.bytes;
                    fi.FileName = client.getFileName(entry.path);                   
                    files.Add(fi);
                }
                return 0;
	        }
	        catch (NotFoundException)
	        {
                return DokanNet.ERROR_PATH_NOT_FOUND;
	        }            
        }

        public int SetFileAttributes(String filename, FileAttributes attr, DokanFileInfo info)
        {
            return -1;
        }

        public int SetFileTime(String filename, DateTime ctime,
                DateTime atime, DateTime mtime, DokanFileInfo info)
        {
            return -1;
        }

        public int DeleteFile(String filename, DokanFileInfo info)
        {
            return -1;
        }

        public int DeleteDirectory(String filename, DokanFileInfo info)
        {
            return -1;
        }

        public int MoveFile(String filename, String newname, bool replace, DokanFileInfo info)
        {
            return -1;
        }

        public int SetEndOfFile(String filename, long length, DokanFileInfo info)
        {
            return -1;
        }

        public int SetAllocationSize(String filename, long length, DokanFileInfo info)
        {
            return -1;
        }

        public int LockFile(String filename, long offset, long length, DokanFileInfo info)
        {
            return 0;
        }

        public int UnlockFile(String filename, long offset, long length, DokanFileInfo info)
        {
            return 0;
        }

        public int GetDiskFreeSpace(ref ulong freeBytesAvailable, ref ulong totalBytes,
            ref ulong totalFreeBytes, DokanFileInfo info)
        {
            freeBytesAvailable = 512 * 1024 * 1024;
            totalBytes = 1024 * 1024 * 1024;
            totalFreeBytes = 512 * 1024 * 1024;
            return 0;
        }

        public int Unmount(DokanFileInfo info)
        {
            return 0;
        }       
    }

    class CSPDokan
    {
        DokanOptions opt = new DokanOptions();
        CSPClient client;
        bool mounted = false;
        Thread dokanMain;
        public bool isMounted { get { return mounted; } }

        public CSPDokan(CSPClient client)
        {
            this.client = client;
        }

        void DokanThread()
        {
            int status = DokanNet.DokanMain(opt, new CSPDokanFS(client));
            mounted = false;
            OnIsMountedChange(status);
        }

        public void Mount(string drive)
        {        
            opt.DebugMode = true;
            opt.MountPoint = drive;
            opt.ThreadCount = 5;
            opt.NetworkDrive = true;
            opt.UseKeepAlive = true;
            dokanMain = new Thread(DokanThread);
            dokanMain.Start();
            mounted = true;
            OnIsMountedChange();
        }

        public void Unmount()
        {
            int status = DokanNet.DokanUnmount(opt.MountPoint[0]);
            if (status == DokanNet.DOKAN_SUCCESS)
            {
                mounted = false;
                OnIsMountedChange();
                // Unfortunately, unmount doesn't work(at least at the moment)
                // Use dokanctl forced unmount
                System.Diagnostics.Process.Start("dokanctl.exe", String.Format("/u {0} /f", opt.MountPoint));
            }
        }

        private void OnIsMountedChange(int status=0)
        {
            if (IsMountedChanged != null)
            {
                var e = new IsMountedChangeEventArgs();
                e.isMounted = mounted;
                e.status = status;
                e.driveLetter = opt.MountPoint;
                IsMountedChanged(this,e);
            }
        }        
       
        public event IsMountedChangeEventHandler IsMountedChanged;

        public delegate void IsMountedChangeEventHandler(object sender, IsMountedChangeEventArgs e);

    }

    class IsMountedChangeEventArgs
    {
        public bool isMounted { get; set; }
        public int status { get; set; }
        public string driveLetter { get; set; }
    }
}
