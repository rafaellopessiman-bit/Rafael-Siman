import { NestFactory } from '@nestjs/core';
import { Logger, ValidationPipe } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { SwaggerModule, DocumentBuilder } from '@nestjs/swagger';
import helmet from 'helmet';
import { AppModule } from './app.module';
import { AllExceptionsFilter } from './shared/filters/all-exceptions.filter';
import { LoggingInterceptor } from './shared/interceptors/logging.interceptor';

async function bootstrap() {
  const logger = new Logger('Bootstrap');
  const app = await NestFactory.create(AppModule, { bufferLogs: true });
  const configService = app.get(ConfigService);

  // Security headers
  app.use(helmet());
  app.enableCors({
    origin: configService.get<string>('CORS_ORIGIN', 'http://localhost:3000'),
    credentials: true,
  });

  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
    }),
  );
  app.useGlobalFilters(new AllExceptionsFilter());
  app.useGlobalInterceptors(new LoggingInterceptor());

  const swagger = new DocumentBuilder()
    .setTitle('Atlas Local API')
    .setDescription('Sistema de inteligência documental — RAG + MongoDB Atlas Local')
    .setVersion('1.0')
    .addTag('knowledge', 'Indexação e busca de documentos')
    .addTag('llm', 'RAG — perguntas sobre documentos indexados')
    .addTag('planner', 'Índice de estado dos documentos')
    .addTag('tabular', 'Consultas SQL em dados tabulares')
    .addTag('agent', 'Agente IA com memória conversacional, tools e loop ReAct')
    .build();
  SwaggerModule.setup('api', app, SwaggerModule.createDocument(app, swagger));

  const port = configService.get<number>('PORT', 3000);
  const env = configService.get<string>('NODE_ENV', 'development');

  await app.listen(port);
  logger.log(`Atlas Local API rodando em http://localhost:${port} [${env}]`);
  logger.log(`Swagger disponível em http://localhost:${port}/api`);
}
bootstrap();
