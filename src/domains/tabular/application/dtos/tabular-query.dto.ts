import { IsString, MinLength } from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

export class TabularQueryDto {
  @ApiProperty({ description: 'SQL SELECT query para execução tabular', minLength: 7 })
  @IsString()
  @MinLength(7)
  sql!: string;
}
