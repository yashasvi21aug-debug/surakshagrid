const DB_NAME = "SurakshaTileCache";
const DB_VERSION = 1;
const STORE_NAME = "tiles";

function openTileDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof window === "undefined" || !window.indexedDB) {
      reject("IndexedDB unsupported");
      return;
    }
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        db.createObjectStore(STORE_NAME);
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function saveTileToCache(url: string, blob: Blob): Promise<void> {
  try {
    const db = await openTileDatabase();
    const tx = db.transaction(STORE_NAME, "readwrite");
    const store = tx.objectStore(STORE_NAME);
    store.put(blob, url);
  } catch (err) {
    console.warn("Failed to store tile in IndexedDB:", err);
  }
}

export async function getTileFromCache(url: string): Promise<Blob | null> {
  try {
    const db = await openTileDatabase();
    return new Promise((resolve) => {
      const tx = db.transaction(STORE_NAME, "readonly");
      const store = tx.objectStore(STORE_NAME);
      const request = store.get(url);
      request.onsuccess = () => resolve(request.result || null);
      request.onerror = () => resolve(null);
    });
  } catch {
    return null;
  }
}

export async function fetchWithTileCache(url: string): Promise<Response> {
  // If offline, check IndexedDB first
  if (typeof navigator !== "undefined" && !navigator.onLine) {
    const cachedBlob = await getTileFromCache(url);
    if (cachedBlob) {
      return new Response(cachedBlob, {
        headers: { "Content-Type": cachedBlob.type || "image/png" },
      });
    }
  }

  try {
    const res = await fetch(url);
    if (res.ok) {
      const clonedBlob = await res.clone().blob();
      saveTileToCache(url, clonedBlob);
    }
    return res;
  } catch (err) {
    const cachedBlob = await getTileFromCache(url);
    if (cachedBlob) {
      return new Response(cachedBlob, {
        headers: { "Content-Type": cachedBlob.type || "image/png" },
      });
    }
    throw err;
  }
}
