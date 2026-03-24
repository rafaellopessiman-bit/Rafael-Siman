import { IAgentDefinition } from '../interfaces/agent-definition.interface';

export const AGENT_DEFINITION_REPOSITORY = Symbol('AGENT_DEFINITION_REPOSITORY');

/**
 * Interface de repositorio para definicoes de agentes.
 *
 * Isola a camada de dominio da implementacao Mongoose.
 * O AgentRegistryService usa este repositorio para sincronizar
 * o cache in-memory com o estado persistido no MongoDB.
 */
export interface IAgentDefinitionRepository {
  /** Busca definicao pelo id logico (campo `id`, nao `_id`). */
  findById(id: string): Promise<IAgentDefinition | null>;

  /** Retorna todas as definicoes independente de estado. */
  findAll(): Promise<IAgentDefinition[]>;

  /** Retorna apenas definicoes com isActive=true. */
  findActive(): Promise<IAgentDefinition[]>;

  /**
   * Cria ou atualiza uma definicao pelo campo `id`.
   * Usa upsert para suportar idempotencia no bootstrap.
   */
  upsert(definition: IAgentDefinition): Promise<IAgentDefinition>;
}
