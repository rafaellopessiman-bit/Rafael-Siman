/**
 * Minimal e2e test to validate MongoMemoryServer + NestJS compilation via globalSetup.
 */
import { Test } from '@nestjs/testing';
import { AppModule } from '../src/app.module';

describe('Minimal compile test', () => {
  it('should compile AppModule with MongoMemoryServer from globalSetup', async () => {
    console.log('[MINIMAL] process.env.MONGODB_URI =', process.env.MONGODB_URI);

    const moduleFixture = await Test.createTestingModule({
      imports: [AppModule],
    }).compile();

    console.log('[MINIMAL] Compiled! Closing...');
    await moduleFixture.close();
    console.log('[MINIMAL] Done.');
  }, 30_000);
});
