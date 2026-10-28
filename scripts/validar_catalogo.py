#!/usr/bin/env python3
"""Valida um arquivo de catálogo JSON público (usado no CI após a sincronização)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sync_catalogo import validar_catalogo  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("arquivo", help="caminho do catalogo.json")
    args = parser.parse_args()

    try:
        dados = json.loads(Path(args.arquivo).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as erro:
        print(f"FALHA: não foi possível ler {args.arquivo}: {erro}", file=sys.stderr)
        return 1

    valido, erros = validar_catalogo(dados)
    if not valido:
        print(f"FALHA: {args.arquivo} inválido:", file=sys.stderr)
        for erro in erros[:30]:
            print(f"  - {erro}", file=sys.stderr)
        return 1

    total = dados.get("total", 0)
    print(f"OK: {args.arquivo} válido ({total} profissionais).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
