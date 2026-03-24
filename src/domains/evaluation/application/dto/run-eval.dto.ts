import { IsOptional, IsString, Length } from 'class-validator';
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export class RunEvalDto {
  @ApiProperty({ description: 'ID do dataset a ser executado' })
  @IsString()
  datasetId!: string;

  @ApiPropertyOptional({ description: 'Identificador de quem disparou o eval (CI, usuário, etc.)' })
  @IsOptional()
  @IsString()
  @Length(1, 128)
  triggeredBy?: string;
}
