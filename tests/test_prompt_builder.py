from src.core.prompt_builder import build_knowledge_prompt


def test_build_knowledge_prompt_prefers_matched_chunks_and_metadata() -> None:
    prompt = build_knowledge_prompt(
        "Como indexar transactions no MongoDB?",
        [
            {
                "file_name": "mongodb-notes.pdf",
                "file_path": "mongodb-notes.pdf",
                "score": 12.5,
                "content": "conteudo completo muito maior que nao deveria ser priorizado",
                "matched_chunks": [
                    "db.transactions.createIndex({ cr_dr: 1 })",
                    "MongoDB cria indice unico em _id por padrao.",
                ],
                "metadata": {
                    "theme": "bancos",
                    "stack": ["mongodb"],
                    "concepts": ["performance"],
                },
            }
        ],
    )

    assert "Trecho relevante 1: db.transactions.createIndex({ cr_dr: 1 })" in prompt
    assert "Tema: bancos" in prompt
    assert "Stack: mongodb" in prompt
    assert "Conteúdo recuperado:" not in prompt
