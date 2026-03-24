import { Injectable, Inject, Logger, OnModuleInit } from '@nestjs/common';
import { IAgentDefinition } from '../interfaces/agent-definition.interface';
import {
  AGENT_DEFINITION_REPOSITORY,
  IAgentDefinitionRepository,
} from '../repositories/agent-definition.repository.interface';
import { DEFAULT_AGENT_DEFINITIONS } from '../../infrastructure/registry/default-agent-definitions';

/**
 * Registry central de agentes do runtime multiagente.
 *
 * Responsabilidades:
 * - Carrega definicoes ativas do MongoDB no startup (OnModuleInit)
 * - Garante que os agentes default existem via upsert idempotente
 * - Mantem cache in-memory para consultas rapidas durante execucao
 * - Valida permissoes de tool (whitelist enforcement)
 *
 * Analogo ao ToolRegistryService, mas para agentes.
 */
@Injectable()
export class AgentRegistryService implements OnModuleInit {
  private readonly logger = new Logger(AgentRegistryService.name);
  private readonly cache = new Map<string, IAgentDefinition>();

  constructor(
    @Inject(AGENT_DEFINITION_REPOSITORY)
    private readonly repo: IAgentDefinitionRepository,
  ) {}

  async onModuleInit(): Promise<void> {
    await this.seedDefaultDefinitions();
    await this.refreshCache();
    this.logger.log(
      `AgentRegistry inicializado com ${this.cache.size} agentes ativos`,
    );
  }

  /** Retorna definicao de agente pelo ID logico. Null se nao encontrado. */
  get(agentId: string): IAgentDefinition | null {
    return this.cache.get(agentId) ?? null;
  }

  /** Retorna todos os agentes no cache. */
  getAll(): IAgentDefinition[] {
    return [...this.cache.values()];
  }

  /** Retorna apenas agentes com isActive=true. */
  getActive(): IAgentDefinition[] {
    return this.getAll().filter((a) => a.isActive);
  }

  /**
   * Valida se um agente tem permissao para usar uma tool especifica.
   *
   * Aplicado pelo AgentOrchestratorService antes de passar o ToolRegistry
   * para o AgentLoopService do agente especialista.
   */
  isToolAllowed(agentId: string, toolName: string): boolean {
    const definition = this.cache.get(agentId);
    if (!definition) return false;
    // Supervisor tem acesso a todas as suas tools declaradas
    return definition.allowedTools.includes(toolName);
  }

  /**
   * Valida se um agente pode fazer handoff para outro agente.
   * Usado pelo HandoffManagerService para garantir governanca.
   */
  isHandoffAllowed(fromAgentId: string, toAgentId: string): boolean {
    const definition = this.cache.get(fromAgentId);
    if (!definition) return false;
    return definition.handoffTargets.includes(toAgentId);
  }

  /**
   * Registra ou atualiza uma definicao no cache e persiste no MongoDB.
   * Util para atualizacoes em runtime sem reiniciar o servidor.
   */
  async register(definition: IAgentDefinition): Promise<void> {
    await this.repo.upsert(definition);
    this.cache.set(definition.id, definition);
    this.logger.log(`Agente registrado/atualizado: ${definition.id} v${definition.version}`);
  }

  /** Forca recarga do cache a partir do MongoDB. */
  async refreshCache(): Promise<void> {
    const active = await this.repo.findActive();
    this.cache.clear();
    for (const def of active) {
      this.cache.set(def.id, def);
    }
  }

  private async seedDefaultDefinitions(): Promise<void> {
    for (const def of DEFAULT_AGENT_DEFINITIONS) {
      await this.repo.upsert(def);
    }
    this.logger.log(
      `${DEFAULT_AGENT_DEFINITIONS.length} definicoes default garantidas no MongoDB`,
    );
  }
}
