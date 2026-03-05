'use strict'

const { app, BrowserWindow, Menu, Tray, ipcMain, shell, dialog, nativeImage } = require('electron')
const path = require('path')
const fs = require('fs')

const { startBackend, startFrontend, stopAll } = require('./server-manager')
const { isSetupRequired, runSetup, resetSetup } = require('./setup-manager')

// Предотвратить множественный запуск
const gotLock = app.requestSingleInstanceLock()
if (!gotLock) {
  app.quit()
}

let mainWindow = null
let tray = null
let backendPort = 8000
let frontendPort = 3000
let isQuitting = false

// ─── Конфиг (API ключ и настройки) ───────────────────────────────────────────

function getConfigPath() {
  return path.join(app.getPath('userData'), 'config.json')
}

function loadConfig() {
  try {
    const configPath = getConfigPath()
    if (fs.existsSync(configPath)) {
      return JSON.parse(fs.readFileSync(configPath, 'utf8'))
    }
  } catch {}
  return {}
}

function saveConfig(data) {
  const configPath = getConfigPath()
  const current = loadConfig()
  fs.writeFileSync(configPath, JSON.stringify({ ...current, ...data }, null, 2))
}

// ─── Loading Window ───────────────────────────────────────────────────────────

function createLoadingWindow() {
  const win = new BrowserWindow({
    width: 480,
    height: 320,
    frame: false,
    resizable: false,
    center: true,
    show: false,
    backgroundColor: '#0f1117',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, '../preload/index.js'),
    },
  })

  win.loadFile(path.join(__dirname, '../../renderer/loading.html'))
  win.once('ready-to-show', () => win.show())

  return win
}

// ─── Main App Window ──────────────────────────────────────────────────────────

function createMainWindow() {
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    show: false,
    title: 'Survey Automation',
    backgroundColor: '#0f1117',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, '../preload/index.js'),
    },
  })

  // Скрыть меню (работаем через tray)
  win.setMenuBarVisibility(false)

  // Minimize to tray вместо закрытия
  win.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault()
      win.hide()
    }
  })

  return win
}

// ─── System Tray ──────────────────────────────────────────────────────────────

function createTray(iconPath) {
  let icon
  try {
    icon = nativeImage.createFromPath(iconPath)
    if (icon.isEmpty()) {
      icon = nativeImage.createEmpty()
    }
  } catch {
    icon = nativeImage.createEmpty()
  }

  const t = new Tray(icon)
  t.setToolTip('Survey Automation')

  const updateMenu = () => {
    const menu = Menu.buildFromTemplate([
      {
        label: 'Открыть приложение',
        click: () => {
          if (mainWindow) {
            mainWindow.show()
            mainWindow.focus()
          }
        },
      },
      { type: 'separator' },
      {
        label: 'Настройки',
        click: () => showSettingsDialog(),
      },
      {
        label: 'Переустановить зависимости',
        click: async () => {
          const { response } = await dialog.showMessageBox({
            type: 'question',
            buttons: ['Отмена', 'Переустановить'],
            defaultId: 0,
            message: 'Переустановить Python зависимости?',
            detail: 'Это может занять несколько минут. Приложение перезапустится.',
          })
          if (response === 1) {
            resetSetup()
            app.relaunch()
            app.quit()
          }
        },
      },
      { type: 'separator' },
      {
        label: 'Выйти',
        click: () => {
          isQuitting = true
          app.quit()
        },
      },
    ])
    t.setContextMenu(menu)
  }

  updateMenu()

  t.on('double-click', () => {
    if (mainWindow) {
      mainWindow.show()
      mainWindow.focus()
    }
  })

  return t
}

// ─── Settings Dialog ──────────────────────────────────────────────────────────

function showSettingsDialog() {
  const config = loadConfig()
  const settingsWin = new BrowserWindow({
    width: 500,
    height: 350,
    parent: mainWindow || undefined,
    modal: true,
    frame: true,
    resizable: false,
    title: 'Настройки — Survey Automation',
    backgroundColor: '#0f1117',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, '../preload/index.js'),
    },
  })

  settingsWin.setMenuBarVisibility(false)
  settingsWin.loadFile(path.join(__dirname, '../../renderer/settings.html'))

  settingsWin.webContents.on('did-finish-load', () => {
    settingsWin.webContents.send('settings-load', config)
  })
}

// ─── IPC Handlers ─────────────────────────────────────────────────────────────

