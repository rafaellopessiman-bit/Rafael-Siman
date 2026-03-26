import { Injectable, Inject } from '@nestjs/common';
import {
  CONVERSATION_REPOSITORY,
  IConversationRepository,
} from '../../domain/repositories/conversation.repository.interface';
import { CreateConversationDto, ConversationSummary } from '../dtos/agent.dto';
import {
  PaginationQueryDto,
  PaginatedResponseDto,
  paginate,
} from '../../../../shared/dto/pagination.dto';

@Injectable()
export class CreateConversationUseCase {
  constructor(
    @Inject(CONVERSATION_REPOSITORY)
    private readonly conversationRepo: IConversationRepository,
  ) {}

  async execute(dto: CreateConversationDto) {
    return this.conversationRepo.create({
      title: dto.title,
      systemPrompt: dto.systemPrompt,
    });
  }
}

@Injectable()
export class ListConversationsUseCase {
  constructor(
    @Inject(CONVERSATION_REPOSITORY)
    private readonly conversationRepo: IConversationRepository,
  ) {}

  async execute(
    query?: PaginationQueryDto,
  ): Promise<PaginatedResponseDto<ConversationSummary>> {
    const q = query ?? new PaginationQueryDto();
    const [docs, total] = await Promise.all([
      this.conversationRepo.findPaginated(q.skip, q.take, true),
      this.conversationRepo.countAll(true),
    ]);
    const items = docs.map((d) => ({
      id: d._id.toString(),
      title: d.title,
      messageCount: d.messageCount,
      totalTokens: d.totalTokens,
      isActive: d.isActive,
      createdAt: d.get('createdAt'),
      updatedAt: d.get('updatedAt'),
    }));
    return paginate(items, total, q);
  }
}

@Injectable()
export class GetConversationUseCase {
  constructor(
    @Inject(CONVERSATION_REPOSITORY)
    private readonly conversationRepo: IConversationRepository,
  ) {}

  async execute(id: string) {
    return this.conversationRepo.findById(id);
  }
}

@Injectable()
export class ArchiveConversationUseCase {
  constructor(
    @Inject(CONVERSATION_REPOSITORY)
    private readonly conversationRepo: IConversationRepository,
  ) {}

  async execute(id: string): Promise<void> {
    await this.conversationRepo.archive(id);
  }
}
