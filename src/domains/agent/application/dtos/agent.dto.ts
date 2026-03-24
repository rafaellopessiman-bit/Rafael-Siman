import {
  IsString,
  IsOptional,
  MinLength,
  MaxLength,
} from 'class-validator';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export class CreateConversationDto {
  @ApiProperty({ description: 'Título da conversa', minLength: 1 })
  @IsString()
  @MinLength(1)
  @MaxLength(200)
  title!: string;

  @ApiPropertyOptional({
    description: 'Slug de um prompt template, ou system prompt literal',
  })
  @IsOptional()
  @IsString()
  systemPrompt?: string;
}

export class SendMessageDto {
  @ApiProperty({
    description: 'Mensagem do usuário em linguagem natural',
    minLength: 1,
  })
  @IsString()
  @MinLength(1)
  message!: string;
}

export class CreatePromptTemplateDto {
  @ApiProperty({ description: 'Slug único (ex: "rag-default")' })
  @IsString()
  @MinLength(2)
  @MaxLength(64)
  slug!: string;

  @ApiProperty({ description: 'Nome legível do template' })
  @IsString()
  @MinLength(2)
  name!: string;

  @ApiProperty({ description: 'Conteúdo do system prompt' })
  @IsString()
  @MinLength(10)
  content!: string;

  @ApiPropertyOptional({ description: 'Descrição do propósito do template' })
  @IsOptional()
  @IsString()
  description?: string;
}

export class UpdatePromptTemplateDto {
  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  @MinLength(2)
  name?: string;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  @MinLength(10)
  content?: string;

  @ApiPropertyOptional()
  @IsOptional()
  @IsString()
  description?: string;
}

export interface AgentResponse {
  conversationId: string;
  answer: string;
  runId?: string;
  toolsUsed: string[];
  iterations: number;
  totalTokens: number;
  latencyMs: number;
}

export interface ConversationSummary {
  id: string;
  title: string;
  messageCount: number;
  totalTokens: number;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}