ipcMain.handle('get-config', () => loadConfig())

ipcMain.handle('save-config', (event, data) => {
  saveConfig(data)
  return { ok: true }
})

ipcMain.handle('open-data-folder', () => {
  const dataDir = path.join(app.getPath('userData'), 'data')
  fs.mkdirSync(dataDir, { recursive: true })
  shell.openPath(dataDir)
})

ipcMain.handle('app-version', () => app.getVersion())

ipcMain.on('settings-close', () => {
  const wins = BrowserWindow.getAllWindows()
  wins.forEach(w => {
    if (w.getTitle().startsWith('Настройки')) w.close()
  })
})

// ─── App Lifecycle ────────────────────────────────────────────────────────────

app.whenReady().then(async () => {
  // Ensure user data directory
  const userData = app.getPath('userData')
  fs.mkdirSync(path.join(userData, 'data', 'projects'), { recursive: true })

  const iconPath = app.isPackaged
    ? path.join(process.resourcesPath, 'build', 'icon.ico')
    : path.join(__dirname, '../../build/icon.ico')

  // Создать tray
  tray = createTray(iconPath)

  // Показать loading window
  const loadingWin = createLoadingWindow()

  const sendProgress = (data) => {
    if (loadingWin && !loadingWin.isDestroyed()) {
      loadingWin.webContents.send('progress', data)
    }
  }

  try {
    // ── Первый запуск: установка зависимостей ──
    if (isSetupRequired()) {
      sendProgress({ step: 'setup', text: 'Первый запуск: установка зависимостей...', percent: 0 })
      await runSetup(sendProgress)
    }

    // ── Запуск Backend ──
    sendProgress({ step: 'backend', text: 'Запуск сервисов...', percent: 82 })
    const config = loadConfig()
    const dataDir = path.join(userData, 'data')

    backendPort = await startBackend(dataDir, config.anthropicApiKey || '', (msg) => {
      sendProgress({ step: 'backend', text: msg, percent: null })
    })

    sendProgress({ step: 'backend', text: `Backend запущен (порт ${backendPort})`, percent: 90 })

    // ── Запуск Frontend ──
    sendProgress({ step: 'frontend', text: 'Запуск интерфейса...', percent: 92 })

    frontendPort = await startFrontend(backendPort, (msg) => {
      sendProgress({ step: 'frontend', text: msg, percent: null })
    })

    sendProgress({ step: 'frontend', text: `Готово!`, percent: 100 })

    // ── Открыть главное окно ──
    mainWindow = createMainWindow()

    // Если API ключ не задан — показать предупреждение
    if (!config.anthropicApiKey) {
      mainWindow.once('show', () => {
        dialog.showMessageBox(mainWindow, {
          type: 'warning',
          title: 'API ключ не задан',
          message: 'Укажите ключ Anthropic API в настройках для работы с ИИ-функциями.',
          buttons: ['Открыть настройки', 'Позже'],
        }).then(({ response }) => {
          if (response === 0) showSettingsDialog()
        })
      })
    }

    await new Promise(resolve => setTimeout(resolve, 500))

    // Закрыть loading, показать главное окно
    if (loadingWin && !loadingWin.isDestroyed()) {
      loadingWin.close()
    }

    mainWindow.loadURL(`http://127.0.0.1:${frontendPort}`)
    mainWindow.once('ready-to-show', () => mainWindow.show())

  } catch (error) {
    sendProgress({ step: 'error', text: `Ошибка: ${error.message}`, percent: -1 })

    await dialog.showMessageBox({
      type: 'error',
      title: 'Ошибка запуска',
      message: 'Не удалось запустить Survey Automation',
      detail: error.message + '\n\nПроверьте логи в: ' + path.join(userData, 'error.log'),
      buttons: ['Выйти'],
    })

    fs.writeFileSync(
      path.join(userData, 'error.log'),
      `[${new Date().toISOString()}] ${error.stack || error.message}\n`,
      { flag: 'a' }
    )

    app.quit()
  }
})

app.on('second-instance', () => {
  if (mainWindow) {
    if (mainWindow.isMinimized()) mainWindow.restore()
    mainWindow.show()
    mainWindow.focus()
  }
})

app.on('window-all-closed', () => {
  // Не выходить при закрытии окна — работаем в tray
})

app.on('before-quit', () => {
  isQuitting = true
  stopAll()
})

app.on('will-quit', () => {
  stopAll()
})
