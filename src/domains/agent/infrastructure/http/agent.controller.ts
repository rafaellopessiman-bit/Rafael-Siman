import {
  Controller,
  Post,
  Get,
  Put,
  Delete,
  Body,
  Param,
  Query,
  NotFoundException,
} from '@nestjs/common';
import { ApiTags, ApiOperation } from '@nestjs/swagger';
import {
  CreateConversationDto,
  SendMessageDto,
  CreatePromptTemplateDto,
  UpdatePromptTemplateDto,
} from '../../application/dtos/agent.dto';
import { SendAgentMessageUseCase } from '../../application/use-cases/send-agent-message.use-case';
import {
  CreateConversationUseCase,
  ListConversationsUseCase,
  GetConversationUseCase,
  ArchiveConversationUseCase,
} from '../../application/use-cases/conversation.use-cases';
import {
  CreatePromptTemplateUseCase,
  ListPromptTemplatesUseCase,
  GetPromptTemplateUseCase,
  UpdatePromptTemplateUseCase,
  DeactivatePromptTemplateUseCase,
} from '../../application/use-cases/prompt-template.use-cases';
import { ToolRegistryService } from '../../domain/services/tool-registry.service';
import { TracingService } from '../../domain/services/tracing.service';
import { GuardrailPipelineService } from '../../domain/services/guardrail-pipeline.service';
import { AgentRegistryService } from '../../domain/services/agent-registry.service';
import { AgentOrchestratorService } from '../../domain/services/agent-orchestrator.service';

@ApiTags('agent')
@Controller('agent')
export class AgentController {
  constructor(
    private readonly sendMessage: SendAgentMessageUseCase,
    private readonly createConversation: CreateConversationUseCase,
    private readonly listConversations: ListConversationsUseCase,
    private readonly getConversation: GetConversationUseCase,
    private readonly archiveConversation: ArchiveConversationUseCase,
    private readonly createTemplate: CreatePromptTemplateUseCase,
    private readonly listTemplates: ListPromptTemplatesUseCase,
    private readonly getTemplate: GetPromptTemplateUseCase,
    private readonly updateTemplate: UpdatePromptTemplateUseCase,
    private readonly deactivateTemplate: DeactivatePromptTemplateUseCase,
    private readonly toolRegistry: ToolRegistryService,
    private readonly tracingService: TracingService,
    private readonly guardrailPipeline: GuardrailPipelineService,
    private readonly agentRegistry: AgentRegistryService,
    private readonly orchestrator: AgentOrchestratorService,
  ) {}

  // ── Conversations ────────────────────────────────────────────────────

  @Post('conversations')
  @ApiOperation({ summary: 'Cria uma nova conversa com o agente' })
  create(@Body() dto: CreateConversationDto) {
    return this.createConversation.execute(dto);
  }

  @Get('conversations')
  @ApiOperation({ summary: 'Lista conversas ativas' })
  list() {
    return this.listConversations.execute();
  }

  @Get('conversations/:id')
  @ApiOperation({ summary: 'Recupera conversa com histórico completo' })
  async get(@Param('id') id: string) {
    const conversation = await this.getConversation.execute(id);
    if (!conversation) {
      throw new NotFoundException(`Conversa "${id}" não encontrada`);
    }
    return conversation;
  }

  @Post('conversations/:id/messages')
  @ApiOperation({
    summary: 'Envia mensagem e executa loop do agente (ReAct + tools)',
  })
  send(@Param('id') id: string, @Body() dto: SendMessageDto) {
    return this.sendMessage.execute(id, dto);
  }

  @Delete('conversations/:id')
  @ApiOperation({ summary: 'Arquiva conversa (soft delete)' })
  async archive(@Param('id') id: string) {
    await this.archiveConversation.execute(id);
    return { archived: true };
  }

  // ── Prompt Templates ─────────────────────────────────────────────────

  @Post('prompts')
  @ApiOperation({ summary: 'Cria um novo template de system prompt' })
  createPrompt(@Body() dto: CreatePromptTemplateDto) {
    return this.createTemplate.execute(dto);
  }

  @Get('prompts')
  @ApiOperation({ summary: 'Lista todos os templates de prompt ativos' })
  listPrompts() {
    return this.listTemplates.execute();
  }

  @Get('prompts/:slug')
  @ApiOperation({ summary: 'Recupera template pelo slug' })
  getPrompt(@Param('slug') slug: string) {
    return this.getTemplate.execute(slug);
  }

