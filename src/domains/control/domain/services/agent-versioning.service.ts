import { Injectable } from '@nestjs/common';
import { InjectModel } from '@nestjs/mongoose';
import { Model } from 'mongoose';
import {
  AgentDefinition,
  AgentDefinitionDocument,
} from '../../../agent/infrastructure/persistence/agent-definition.schema';
import { IAgentDefinition } from '../../../agent/domain/interfaces/agent-definition.interface';

/**
 * Serviço de versionamento de AgentDefinition.
 *
 * Mantém o histórico de versões lidas do MongoDB,
 * valida bumps semânticos e compara snapshots de definições.
 *
 * A persistência de histórico não cria nova collection — reutiliza
 * `agent_definitions` com query por version field, evitando duplicação.
 */
@Injectable()
export class AgentVersioningService {
  constructor(
    @InjectModel(AgentDefinition.name)
    private readonly model: Model<AgentDefinitionDocument>,
  ) {}

  /**
   * Retorna todas as versões disponíveis de um agente no MongoDB.
   * Cada chamada a upsert() do AgentRegistryService substitui a definição,
   * então este método retorna a versão atual registrada.
   */
  async getVersionHistory(agentId: string): Promise<Array<{ version: string; updatedAt: Date }>> {
    const docs = await this.model
      .find({ id: agentId })
      .sort({ updatedAt: -1 })
      .select({ version: 1, updatedAt: 1, _id: 0 })
      .lean();

    return docs.map((d) => ({
      version: (d as unknown as { version: string; updatedAt: Date }).version,
      updatedAt: (d as unknown as { version: string; updatedAt: Date }).updatedAt,
    }));
  }

  /**
   * Valida se um bump de versão semântica é válido.
   * Regras:
   * - Major/minor/patch devem ser inteiros não-negativos.
   * - A nova versão deve ser maior que a atual (comparação semântica).
   */
  validateVersionBump(currentVersion: string, newVersion: string): boolean {
    const parse = (v: string) => v.split('.').map(Number);
    const [cMaj, cMin, cPat] = parse(currentVersion);
    const [nMaj, nMin, nPat] = parse(newVersion);

    if ([nMaj, nMin, nPat].some((n) => isNaN(n) || n < 0)) return false;

    if (nMaj > cMaj) return true;
    if (nMaj === cMaj && nMin > cMin) return true;
    if (nMaj === cMaj && nMin === cMin && nPat > cPat) return true;
    return false;
  }

  /**
   * Compara dois snapshots de definições e retorna as diferenças.
   */
  diffDefinitions(
    prev: IAgentDefinition,
    next: IAgentDefinition,
  ): Record<string, { from: unknown; to: unknown }> {
    const diff: Record<string, { from: unknown; to: unknown }> = {};
    const keys = new Set([...Object.keys(prev), ...Object.keys(next)]) as Set<keyof IAgentDefinition>;

    for (const key of keys) {
      const prevVal = JSON.stringify(prev[key]);
      const nextVal = JSON.stringify(next[key]);
      if (prevVal !== nextVal) {
        diff[key] = { from: prev[key], to: next[key] };
      }
    }
    return diff;
  }

  /**
   * Lista todos os agentes com suas versões atuais.
   */
  async listAll(): Promise<Array<{ id: string; name: string; version: string; isActive: boolean }>> {
    const docs = await this.model
      .find()
      .select({ id: 1, name: 1, version: 1, isActive: 1, _id: 0 })
      .lean();

    return docs.map((d) => ({
      id: (d as unknown as { id: string }).id,
      name: (d as unknown as { name: string }).name,
      version: (d as unknown as { version: string }).version,
      isActive: (d as unknown as { isActive: boolean }).isActive,
    }));
  }
}
