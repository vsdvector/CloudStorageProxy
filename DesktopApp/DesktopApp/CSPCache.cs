using System;
using System.Collections.Concurrent;
using System.Linq;
using System.Text;

class Cache<T>
{
    ConcurrentDictionary<string, CacheItem<T>> dict = new ConcurrentDictionary<string, CacheItem<T>>();
    int expires;

    public Cache(int expires = 30)
    {
        this.expires = expires;
    }

    public void add(string key, T value)
    {
        CacheItem<T> newItem = new CacheItem<T>();
        newItem.value = value;
        newItem.expires = DateTime.Now + TimeSpan.FromSeconds(expires);
        dict[key] = newItem;
    }

    public T this[string index]
    {
        get
        {
            CacheItem<T> item;
            if (dict.TryGetValue(index, out item))
            {                
                // check if cache has not expired
                if (item.expires > DateTime.Now)
                {                    
                    return item.value;
                }                
            }
            return default(T);
        }
        set { add(index, value); }
    }

    private class CacheItem<T2>
    {
        public T2 value;
        public DateTime expires;
    }
}

