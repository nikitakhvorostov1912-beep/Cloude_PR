'use strict'

const { spawn } = require('child_process')
const path = require('path')
const fs = require('fs')
const https = require('https')
const { app } = require('electron')
const { getPythonPath, getBackendDir, getSitePackagesDir } = require('./server-manager')

const SETUP_MARKER = 'setup_v1.done'

/**
 * Скачать файл по URL
 */
function downloadFile(url, dest) {
  return new Promise((resolve, reject) => {
    const file = fs.createWriteStream(dest)
    https.get(url, (response) => {
      if (response.statusCode === 302 || response.statusCode === 301) {
        file.close()
        fs.unlinkSync(dest)
        downloadFile(response.headers.location, dest).then(resolve).catch(reject)
        return
      }
      response.pipe(file)
      file.on('finish', () => {
        file.close(resolve)
      })
    }).on('error', (err) => {
      fs.unlinkSync(dest)
      reject(err)
    })
  })
}

/**
 * Выполнить Python команду и вернуть Promise с прогрессом
 */
function runPython(args, cwd, env, onLine) {
  return new Promise((resolve, reject) => {
    const pythonPath = getPythonPath()
    const proc = spawn(pythonPath, args, {
      cwd,
      env,
      windowsHide: true,
    })

    proc.stdout.on('data', (data) => {
      data.toString().split('\n').forEach(line => {
        line = line.trim()
        if (line) onLine && onLine(line)
      })
    })

    proc.stderr.on('data', (data) => {
      data.toString().split('\n').forEach(line => {
        line = line.trim()
        if (line) onLine && onLine(line)
      })
    })

    proc.on('close', (code) => {
      if (code === 0) resolve()
      else reject(new Error(`Python процесс завершился с кодом ${code}`))
    })

    proc.on('error', reject)
  })
}

/**
 * Установить pip для embedded Python (только в продакшн)
 */
async function ensurePip(onProgress) {
  if (!app.isPackaged) return // В разработке pip уже есть

  const pythonDir = path.join(process.resourcesPath, 'python')
  const pipScript = path.join(pythonDir, 'get-pip.py')
  const pipExe = path.join(pythonDir, 'Scripts', 'pip.exe')

  if (fs.existsSync(pipExe)) return // pip уже установлен

  onProgress({ step: 'pip', text: 'Установка pip...', percent: 5 })

  // Скачать get-pip.py
  if (!fs.existsSync(pipScript)) {
    await downloadFile('https://bootstrap.pypa.io/get-pip.py', pipScript)
  }

  // Включить site-packages в embedded Python
  // В embedded Python нужно раскомментировать import site в python311._pth
  const pthFiles = fs.readdirSync(pythonDir).filter(f => f.endsWith('._pth'))
  for (const pth of pthFiles) {
    const pthPath = path.join(pythonDir, pth)
    let content = fs.readFileSync(pthPath, 'utf8')
    if (content.includes('#import site')) {
      content = content.replace('#import site', 'import site')
      fs.writeFileSync(pthPath, content)
    }
  }

  // Установить pip
  await runPython(
    [pipScript, '--no-warn-script-location'],
    pythonDir,
    { ...process.env, PYTHONHOME: pythonDir },
    (line) => onProgress({ step: 'pip', text: line, percent: 10 })
  )

  onProgress({ step: 'pip', text: 'pip установлен', percent: 15 })
}

/**
 * Установить Python зависимости
 */
async function installDependencies(onProgress) {
  const backendDir = getBackendDir()
  const sitePackages = getSitePackagesDir()
  const requirementsPath = path.join(backendDir, 'requirements.txt')

  if (!fs.existsSync(requirementsPath)) {
    throw new Error(`Файл requirements.txt не найден: ${requirementsPath}`)
  }

  // Создать директорию для пакетов
  fs.mkdirSync(sitePackages, { recursive: true })

  onProgress({ step: 'deps', text: 'Установка зависимостей Python...', percent: 20 })

  const pythonDir = app.isPackaged ? path.join(process.resourcesPath, 'python') : null
  const env = {
    ...process.env,
    ...(pythonDir && { PYTHONHOME: pythonDir }),
  }

  // Считаем пакеты для прогресса
  const requirements = fs.readFileSync(requirementsPath, 'utf8')
    .split('\n')
    .filter(l => l.trim() && !l.startsWith('#'))

  let installed = 0
  const total = requirements.length

  await runPython(
    [
      '-m', 'pip', 'install',
      '-r', requirementsPath,
      '--target', sitePackages,
      '--no-warn-script-location',
      '--disable-pip-version-check',
      '--quiet',
    ],
    backendDir,
    env,
    (line) => {
      if (line.startsWith('Successfully installed') || line.includes('Installing')) {
        installed++
        const percent = 20 + Math.round((installed / total) * 55)
        onProgress({ step: 'deps', text: line, percent: Math.min(percent, 75) })
      } else {
        onProgress({ step: 'deps', text: line, percent: null })
      }
    }
  )

  onProgress({ step: 'deps', text: 'Зависимости установлены', percent: 75 })
}

/**
 * Проверить нужна ли настройка (первый запуск)
 */
function isSetupRequired() {
  const markerPath = path.join(app.getPath('userData'), SETUP_MARKER)
  return !fs.existsSync(markerPath)
}

/**
 * Отметить настройку как выполненную
 */
function markSetupDone() {
  const markerPath = path.join(app.getPath('userData'), SETUP_MARKER)
  fs.writeFileSync(markerPath, new Date().toISOString())
}

/**
 * Сбросить настройку (для переустановки зависимостей)
 */
function resetSetup() {
  const markerPath = path.join(app.getPath('userData'), SETUP_MARKER)
  if (fs.existsSync(markerPath)) {
    fs.unlinkSync(markerPath)
  }
  const sitePackages = getSitePackagesDir()
  if (fs.existsSync(sitePackages)) {
    fs.rmdirSync(sitePackages, { recursive: true })
  }
}

/**
 * Полный процесс первоначальной настройки
 */
async function runSetup(onProgress) {
  try {
    // Шаг 1: Установить pip (если embeddable Python)
    await ensurePip(onProgress)

    // Шаг 2: Установить зависимости
    await installDependencies(onProgress)

    // Шаг 3: Отметить как выполнено
    markSetupDone()

    onProgress({ step: 'done', text: 'Настройка завершена', percent: 80 })
  } catch (error) {
    // Если не удалось установить — сбросить маркер
    const markerPath = path.join(app.getPath('userData'), SETUP_MARKER)
    if (fs.existsSync(markerPath)) fs.unlinkSync(markerPath)
    throw error
  }
}

module.exports = {
  isSetupRequired,
  runSetup,
  markSetupDone,
  resetSetup,
}
