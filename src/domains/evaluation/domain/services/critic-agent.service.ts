import { Injectable } from '@nestjs/common';
import { IEvalCase } from '../interfaces/eval-case.interface';

export interface CritiqueResult {
  approved: boolean;
  reason: string;
  violations: string[];
}

@Injectable()
export class CriticAgentService {
  critique(draft: string, evalCase: IEvalCase): CritiqueResult {
    const violations: string[] = [];
    const draftLower = draft.toLowerCase();

    // Check forbidden keywords
    for (const kw of evalCase.forbiddenKeywords ?? []) {
      if (draftLower.includes(kw.toLowerCase())) {
        violations.push(`Forbidden keyword detected: "${kw}"`);
      }
    }

    // Check citation requirement
    if (evalCase.requiresCitations) {
      const citationPatterns = [/\[[\d,\s]+\]/, /\(fonte:/i, /\(source:/i, /\bfonte\b/i, /\bref\./i];
      const hasCitation = citationPatterns.some((p) => p.test(draft));
      if (!hasCitation) {
        violations.push('Response requires citations but none were found');
      }
    }

    // Check minimum content — reject empty or too-short drafts
    if (draft.trim().length < 10) {
      violations.push('Response is too short or empty');
    }

    const approved = violations.length === 0;
    const reason = approved
      ? 'Draft approved: all quality criteria met'
      : `Draft rejected: ${violations.join('; ')}`;

    return { approved, reason, violations };
  }

  critiqueWithScore(
    draft: string,
    evalCase: IEvalCase,
  ): CritiqueResult & { confidenceScore: number } {
    const base = this.critique(draft, evalCase);
    const totalChecks = 1 + (evalCase.requiresCitations ? 1 : 0) + (evalCase.forbiddenKeywords?.length ?? 0);
    const passedChecks = totalChecks - base.violations.length;
    const confidenceScore = Math.round((passedChecks / totalChecks) * 100) / 100;
    return { ...base, confidenceScore };
  }
}
