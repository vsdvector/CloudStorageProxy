using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;

namespace CSP
{
    class FileCache
    {
        public int refs = 0;
        Cache<byte[]> buffers = new Cache<byte[]>();
        
        public byte[] this[string index]
        {
            get { return buffers[index]; }
            set { buffers[index] = value; }
        }
    }
}
