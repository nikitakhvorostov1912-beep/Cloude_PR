/**
 * Хранилище аудиофайлов в IndexedDB.
 * Blob URL не переживает перезапуск приложения — IndexedDB сохраняет файлы между сессиями.
 */

const DB_NAME = 'aether-files';
const STORE_NAME = 'audio-files';
const DB_VERSION = 1;

interface StoredFile {
  blob: Blob;
  name: string;
  type: string;
  size: number;
}

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(STORE_NAME)) {
        request.result.createObjectStore(STORE_NAME);
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

/** Сохранить аудиофайл для meetingId */
export async function storeAudioFile(meetingId: string, file: File): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    const data: StoredFile = {
      blob: new Blob([file], { type: file.type }),
      name: file.name,
      type: file.type,
      size: file.size,
    };
    store.put(data, meetingId);
    tx.oncomplete = () => { db.close(); resolve(); };
    tx.onerror = () => { db.close(); reject(tx.error); };
  });
}

/** Получить аудиофайл по meetingId */
export async function getAudioFile(meetingId: string): Promise<File | null> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readonly');
    const store = tx.objectStore(STORE_NAME);
    const request = store.get(meetingId);
    request.onsuccess = () => {
      db.close();
      const data = request.result as StoredFile | undefined;
      if (!data?.blob) { resolve(null); return; }
      const file = new File([data.blob], data.name, { type: data.type });
      resolve(file);
    };
    request.onerror = () => { db.close(); reject(request.error); };
  });
}

/** Удалить аудиофайл */
export async function deleteAudioFile(meetingId: string): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NAME, 'readwrite');
    const store = tx.objectStore(STORE_NAME);
    store.delete(meetingId);
    tx.oncomplete = () => { db.close(); resolve(); };
    tx.onerror = () => { db.close(); reject(tx.error); };
  });
}
