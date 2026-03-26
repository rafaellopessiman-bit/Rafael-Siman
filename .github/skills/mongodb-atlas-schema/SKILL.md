---
name: mongodb-atlas-schema
description: Templates e melhores práticas de schema design para MongoDB Atlas Local + @nestjs/mongoose
---

**Regras de Schema Design (sempre siga)**

1. Identifique entidades e relacionamentos.
2. Entenda o workload completo.
3. Escolha o padrão correto: Embedding | Referencing | Hybrid | Outbox | Versioning.
4. Adicione índices necessários (compound, text, vector).
5. Use versionamento (`versionKey: 'version'`).

**Template pronto (Hybrid – mais usado)**

```ts
@Schema({ timestamps: true, versionKey: 'version' })
export class Post {
  @Prop({ required: true, index: true })
  title: string;

  @Prop({ type: String, index: 'text' })
  content: string;

  @Prop({ type: Schema.Types.ObjectId, ref: 'User', index: true })
  author: string;

  @Prop({ type: Object })
  authorSnapshot: { name: string; email: string };
}
```

**Índices recomendados**

- Compound: `{ email: 1, createdAt: -1 }`
- Text: para Atlas Search
- Vector: quando usar embeddings

**Comando útil no terminal**

```bash
mongosh "mongodb://admin:password@localhost:27017"
```

Essa skill é carregada automaticamente pelo NestJS Atlas Architect.

---

## Anti-Padrões Proibidos

- ❌ Arrays ilimitados em um único documento (use referenciação quando > 100 itens)
- ❌ Datas como strings ISO — use sempre `datetime` UTC
- ❌ Enums como inteiros — use `string` lowercase
- ❌ Índices sem `name` explícito
- ❌ `os.environ` diretamente — use `get_settings()` de `src/config.py`
- ❌ `print()` nos módulos — use `src/core/output.py`
- ❌ Exceções genéricas — use `src/exceptions.py`
