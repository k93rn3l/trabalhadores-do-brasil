/**
 * Estrutura configurável de categorias e profissões sugeridas.
 *
 * A plataforma NÃO se limita a estas categorias: qualquer categoria presente
 * na planilha administrativa gera automaticamente sua página e aparece na
 * busca. Este arquivo serve para:
 *  - exibir as categorias populares na página inicial;
 *  - oferecer profissões sugeridas no select de categoria;
 *  - fornecer um texto introdutório (bom para SEO) em cada página de categoria.
 */
import { slug } from '../lib/normalizar';

export interface CategoriaConfig {
  nome: string;
  descricao: string;
  /** Profissões sugeridas — apenas sugestão, não uma lista fechada. */
  profissoes: string[];
}

export const CATEGORIAS: CategoriaConfig[] = [
  {
    nome: 'Construção e reformas',
    descricao: 'Profissionais para obras, reformas, pintura, revestimentos e carpintaria.',
    profissoes: ['Pedreiro', 'Pintor', 'Azulejista', 'Carpinteiro', 'Marceneiro', 'Gesseiro', 'Reforma em geral'],
  },
  {
    nome: 'Serviços domésticos',
    descricao: 'Limpeza, organização e cuidados com residências.',
    profissoes: ['Diarista', 'Limpeza residencial', 'Limpeza pós-obra', 'Organização de residências', 'Cozinheira doméstica'],
  },
  {
    nome: 'Manutenção residencial',
    descricao: 'Pequenos reparos, montagem de móveis, vidros, chaves e impermeabilização.',
    profissoes: ['Pequenos reparos', 'Montador de móveis', 'Vidraceiro', 'Serralheiro', 'Chaveiro', 'Impermeabilização', 'Dedetização e controle de pragas'],
  },
  {
    nome: 'Instalações elétricas',
    descricao: 'Eletricistas para instalações, manutenção e segurança elétrica.',
    profissoes: ['Eletricista residencial', 'Eletricista predial', 'Manutenção elétrica', 'Instalação de chuveiros e luminárias', 'Instalador de ar-condicionado'],
  },
  {
    nome: 'Hidráulica',
    descricao: 'Encanadores, desentupimento, caixas d’água e aquecedores.',
    profissoes: ['Encanador', 'Desentupimento', 'Conserto de vazamentos', 'Instalação de caixas d’água', 'Instalação de aquecedores'],
  },
  {
    nome: 'Tecnologia e informática',
    descricao: 'Suporte técnico, manutenção de computadores e desenvolvimento.',
    profissoes: ['Suporte técnico de informática', 'Manutenção de computadores e notebooks', 'Montagem de computadores', 'Desenvolvedor de sites e sistemas', 'Configuração de redes e Wi-Fi'],
  },
  {
    nome: 'Educação e aulas particulares',
    descricao: 'Professores particulares, reforço escolar e aulas diversas.',
    profissoes: ['Professor particular', 'Reforço escolar', 'Aulas de idiomas', 'Aulas de música', 'Preparação para ENEM e concursos', 'Aulas de informática'],
  },
  {
    nome: 'Beleza e estética',
    descricao: 'Cabelo, unhas, maquiagem, sobrancelhas e bem-estar.',
    profissoes: ['Cabelereiro', 'Barbeiro', 'Manicure e pedicure', 'Maquiador', 'Designer de sobrancelhas', 'Massagista', 'Depilação'],
  },
  {
    nome: 'Jardinagem',
    descricao: 'Criação e manutenção de jardins e áreas verdes.',
    profissoes: ['Jardinagem', 'Paisagismo', 'Poda de árvores', 'Manutenção de jardins', 'Plantio de grama'],
  },
  {
    nome: 'Transporte e mudanças',
    descricao: 'Fretes, carretos, mudanças e motoristas.',
    profissoes: ['Frete e carreto', 'Mudança residencial', 'Motorista particular', 'Transporte de cargas'],
  },
  {
    nome: 'Costura e confecção',
    descricao: 'Ajustes de roupas, confecção sob medida e customização.',
    profissoes: ['Costureira', 'Ajustes de roupas', 'Roupas sob medida', 'Bordado e customização', 'Confecção de peças'],
  },
  {
    nome: 'Serviços automotivos',
    descricao: 'Mecânica, funilaria, estética e socorro automotivo.',
    profissoes: ['Mecânico', 'Eletricista automotivo', 'Funilaria e pintura', 'Lavagem a domicílio', 'Borracharia', 'Socorro mecânico'],
  },
  {
    nome: 'Eventos',
    descricao: 'Buffet, confeitaria, decoração, fotografia e sonorização.',
    profissoes: ['Buffet', 'Confeiteiro', 'Decoração de festas', 'Fotógrafo', 'Garçom', 'DJ e sonorização', 'Animador de festas'],
  },
  {
    nome: 'Serviços administrativos',
    descricao: 'Apoio administrativo, digitação, currículos e imposto de renda.',
    profissoes: ['Apoio administrativo', 'Serviços de digitação', 'Elaboração de currículos', 'Declaração de imposto de renda'],
  },
  {
    nome: 'Serviços profissionais especializados',
    descricao: 'Profissionais de nível superior atendendo de forma autônoma.',
    profissoes: ['Advogado', 'Contador', 'Engenheiro', 'Arquiteto', 'Designer', 'Psicólogo', 'Nutricionista', 'Fisioterapeuta'],
  },
  {
    nome: 'Outros serviços',
    descricao: 'Serviços que não se encaixam nas demais categorias.',
    profissoes: ['Outro tipo de serviço'],
  },
];

/** Busca a configuração de uma categoria a partir do seu slug. */
export function categoriaPorSlug(slugCategoria: string): CategoriaConfig | undefined {
  return CATEGORIAS.find((c) => slug(c.nome) === slugCategoria);
}
