/**
 * Runs a command with the backend virtualenv's python.
 * The venv layout differs per OS (Windows: .venv/Scripts, POSIX: .venv/bin),
 * so the path is resolved here instead of being hardcoded in package.json.
 */
import { spawn } from 'node:child_process'
import { existsSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const backend = join(root, 'backend')
const isWindows = process.platform === 'win32'
const venvPython = join(backend, '.venv', isWindows ? 'Scripts' : 'bin', isWindows ? 'python.exe' : 'python')

if (!existsSync(venvPython)) {
  console.error(
    `Backend virtualenv not found at ${venvPython}.\n` +
      `Create it with:\n  cd backend\n  python -m venv .venv\n  .venv/${isWindows ? 'Scripts' : 'bin'}/python -m pip install -r requirements.txt`,
  )
  process.exit(1)
}

const tasks = {
  '--pytest': ['-m', 'pytest', '-q'],
  '--seed': ['-m', 'app.seed', '--reset'],
  '--simulate': ['-m', 'app.seed', '--reset', '--simulate', '500'],
}
const args = tasks[process.argv[2]] ?? ['-m', 'uvicorn', 'app.main:app', '--reload', '--port', '8000']

const child = spawn(venvPython, args, { cwd: backend, stdio: 'inherit' })
child.on('exit', (code, signal) => {
  if (signal) process.kill(process.pid, signal)
  else process.exit(code ?? 0)
})