  @Put('prompts/:slug')
  @ApiOperation({ summary: 'Atualiza template de prompt' })
  updatePrompt(
    @Param('slug') slug: string,
    @Body() dto: UpdatePromptTemplateDto,
  ) {
    return this.updateTemplate.execute(slug, dto);
  }

  @Delete('prompts/:slug')
  @ApiOperation({ summary: 'Desativa template de prompt (soft delete)' })
  async deactivatePrompt(@Param('slug') slug: string) {
    await this.deactivateTemplate.execute(slug);
    return { deactivated: true };
  }

  // ── Tools ────────────────────────────────────────────────────────────

  @Get('tools')
  @ApiOperation({ summary: 'Lista ferramentas disponíveis para o agente' })
  listTools() {
    return this.toolRegistry.getAll().map((t) => ({
      name: t.name,
      description: t.description,
      parameters: t.parameters,
    }));
  }

  // ── Tracing ──────────────────────────────────────────────────────────

  @Get('runs')
  @ApiOperation({ summary: 'Lista execuções recentes do agente' })
  listRuns(@Query('limit') limit?: string) {
    return this.tracingService.getRecentRuns(
      limit ? Math.min(Math.max(parseInt(limit, 10) || 20, 1), 100) : 20,
    );
  }

  @Get('runs/:runId')
  @ApiOperation({ summary: 'Recupera detalhes de uma execução do agente' })
  async getRun(@Param('runId') runId: string) {
    const run = await this.tracingService.getRun(runId);
    if (!run) {
      throw new NotFoundException(`Run "${runId}" não encontrado`);
    }
    return run;
  }

  @Get('runs/:runId/steps')
  @ApiOperation({ summary: 'Lista steps de uma execução do agente' })
  getRunSteps(@Param('runId') runId: string) {
    return this.tracingService.getSteps(runId);
  }

  @Get('conversations/:id/runs')
  @ApiOperation({ summary: 'Lista execuções de uma conversa' })
  getConversationRuns(
    @Param('id') conversationId: string,
    @Query('limit') limit?: string,
  ) {
    return this.tracingService.getRunsByConversation(
      conversationId,
      limit ? Math.min(Math.max(parseInt(limit, 10) || 20, 1), 100) : 20,
    );
  }

  // ── Guardrails ───────────────────────────────────────────────────────

  @Get('guardrails')
  @ApiOperation({ summary: 'Lista guardrails ativos' })
  listGuardrails() {
    return this.guardrailPipeline.listGuardrails();
  }

  // ── Agent Registry (Sprint 5) ────────────────────────────────────────

  @Get('registry')
  @ApiOperation({ summary: 'Lista todos os agentes ativos no registry' })
  listAgents() {
    return this.agentRegistry.getActive().map((agent) => ({
      id: agent.id,
      name: agent.name,
      description: agent.description,
      version: agent.version,
      capabilities: agent.capabilities,
      allowedTools: agent.allowedTools,
      handoffTargets: agent.handoffTargets,
      isActive: agent.isActive,
    }));
  }

  @Get('registry/:agentId')
  @ApiOperation({ summary: 'Recupera detalhes de um agente no registry' })
  getAgent(@Param('agentId') agentId: string) {
    const agent = this.agentRegistry.get(agentId);
    if (!agent) {
      throw new NotFoundException(`Agente "${agentId}" não encontrado no registry`);
    }
    return agent;
  }

  // ── Orchestrator (Sprint 5) ──────────────────────────────────────────

  @Post('conversations/:id/orchestrate')
  @ApiOperation({
    summary: 'Envia mensagem com orquestração multiagente (supervisor + especialistas)',
  })
  async orchestrate(@Param('id') id: string, @Body() dto: SendMessageDto) {
    const conversation = await this.getConversation.execute(id);
    if (!conversation) {
      throw new NotFoundException(`Conversa "${id}" não encontrada`);
    }

    // Converte histórico para GroqMessage[]
    const messages = [
      ...(conversation as any).messages?.map((m: any) => ({
        role: m.role as 'user' | 'assistant',
        content: m.content,
      })) ?? [],
      { role: 'user' as const, content: dto.message },
    ];

    return this.orchestrator.orchestrate(messages, {
      conversationId: id,
      triggeredBy: 'api',
    });
  }
}
