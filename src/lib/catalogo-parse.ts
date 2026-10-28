/**
 * Tipos e validação do catálogo público (isomórfico: usado no build pelo
 * servidor e no navegador pela página de busca).
 *
 * Somente campos autorizados para publicação existem aqui. E-mails
 * administrativos, observações internas e dados de registros não aprovados
 * nunca chegam a este formato — o sincronizador (scripts/sync_catalogo.py)
 * garante isso na origem e esta validação confere na leitura.
 */
import { UFS, type UF } from './estados';

export interface Profissional {
  /** Identificador público estável (não expõe dados privados). */
  id: string;
  nome: string;
  categoria: string;
  categoriaSlug: string;
  profissao: string;
  descricao: string;
  uf: UF;
  municipio: string;
  municipioSlug: string;
  /** Bairros/regiões atendidas. */
  regioes: string[];
  /** Outros municípios atendidos, quando informado. */
  municipiosAtendidos: string[];
  /** Atendimento remoto/online. */
  remoto: boolean;
  /** WhatsApp normalizado no formato 55DDD9XXXXXXXX. */
  whatsapp: string;
  /** Data de atualização pública (YYYY-MM-DD). */
  atualizadoEm: string;
}

export interface Catalogo {
  versao: number;
  /** ISO 8601 ou null quando o catálogo inicial ainda está vazio. */
  geradoEm: string | null;
  total: number;
  profissionais: Profissional[];
}

export type ResultadoAnalise =
  | { ok: true; catalogo: Catalogo }
  | { ok: false; erros: string[] };

const CAMPOS_TEXTO: (keyof Profissional)[] = [
  'id', 'nome', 'categoria', 'categoriaSlug', 'profissao', 'descricao',
  'uf', 'municipio', 'municipioSlug', 'whatsapp', 'atualizadoEm',
];

const REGEX_ID = /^[a-z0-9-]{4,64}$/;
const REGEX_SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const REGEX_DATA = /^\d{4}-\d{2}-\d{2}$/;
const REGEX_WHATSAPP = /^55[1-9][0-9]9[0-9]{8}$/;
const TAMANHO_MAXIMO: Partial<Record<keyof Profissional, number>> = {
  nome: 160,
  profissao: 120,
  categoria: 120,
  descricao: 2000,
  municipio: 120,
};

function ehObjeto(valor: unknown): valor is Record<string, unknown> {
  return typeof valor === 'object' && valor !== null && !Array.isArray(valor);
}

function listaDeTextos(valor: unknown, erros: string[], prefixo: string, campo: string): string[] {
  if (valor === undefined || valor === null) return [];
  if (!Array.isArray(valor)) {
    erros.push(`${prefixo}: campo "${campo}" deve ser uma lista de textos.`);
    return [];
  }
  const itens: string[] = [];
  valor.forEach((item, i) => {
    if (typeof item !== 'string' || !item.trim()) {
      erros.push(`${prefixo}: "${campo}[${i}]" deve ser um texto não vazio.`);
    } else {
      itens.push(item.trim().slice(0, 120));
    }
  });
  return itens;
}

/**
 * Valida a estrutura completa do catálogo. Retorna todos os problemas
 * encontrados de uma vez, para facilitar o diagnóstico no CI.
 */
