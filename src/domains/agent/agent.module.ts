import { Module } from '@nestjs/common';
import { MongooseModule } from '@nestjs/mongoose';

// Schemas
import {
  Conversation,
  ConversationSchema,
} from './infrastructure/persistence/conversation.schema';
import {
  PromptTemplate,
  PromptTemplateSchema,
} from './infrastructure/persistence/prompt-template.schema';
import {
  AgentRun,
  AgentRunSchema,
} from './infrastructure/persistence/agent-run.schema';
import {
  AgentStep,
  AgentStepSchema,
} from './infrastructure/persistence/agent-step.schema';
import {
  AgentDefinition,
  AgentDefinitionSchema,
} from './infrastructure/persistence/agent-definition.schema';
import {
  AgentMemory,
  AgentMemorySchema,
} from './infrastructure/persistence/agent-memory.schema';

// Repository interfaces + implementations
import { CONVERSATION_REPOSITORY } from './domain/repositories/conversation.repository.interface';
import { MongooseConversationRepository } from './infrastructure/persistence/conversation.repository';
import { PROMPT_TEMPLATE_REPOSITORY } from './domain/repositories/prompt-template.repository.interface';
import { MongoosePromptTemplateRepository } from './infrastructure/persistence/prompt-template.repository';
import { AGENT_RUN_REPOSITORY } from './domain/repositories/agent-run.repository.interface';
import { MongooseAgentRunRepository } from './infrastructure/persistence/agent-run.repository';
import { AGENT_STEP_REPOSITORY } from './domain/repositories/agent-step.repository.interface';
import { MongooseAgentStepRepository } from './infrastructure/persistence/agent-step.repository';
import { AGENT_DEFINITION_REPOSITORY } from './domain/repositories/agent-definition.repository.interface';
import { MongooseAgentDefinitionRepository } from './infrastructure/persistence/agent-definition.repository';
import { AGENT_MEMORY_REPOSITORY } from './domain/repositories/agent-memory.repository.interface';
import { MongooseAgentMemoryRepository } from './infrastructure/persistence/agent-memory.repository';

// Domain services
import { ToolRegistryService } from './domain/services/tool-registry.service';
import { AgentLoopService } from './domain/services/agent-loop.service';
import { TracingService } from './domain/services/tracing.service';
import { ContextManagerService } from './domain/services/context-manager.service';
import { GuardrailPipelineService } from './domain/services/guardrail-pipeline.service';
import { AgentRegistryService } from './domain/services/agent-registry.service';
import { HandoffManagerService } from './domain/services/handoff-manager.service';
import { ConversationMemoryService } from './domain/services/conversation-memory.service';
import { AgentOrchestratorService } from './domain/services/agent-orchestrator.service';

// Use cases
import { SendAgentMessageUseCase } from './application/use-cases/send-agent-message.use-case';
import {
  CreateConversationUseCase,
  ListConversationsUseCase,
  GetConversationUseCase,
  ArchiveConversationUseCase,
} from './application/use-cases/conversation.use-cases';
import {
  CreatePromptTemplateUseCase,
  ListPromptTemplatesUseCase,
  GetPromptTemplateUseCase,
  UpdatePromptTemplateUseCase,
  DeactivatePromptTemplateUseCase,
} from './application/use-cases/prompt-template.use-cases';
import { ExtractDocumentsUseCase } from './application/use-cases/extract-documents.use-case';
import { ExecuteGovernedActionUseCase } from './application/use-cases/execute-governed-action.use-case';

// Built-in tools
import { SearchDocumentsTool } from './infrastructure/tools/search-documents.tool';
import { ListSourcesTool } from './infrastructure/tools/list-sources.tool';
import { GetCachedAnswerTool } from './infrastructure/tools/get-cached-answer.tool';
import { GetDocumentByIdTool } from './infrastructure/tools/get-document-by-id.tool';
import { SummarizeSourcesTool } from './infrastructure/tools/summarize-sources.tool';
import { ExtractStructuredDataTool } from './infrastructure/tools/extract-structured-data.tool';
import { ExecuteWhitelistedActionTool } from './infrastructure/tools/execute-whitelisted-action.tool';

