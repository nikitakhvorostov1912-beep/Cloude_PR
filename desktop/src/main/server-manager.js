'use strict'

const { spawn } = require('child_process')
const path = require('path')
const fs = require('fs')
const http = require('http')
const { app } = require('electron')

let backendProcess = null
let frontendProcess = null

/**
 * Получить путь к Python executable
 */
function getPythonPath() {
  if (app.isPackaged) {
    // В продакшн: resources/python/python.exe
    return path.join(process.resourcesPath, 'python', 'python.exe')
  }
  // В разработке: системный Python
  return process.platform === 'win32' ? 'python' : 'python3'
}

/**
 * Получить путь к директории backend
 */
function getBackendDir() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'backend')
  }
  return path.join(__dirname, '../../../../projects/survey-automation/backend')
}

/**
 * Получить путь к директории frontend
 */
function getFrontendDir() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'frontend')
  }
  return path.join(__dirname, '../../../../projects/survey-automation/frontend')
}

/**
 * Получить путь к site-packages (установленные зависимости)
 */
function getSitePackagesDir() {
  return path.join(app.getPath('userData'), 'site-packages')
}

/**
 * Ждать пока порт станет доступен (сервер запустился)
 */
function waitForServer(port, timeoutMs = 60000) {
  return new Promise((resolve, reject) => {
    const start = Date.now()
    const check = () => {
      const req = http.request({ host: '127.0.0.1', port, path: '/', method: 'GET' }, () => {
        resolve()
      })
      req.on('error', () => {
        if (Date.now() - start > timeoutMs) {
          reject(new Error(`Сервер на порту ${port} не запустился за ${timeoutMs / 1000}с`))
          return
        }
        setTimeout(check, 500)
      })
      req.setTimeout(1000, () => {
        req.destroy()
        if (Date.now() - start > timeoutMs) {
          reject(new Error(`Таймаут ожидания сервера на порту ${port}`))
          return
        }
        setTimeout(check, 500)
      })
      req.end()
    }
    check()
  })
}

/**
 * Найти свободный порт начиная с basePort
 */
function findFreePort(basePort) {
  return new Promise((resolve) => {
    const net = require('net')
    const server = net.createServer()
    server.listen(basePort, '127.0.0.1', () => {
      const port = server.address().port
      server.close(() => resolve(port))
    })
    server.on('error', () => {
      resolve(findFreePort(basePort + 1))
    })
  })
}

/**
 * Запустить FastAPI backend
 */
async function startBackend(dataDir, apiKey, onLog) {
  const pythonPath = getPythonPath()
  const backendDir = getBackendDir()
  const sitePackages = getSitePackagesDir()
  const port = await findFreePort(8000)

  onLog && onLog(`Запуск backend на порту ${port}...`)

  const env = {
    ...process.env,
    PYTHONPATH: `${sitePackages}${path.delimiter}${backendDir}`,
    SURVEY_DATA_DIR: dataDir,
    ANTHROPIC_API_KEY: apiKey || '',
    BACKEND_PORT: String(port),
    PYTHONUNBUFFERED: '1',
    PYTHONDONTWRITEBYTECODE: '1',
  }

  backendProcess = spawn(
    pythonPath,
    ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', String(port), '--log-level', 'warning'],
    {
      cwd: backendDir,
      env,
      windowsHide: true,
    }
  )

  backendProcess.stdout.on('data', (data) => {
    onLog && onLog(`Backend: ${data.toString().trim()}`)
  })

  backendProcess.stderr.on('data', (data) => {
    const msg = data.toString().trim()
    if (msg) onLog && onLog(`Backend: ${msg}`)
  })

  backendProcess.on('error', (err) => {
    console.error('Backend process error:', err)
  })

  await waitForServer(port, 30000)
  onLog && onLog(`Backend готов (port ${port})`)

  return port
}

/**
 * Запустить Next.js frontend
 */
async function startFrontend(backendPort, onLog) {
  const frontendDir = getFrontendDir()
  const port = await findFreePort(3000)

  onLog && onLog(`Запуск frontend на порту ${port}...`)

  // Найти node executable (используем тот же что и Electron)
  const nodePath = process.execPath // Electron содержит Node.js

  // В продакшн используем next start
  const nextBin = path.join(frontendDir, 'node_modules', '.bin', 'next')
  const nextBinCmd = process.platform === 'win32' ? nextBin + '.cmd' : nextBin

  const useBuiltNext = fs.existsSync(path.join(frontendDir, '.next'))

  let frontendCmd, frontendArgs
  if (useBuiltNext && fs.existsSync(nextBinCmd)) {
    // Используем системный Node для next start
    frontendCmd = 'node'
    frontendArgs = [nextBin, 'start', '-p', String(port)]
  } else {
    // Fallback: запустить next сервер через node напрямую
    const nextServer = path.join(frontendDir, 'node_modules', 'next', 'dist', 'server', 'next.js')
    frontendCmd = 'node'
    frontendArgs = [nextServer]
  }

  const env = {
    ...process.env,
    PORT: String(port),
    NEXT_PUBLIC_API_URL: `http://127.0.0.1:${backendPort}`,
    NODE_ENV: 'production',
  }

  frontendProcess = spawn(frontendCmd, frontendArgs, {
    cwd: frontendDir,
    env,
    windowsHide: true,
  })

  frontendProcess.stdout.on('data', (data) => {
    onLog && onLog(`Frontend: ${data.toString().trim()}`)
  })

  frontendProcess.stderr.on('data', (data) => {
    const msg = data.toString().trim()
    if (msg && !msg.includes('warn')) onLog && onLog(`Frontend: ${msg}`)
  })

  frontendProcess.on('error', (err) => {
    console.error('Frontend process error:', err)
  })

  await waitForServer(port, 60000)
  onLog && onLog(`Frontend готов (port ${port})`)

  return port
}

/**
 * Остановить все серверы
 */
function stopAll() {
  if (backendProcess) {
    backendProcess.kill('SIGTERM')
    backendProcess = null
  }
  if (frontendProcess) {
    frontendProcess.kill('SIGTERM')
    frontendProcess = null
  }
}

/**
 * Проверить что все серверы живы
 */
function isRunning() {
  return (
    backendProcess !== null &&
    !backendProcess.killed &&
    frontendProcess !== null &&
    !frontendProcess.killed
  )
}

module.exports = {
  getPythonPath,
  getBackendDir,
  getFrontendDir,
  getSitePackagesDir,
  startBackend,
  startFrontend,
  stopAll,
  isRunning,
}
