import { Injectable } from '@nestjs/common';
import { IEvalCase } from '../interfaces/eval-case.interface';
import { IEvalScore } from '../interfaces/eval-score.interface';

const SCORE_WEIGHTS: Readonly<Record<keyof Omit<IEvalScore, 'overallScore'>, number>> = {
  faithfulness: 0.25,
  relevance: 0.20,
  completeness: 0.15,
  citationCoverage: 0.15,
  toolSuccess: 0.10,
  guardrailCompliance: 0.10,
  latencyBudget: 0.05,
};

@Injectable()
export class EvalEngineService {
  scoreCase(evalCase: IEvalCase): IEvalScore {
    const output = evalCase.actualOutput ?? '';
    const outputLower = output.toLowerCase();

    const faithfulness = this.scoreFaithfulness(outputLower, evalCase);
    const relevance = this.scoreRelevance(outputLower, evalCase);
    const completeness = this.scoreCompleteness(outputLower, evalCase);
    const citationCoverage = this.scoreCitationCoverage(outputLower, evalCase);
    const toolSuccess = this.scoreToolSuccess(evalCase);
    const guardrailCompliance = this.scoreGuardrailCompliance(outputLower, evalCase);
    const latencyBudget = this.scoreLatencyBudget(evalCase);

    const overallScore = this.weightedMean({
      faithfulness,
      relevance,
      completeness,
      citationCoverage,
      toolSuccess,
      guardrailCompliance,
      latencyBudget,
    });

    return {
      faithfulness,
      relevance,
      completeness,
      citationCoverage,
      toolSuccess,
      guardrailCompliance,
      latencyBudget,
      overallScore,
    };
  }

  aggregate(scores: IEvalScore[]): IEvalScore {
    if (scores.length === 0) {
      return {
        faithfulness: 0,
        relevance: 0,
        completeness: 0,
        citationCoverage: 0,
        toolSuccess: 0,
        guardrailCompliance: 0,
        latencyBudget: 0,
        overallScore: 0,
      };
    }

    const avg = (key: keyof IEvalScore): number =>
      scores.reduce((sum, s) => sum + (s[key] ?? 0), 0) / scores.length;

    const faithfulness = avg('faithfulness');
    const relevance = avg('relevance');
    const completeness = avg('completeness');
    const citationCoverage = avg('citationCoverage');
    const toolSuccess = avg('toolSuccess');
    const guardrailCompliance = avg('guardrailCompliance');
    const latencyBudget = avg('latencyBudget');
    const overallScore = avg('overallScore');

    return {
      faithfulness,
      relevance,
      completeness,
      citationCoverage,
      toolSuccess,
      guardrailCompliance,
      latencyBudget,
      overallScore,
    };
  }

  private scoreFaithfulness(outputLower: string, evalCase: IEvalCase): number {
    const forbidden = evalCase.forbiddenKeywords ?? [];
    if (forbidden.length === 0) return 1.0;
    const violations = forbidden.filter((kw) => outputLower.includes(kw.toLowerCase()));
    return violations.length === 0 ? 1.0 : Math.max(0, 1.0 - violations.length / forbidden.length);
  }

  private scoreRelevance(outputLower: string, evalCase: IEvalCase): number {
    const expected = evalCase.expectedKeywords ?? [];
    if (expected.length === 0) return outputLower.length > 0 ? 1.0 : 0.0;
    const found = expected.filter((kw) => outputLower.includes(kw.toLowerCase()));
    return found.length / expected.length;
  }

  private scoreCompleteness(outputLower: string, evalCase: IEvalCase): number {
    const expected = evalCase.expectedKeywords ?? [];
    if (expected.length === 0) return 1.0;
    const found = expected.filter((kw) => outputLower.includes(kw.toLowerCase()));
    return found.length / expected.length;
  }

  private scoreCitationCoverage(outputLower: string, evalCase: IEvalCase): number {
    if (!evalCase.requiresCitations) return 1.0;
    const citationPatterns = [/\[[\d,\s]+\]/, /\(fonte:/i, /\(source:/i, /\bfonte\b/i, /\bref\./i];
    const hasCitation = citationPatterns.some((p) => p.test(outputLower));
    return hasCitation ? 1.0 : 0.0;
  }

  private scoreToolSuccess(evalCase: IEvalCase): number {
    const expected = evalCase.expectedAgents ?? [];
    if (expected.length === 0) return 1.0;
    const actual = evalCase.actualAgents ?? [];
    const matched = expected.filter((a) => actual.includes(a));
    return matched.length / expected.length;
  }

  private scoreGuardrailCompliance(outputLower: string, evalCase: IEvalCase): number {
    const blocked = evalCase.forbiddenKeywords ?? [];
    if (blocked.length === 0) return 1.0;
    const violations = blocked.filter((kw) => outputLower.includes(kw.toLowerCase()));
    return violations.length === 0 ? 1.0 : 0.0;
  }

  private scoreLatencyBudget(evalCase: IEvalCase): number {
    if (!evalCase.latencyBudgetMs || !evalCase.actualLatencyMs) return 1.0;
    return evalCase.actualLatencyMs <= evalCase.latencyBudgetMs ? 1.0 : 0.0;
  }

  private weightedMean(
    scores: Omit<IEvalScore, 'overallScore'>,
  ): number {
    let total = 0;
    let weightSum = 0;
    for (const [key, weight] of Object.entries(SCORE_WEIGHTS) as [keyof typeof SCORE_WEIGHTS, number][]) {
      const val = scores[key];
      if (val !== null && val !== undefined) {
        total += val * weight;
        weightSum += weight;
      }
    }
    return weightSum > 0 ? Math.round((total / weightSum) * 1000) / 1000 : 0;
  }
}
