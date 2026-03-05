'use strict'

const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  // Конфиг
  getConfig: () => ipcRenderer.invoke('get-config'),
  saveConfig: (data) => ipcRenderer.invoke('save-config', data),
  appVersion: () => ipcRenderer.invoke('app-version'),

  // Утилиты
  openDataFolder: () => ipcRenderer.invoke('open-data-folder'),

  // Settings window
  closeSettings: () => ipcRenderer.send('settings-close'),

  // Прогресс (loading screen)
  onProgress: (callback) => {
    ipcRenderer.on('progress', (_, data) => callback(data))
  },

  // Settings load
  onSettingsLoad: (callback) => {
    ipcRenderer.on('settings-load', (_, config) => callback(config))
  },
})
