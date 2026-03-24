// ── Test environment setup ──────────────────────────────────────────────────
// Executed BEFORE any test file imports (via jest setupFiles).
// Reads the MongoMemoryServer URI written by globalSetup.
// This ensures NestJS ConfigModule picks up the real URI at import time.
// ────────────────────────────────────────────────────────────────────────────
import * as fs from 'fs';
import * as path from 'path';

const uriFile = path.resolve(__dirname, '.test-mongo-uri');
if (fs.existsSync(uriFile)) {
  process.env.MONGODB_URI = fs.readFileSync(uriFile, 'utf-8').trim();
}

process.env.NODE_ENV = 'test';
