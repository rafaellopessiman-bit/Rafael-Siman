/**
 * Jest globalTeardown — stops MongoMemoryServer started in globalSetup.
 * Cleans up the temp URI file.
 */
import * as fs from 'fs';
import * as path from 'path';

export default async function globalTeardown(): Promise<void> {
  const mongod = (globalThis as Record<string, unknown>).__MONGOD__ as
    | { stop: () => Promise<boolean> }
    | undefined;

  if (mongod) {
    await mongod.stop();
  }

  // Clean up temp file
  const uriFile = path.resolve(__dirname, '.test-mongo-uri');
  if (fs.existsSync(uriFile)) {
    fs.unlinkSync(uriFile);
  }
}
