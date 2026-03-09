#!/usr/bin/env node
/**
 * Build-time domain validation — wraps audit-questions.js for CI/pre-commit use.
 * Exits 0 if all questions pass, 1 if any issues found.
 * Usage: node scripts/validate-domains.js
 */
import { execFileSync } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const auditScript = join(__dirname, 'audit-questions.js');

try {
  const output = execFileSync('node', [auditScript], { encoding: 'utf-8', stdio: 'pipe' });
  console.log(output);
  console.log('✓ Domain validation passed');
  process.exit(0);
} catch (err) {
  console.error(err.stdout || '');
  console.error(err.stderr || '');
  console.error('✗ Domain validation failed — fix issues above before committing');
  process.exit(1);
}
