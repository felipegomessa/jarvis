# Dataset — JARVIS Acadêmico

Este diretório contém os documentos acadêmicos usados pelo RAG.

> **Trabalho 1 — requisito 7 (Dataset)**: mínimo de 10 documentos.

## Inventário (preencher quando documentos forem adicionados)

| # | Arquivo | Tipo | Origem | Tamanho | Tema |
|---|---------|------|--------|---------|------|
| 1 | _vazio_ | _PDF/TXT/MD_ | _autor/origem_ | _pgs/KB_ | _assunto_ |

## Estratégia de chunking

Conforme ADR [D-006](../decisions.md#d-006):

- **Algoritmo**: Recursive Character Splitter (hierarquia de separadores)
- **Tamanho-alvo**: 800 caracteres
- **Overlap**: 150 caracteres
- **Separadores (em ordem)**: `"\n\n"`, `"\n"`, `". "`, `"? "`, `"! "`, `" "`, `""`

### Impacto esperado no RAG

- **Chunks de ~800 chars** equilibram: contexto suficiente para a LLM responder + cabe
  bem na janela de 512 tokens do `multilingual-e5-small` (com folga para acentos e
  caracteres pt-BR).
- **Overlap de 150 chars** evita perda de informação na fronteira (especialmente em
  conteúdo acadêmico onde a continuidade de raciocínio é crítica).
- **Separadores hierárquicos** preservam fronteiras semânticas naturais (parágrafos,
  sentenças) antes de quebrar por palavra/caractere.

## Limitações conhecidas

(serão registradas conforme observadas durante a avaliação)

- pdfplumber pode falhar em PDFs scanneados (OCR seria necessário — fora do escopo do Trabalho 1).
- Tabelas complexas podem ser linearizadas de forma sub-ótima.
- Fórmulas matemáticas em LaTeX/imagem ficam ilegíveis.

## Procedência

Cada documento deve listar abaixo:
- Origem (URL, autor, instituição).
- Licença (creative commons, fair use acadêmico, material próprio).
- Data de coleta.
