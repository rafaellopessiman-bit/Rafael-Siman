# Retrospective Sprint 9 - Security Access Hardening

## Objetivo

Este documento promove o Sprint 9 para documentacao retrospectiva canonica.

O numero do sprint nao aparece nomeado no historico atual, mas a camada de seguranca e acesso ja instalada no repositorio e forte o suficiente para sustentar uma reconstrucao formal.

## Status do Documento

| Campo | Valor |
| --- | --- |
| Tipo | retrospectivo |
| Escopo | Sprint 9 |
| Base de evidencia | guard global, decorator publico, smoke auth, wiring do AppModule |
| Confianca global | alta |

## Objetivo retrospectivo

Introduzir controle de acesso minimo, coerente e operacional no runtime HTTP do `atlas_local`, sem bloquear endpoints publicos essenciais.

## Escopo normalizado

- `ApiKeyGuard` global
- rotas `@Public()`
- smoke de autenticacao
- encaixe com throttling e bootstrap da app

## Evidencias primarias

- [api-key.guard.ts](../../src/shared/guards/api-key.guard.ts) implementa validacao por `x-api-key`
- [public.decorator.ts](../../src/shared/guards/public.decorator.ts) define a marcacao de endpoints publicos
- [app.module.ts](../../src/app.module.ts) registra `ApiKeyGuard` globalmente
- [smoke-auth.e2e-spec.ts](../../test/smoke-auth.e2e-spec.ts) cobre rejeicao sem chave, aceitacao com chave valida e preservacao do endpoint publico de health

## Entregaveis observaveis hoje

- quando `API_KEYS` esta configurado, rotas protegidas exigem header `x-api-key`
- handlers e controllers podem escapar da autenticacao com `@Public()`
- o comportamento ja esta validado por smoke dedicado em [smoke-auth.e2e-spec.ts](../../test/smoke-auth.e2e-spec.ts)

## Delimitacao em relacao aos sprints vizinhos

- nao pertence ao Sprint 8 porque vai alem do hardening de surfaces e introduz uma fronteira clara de acesso
- antecede naturalmente o Sprint 10, que ja aparece explicitamente como production hardening em [smoke-s10.e2e-spec.ts](../../test/smoke-s10.e2e-spec.ts)

## Veredito

O Sprint 9 fica canonicamente definido como o sprint de **security access hardening**.

Ele nao possui artefato historico nomeado no repositorio atual, mas agora passa a ter documentacao explicita retrospectiva, sustentada por evidencia forte no codigo e nos testes.
