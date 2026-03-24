import { Module } from '@nestjs/common';
import {
  ConfigModule as NestConfigModule,
  ConfigService,
} from '@nestjs/config';
import { z } from 'zod';

const envSchema = z
  .object({
    NODE_ENV: z.enum(['development', 'production', 'test']).default('development'),
    PORT: z.coerce.number().optional(),
    APP_PORT: z.coerce.number().optional(),
    MONGODB_URI: z.string().url().startsWith('mongodb'),
    GROQ_API_KEY: z.string().optional(),
    GROQ_MODEL: z.string().default('llama-3.3-70b-versatile'),
    EMBEDDING_API_KEY: z.string().optional(),
    EMBEDDING_BASE_URL: z.string().url().default('https://api.openai.com/v1'),
    EMBEDDING_MODEL: z.string().default('text-embedding-3-small'),
    EMBEDDING_DIMENSIONS: z.coerce.number().int().positive().default(1536),
    ATLAS_VECTOR_SEARCH_ENABLED: z.string().default('false'),
    CORS_ORIGIN: z.string().optional().default('http://localhost:3000'),
    API_KEYS: z.string().optional().default(''),
  })
  .transform((env) => ({
    ...env,
    PORT: env.PORT ?? env.APP_PORT ?? 3000,
  }));

export type EnvConfig = z.infer<typeof envSchema>;

@Module({
  imports: [
    NestConfigModule.forRoot({
      isGlobal: true,
      validate: (config: Record<string, unknown>) => envSchema.parse(config),
    }),
  ],
  providers: [ConfigService],
  exports: [ConfigService],
})
export class ConfigModule {}
