/**
 * Jest globalSetup — starts MongoMemoryServer ONCE for the entire test suite.
 * Writes the URI to a temp file so test workers can read it via setupFiles.
 * Stores the MMS instance on globalThis for teardown.
 */
import { MongoMemoryServer } from 'mongodb-memory-server';
import * as fs from 'fs';
import * as path from 'path';

export default async function globalSetup(): Promise<void> {
  const mongod = await MongoMemoryServer.create();
  const uri = mongod.getUri();

  // Write URI to file — test workers read this in setup-env.ts
  fs.writeFileSync(
    path.resolve(__dirname, '.test-mongo-uri'),
    uri,
    'utf-8',
  );

  // Store instance for globalTeardown (same context)
  (globalThis as Record<string, unknown>).__MONGOD__ = mongod;
}
