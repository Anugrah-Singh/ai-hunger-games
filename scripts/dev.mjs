import { spawn } from 'node:child_process';

const npmCommand = process.platform === 'win32' ? 'npm.cmd' : 'npm';
const children = [
  spawn(npmCommand, ['run', 'dev:api'], { stdio: 'inherit' }),
  spawn(npmCommand, ['run', 'dev:web'], { stdio: 'inherit' }),
];

let shuttingDown = false;

function stop(exitCode = 0) {
  if (shuttingDown) return;
  shuttingDown = true;
  for (const child of children) child.kill('SIGTERM');
  process.exitCode = exitCode;
}

for (const child of children) {
  child.once('exit', (code, signal) => {
    if (!shuttingDown && (code !== 0 || signal)) stop(code ?? 1);
  });
  child.once('error', () => stop(1));
}

process.once('SIGINT', () => stop(0));
process.once('SIGTERM', () => stop(0));
