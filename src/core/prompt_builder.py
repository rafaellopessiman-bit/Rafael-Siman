from typing import Any


def build_knowledge_prompt(question: str, documents: list[dict[str, Any]]) -> str:
    context_blocks = []

    for index, document in enumerate(documents, start=1):
        raw_content = str(document.get("content", "")).strip()
        normalized_content = " ".join(raw_content.split())
        truncated_content = normalized_content[:1500]

        context_blocks.append(
            "\n".join(
                [
                    f"[Fonte {index}]",
                    f"Arquivo: {document.get('file_name', '')}",
                    f"Caminho: {document.get('file_path', '')}",
                    f"Score: {document.get('score', 0.0)}",
                    f"Conteúdo recuperado: {truncated_content}",
                ]
            )
        )

    context_text = "\n\n".join(context_blocks)

    return f"""Você deve responder usando apenas o contexto fornecido.
Se o contexto não for suficiente, diga isso explicitamente.
Não invente fatos.

Pergunta:
{question}

Contexto:
{context_text}

Instruções de resposta:
- responda em português
- seja técnico e objetivo
- use apenas as informações do contexto
- cite os arquivos usados na resposta
"""


def build_plan_prompt(objective: str) -> str:
    return f"""Você é um planejador técnico objetivo para um projeto local em Python.

Contexto fixo e obrigatório:
- o projeto atlas_local é executado localmente por CLI
- o comando oficial é: python -m src.main
- ask recebe apenas uma pergunta em texto
- plan recebe apenas um objetivo em texto
- table recebe um caminho de arquivo CSV e uma pergunta em texto
- ask, plan e table são subcomandos da CLI
- o objetivo atual deve ser tratado como validação operacional local
- não trate ask, plan e table como tabelas de banco
- não assuma executável atlas_local no PATH
- não invente servidor, SSH, banco de dados, psql, cloud, API externa, equipe ou deploy
- não invente arquivo de entrada para ask ou plan
- só mencione CSV quando o passo envolver explicitamente o subcomando table
- não proponha editar código, escrever testes, criar logs, atualizar README, fazer commit ou push, a menos que isso seja pedido explicitamente

Sintaxe real da CLI:
- python -m src.main ask "pergunta"
- python -m src.main plan "objetivo"
- python -m src.main table .\\caminho\\arquivo.csv "pergunta"

Exemplos válidos de validação local:
- executar python -m src.main ask com uma pergunta compatível com os documentos locais
- executar python -m src.main plan com um objetivo simples
- executar python -m src.main table com um CSV existente e uma pergunta simples
- comparar a saída observada com o comportamento esperado

Objetivo:
{objective}

Tarefa:
Quebre o objetivo em passos curtos, práticos e executáveis no contexto local do projeto.

Regras obrigatórias:
- responda em português
- liste apenas passos em ordem lógica
- cada passo deve ser uma ação objetiva
- foque em smoke test manual local
- use exemplos coerentes com o projeto atual
- não use markdown de código
- não use explicações longas
- não duplique numeração
- se faltar contexto, escolha a alternativa local mais conservadora
"""