// Built-in guardrails
import { ContentFilterGuardrail } from './infrastructure/guardrails/content-filter.guardrail';
import { PiiDetectorGuardrail } from './infrastructure/guardrails/pii-detector.guardrail';
import { MaxTokensGuardrail } from './infrastructure/guardrails/max-tokens.guardrail';

// Controller
import { AgentController } from './infrastructure/http/agent.controller';
import { AskController } from './infrastructure/http/ask.controller';
import { ExtractController } from './infrastructure/http/extract.controller';
import { ActController } from './infrastructure/http/act.controller';

// Módulos externos
import { KnowledgeModule } from '../knowledge/knowledge.module';
import { LlmModule } from '../llm/llm.module';
import { ControlModule } from '../control/control.module';

@Module({
  imports: [
    MongooseModule.forFeature([
      { name: Conversation.name, schema: ConversationSchema },
      { name: PromptTemplate.name, schema: PromptTemplateSchema },
      { name: AgentRun.name, schema: AgentRunSchema },
      { name: AgentStep.name, schema: AgentStepSchema },
      { name: AgentDefinition.name, schema: AgentDefinitionSchema },
      { name: AgentMemory.name, schema: AgentMemorySchema },
    ]),
    KnowledgeModule,
    LlmModule,
    ControlModule,
  ],
  controllers: [AgentController, AskController, ExtractController, ActController],
  providers: [
    // Repositories
    {
      provide: CONVERSATION_REPOSITORY,
      useClass: MongooseConversationRepository,
    },
    {
      provide: PROMPT_TEMPLATE_REPOSITORY,
      useClass: MongoosePromptTemplateRepository,
    },
    {
      provide: AGENT_RUN_REPOSITORY,
      useClass: MongooseAgentRunRepository,
    },
    {
      provide: AGENT_STEP_REPOSITORY,
      useClass: MongooseAgentStepRepository,
    },
    {
      provide: AGENT_DEFINITION_REPOSITORY,
      useClass: MongooseAgentDefinitionRepository,
    },
    {
      provide: AGENT_MEMORY_REPOSITORY,
      useClass: MongooseAgentMemoryRepository,
    },
    // Domain services
    ToolRegistryService,
    AgentLoopService,
    TracingService,
    ContextManagerService,
    GuardrailPipelineService,
    AgentRegistryService,
    HandoffManagerService,
    ConversationMemoryService,
    AgentOrchestratorService,
    // Use cases
    SendAgentMessageUseCase,
    CreateConversationUseCase,
    ListConversationsUseCase,
    GetConversationUseCase,
    ArchiveConversationUseCase,
    CreatePromptTemplateUseCase,
    ListPromptTemplatesUseCase,
    GetPromptTemplateUseCase,
    UpdatePromptTemplateUseCase,
    DeactivatePromptTemplateUseCase,
    ExtractDocumentsUseCase,
    ExecuteGovernedActionUseCase,
    // Built-in tools (auto-registram via onModuleInit)
    SearchDocumentsTool,
    ListSourcesTool,
    GetCachedAnswerTool,
    GetDocumentByIdTool,
    SummarizeSourcesTool,
    ExtractStructuredDataTool,
    ExecuteWhitelistedActionTool,
    // Built-in guardrails (auto-registram via onModuleInit)
    ContentFilterGuardrail,
    PiiDetectorGuardrail,
    MaxTokensGuardrail,
  ],
  exports: [
    ToolRegistryService,
    AgentLoopService,
    TracingService,
    GuardrailPipelineService,
    AgentRegistryService,
    HandoffManagerService,
    ConversationMemoryService,
    AgentOrchestratorService,
  ],
})
export class AgentModule {}
