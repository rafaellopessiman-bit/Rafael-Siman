from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="atlas_local")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ask_parser = subparsers.add_parser("ask", help="Consultar documentos locais.")
    ask_parser.add_argument("question", nargs="+", help="Pergunta sobre os documentos locais.")

    plan_parser = subparsers.add_parser("plan", help="Gerar um plano simples.")
    plan_parser.add_argument("objective", nargs="+", help="Objetivo para o planner.")

    table_parser = subparsers.add_parser("table", help="Consultar um arquivo CSV local.")
    table_parser.add_argument("file_path", help="Caminho do arquivo CSV.")
    table_parser.add_argument("question", nargs="+", help="Pergunta sobre o CSV local.")

    subparsers.add_parser("index", help="Indexar documentos textuais no SQLite local.")

    return parser
