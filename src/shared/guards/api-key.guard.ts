import {
  CanActivate,
  ExecutionContext,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { Reflector } from '@nestjs/core';
import { ConfigService } from '@nestjs/config';
import { PUBLIC_KEY } from './public.decorator';

@Injectable()
export class ApiKeyGuard implements CanActivate {
  private readonly validKeys: Set<string>;

  constructor(
    private readonly configService: ConfigService,
    private readonly reflector: Reflector,
  ) {
    const raw = this.configService.get<string>('API_KEYS', '');
    this.validKeys = new Set(
      raw
        .split(',')
        .map((k) => k.trim())
        .filter(Boolean),
    );
  }

  canActivate(context: ExecutionContext): boolean {
    // Skip auth if no API_KEYS configured (development mode)
    if (this.validKeys.size === 0) {
      return true;
    }

    // Skip auth for @Public() decorated handlers/controllers
    const isPublic = this.reflector.getAllAndOverride<boolean>(PUBLIC_KEY, [
      context.getHandler(),
      context.getClass(),
    ]);
    if (isPublic) {
      return true;
    }

    const request = context.switchToHttp().getRequest<{ headers: Record<string, string> }>();
    const apiKey = request.headers['x-api-key'];

    if (!apiKey || !this.validKeys.has(apiKey)) {
      throw new UnauthorizedException('API key invalida ou ausente');
    }

    return true;
  }
}
