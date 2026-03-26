import { Module } from '@nestjs/common';
import { AskCacheService } from './ask-cache.service';

@Module({
  providers: [AskCacheService],
  exports: [AskCacheService],
})
export class CacheModule {}