export function analisarCatalogo(dados: unknown): ResultadoAnalise {
  const erros: string[] = [];
  if (!ehObjeto(dados)) {
    return { ok: false, erros: ['O catálogo deve ser um objeto JSON.'] };
  }

  if (dados.versao !== 1) {
    erros.push(`Campo "versao" deve ser o número 1 (recebido: ${JSON.stringify(dados.versao)}).`);
  }

  if (dados.geradoEm !== null && dados.geradoEm !== undefined) {
    if (typeof dados.geradoEm !== 'string' || !/^\d{4}-\d{2}-\d{2}T[\d:.]+Z$/.test(dados.geradoEm)) {
      erros.push('Campo "geradoEm" deve ser null ou data ISO 8601.');
    }
  }

  if (!Array.isArray(dados.profissionais)) {
    return { ok: false, erros: [...erros, 'Campo "profissionais" deve ser uma lista.'] };
  }

  const profissionais: Profissional[] = [];
  const ids = new Set<string>();

  dados.profissionais.forEach((item, indice) => {
    const prefixo = `profissionais[${indice}]`;
    if (!ehObjeto(item)) {
      erros.push(`${prefixo}: deve ser um objeto.`);
      return;
    }

    let itemValido = true;

    for (const campo of CAMPOS_TEXTO) {
      const valor = item[campo];
      if (typeof valor !== 'string' || !valor.trim()) {
        erros.push(`${prefixo}: campo "${campo}" é obrigatório e não pode ser vazio.`);
        itemValido = false;
      }
    }

    const p = item as unknown as Profissional;

    if (itemValido) {
      if (!REGEX_ID.test(p.id)) {
        erros.push(`${prefixo}: "id" inválido (use 4–64 caracteres: a–z, 0–9, hífen).`);
        itemValido = false;
      } else if (ids.has(p.id)) {
        erros.push(`${prefixo}: "id" duplicado (${p.id}).`);
        itemValido = false;
      }

      if (!(UFS as readonly string[]).includes(p.uf)) {
        erros.push(`${prefixo}: UF inválida ("${p.uf}").`);
        itemValido = false;
      }
      if (!REGEX_SLUG.test(p.categoriaSlug)) {
        erros.push(`${prefixo}: "categoriaSlug" inválida.`);
        itemValido = false;
      }
      if (!REGEX_SLUG.test(p.municipioSlug)) {
        erros.push(`${prefixo}: "municipioSlug" inválido.`);
        itemValido = false;
      }
      if (!REGEX_WHATSAPP.test(p.whatsapp)) {
        erros.push(`${prefixo}: "whatsapp" fora do formato 55DDD9XXXXXXXX.`);
        itemValido = false;
      }
      if (!REGEX_DATA.test(p.atualizadoEm)) {
        erros.push(`${prefixo}: "atualizadoEm" fora do formato AAAA-MM-DD.`);
        itemValido = false;
      }
      for (const [campo, maximo] of Object.entries(TAMANHO_MAXIMO)) {
        const valor = item[campo];
        if (typeof valor === 'string' && valor.length > maximo) {
          erros.push(`${prefixo}: "${campo}" excede ${maximo} caracteres.`);
          itemValido = false;
        }
      }
    }

    if (item.remoto !== undefined && typeof item.remoto !== 'boolean') {
      erros.push(`${prefixo}: "remoto" deve ser verdadeiro/falso.`);
      itemValido = false;
    }

    if (itemValido) {
      ids.add(p.id);
      profissionais.push({
        ...p,
        nome: p.nome.trim(),
        categoria: p.categoria.trim(),
        profissao: p.profissao.trim(),
        descricao: p.descricao.trim(),
        municipio: p.municipio.trim(),
        regioes: listaDeTextos(item.regioes, erros, prefixo, 'regioes'),
        municipiosAtendidos: listaDeTextos(item.municipiosAtendidos, erros, prefixo, 'municipiosAtendidos'),
        remoto: item.remoto === true,
      });
    }
  });

  if (erros.length > 0) {
    return { ok: false, erros: erros.slice(0, 50) };
  }

  const total = typeof dados.total === 'number' ? dados.total : profissionais.length;
  if (typeof dados.total !== 'undefined' && dados.total !== profissionais.length) {
    return { ok: false, erros: [`Campo "total" (${dados.total}) difere da lista (${profissionais.length} itens).`] };
  }

  return {
    ok: true,
    catalogo: {
      versao: 1,
      geradoEm: typeof dados.geradoEm === 'string' ? dados.geradoEm : null,
      total,
      profissionais,
    },
  };
}
