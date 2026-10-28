/**
 * Carregamento do catálogo no build (somente servidor — nunca importado
 * pelo código que roda no navegador).
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { analisarCatalogo, type Catalogo } from './catalogo-parse';

const CAMINHO_CATALOGO = new URL('../../public/data/catalogo.json', import.meta.url);

export interface CarregarCatalogo {
  /** O catálogo nunca é null: sem dados é um catálogo válido e vazio. */
  catalogo: Catalogo;
}

/**
 * Lê e valida public/data/catalogo.json. Se o arquivo estiver corrompido,
 * o build falha com mensagem clara — um catálogo inválido nunca deve ser
 * publicado (princípio fail-closed).
 */
export function carregarCatalogo(): CarregarCatalogo {
  let texto: string;
  try {
    texto = readFileSync(fileURLToPath(CAMINHO_CATALOGO), 'utf-8');
  } catch (erro) {
    throw new Error(
      `Não foi possível ler public/data/catalogo.json: ${(erro as Error).message}`,
    );
  }

  let dados: unknown;
  try {
    dados = JSON.parse(texto);
  } catch (erro) {
    throw new Error(
      `public/data/catalogo.json contém JSON inválido (${(erro as Error).message}). ` +
        'Execute "npm run sync" para regenerar ou restaure a última versão válida.',
    );
  }

  const resultado = analisarCatalogo(dados);
  if (!resultado.ok) {
    throw new Error(
      'public/data/catalogo.json não passou na validação:\n  - ' +
        resultado.erros.join('\n  - '),
    );
  }

  return { catalogo: resultado.catalogo };
}
