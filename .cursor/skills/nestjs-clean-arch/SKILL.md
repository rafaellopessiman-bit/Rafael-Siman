---
name: nestjs-clean-arch
description: >
  Fornece a estrutura feature-based de Clean Architecture para NestJS v11 com MongoDB
  Atlas Local. Use ao criar módulos NestJS, features ou reorganizar domínios.
paths: "**/*.ts"
---

# NestJS Clean Architecture — atlas_local

## Estrutura padrão recomendada (Feature-based Clean Architecture)

```text
src/
├── domains/                  # Uma pasta por feature (user, post, etc.)
│   ├── user/
│   │   ├── application/      # Use Cases, Commands, Queries
│   │   ├── domain/           # Entidades puras
│   │   └── infrastructure/   # Repositories + Mongoose schemas
├── infrastructure/           # Configurações globais e persistência
│   └── persistence/
│       └── mongoose/
├── presentation/             # Controllers, DTOs, Pipes
├── shared/                   # Módulos reutilizáveis
└── main.ts
```

## Regras obrigatórias

- Um module por feature (`user.module.ts`).
- Repository Pattern customizado.
- CQRS leve com `@nestjs/cqrs` apenas quando necessário.
- Camadas internas nunca dependem de camadas externas.
- Sempre use `MongooseModule.forFeature()` no module.

## Exemplo de Module completo

```ts
@Module({
  imports: [
    MongooseModule.forFeature([{ name: User.name, schema: UserSchema }]),
  ],
  controllers: [UserController],
  providers: [UserService, UserRepository],
})
export class UserModule {}
```
