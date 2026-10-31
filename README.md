# LinkTrial — MVP local

Plataforma demonstrativa de descoberta, pré-triagem, revisão médica e acompanhamento de encaminhamentos. Somente pacientes fictícios.

## Executar

Requisito: Node.js 24 ou superior. Não há dependências externas para instalar.

1. Abra esta pasta no terminal.
2. Execute `npm start`.
3. Acesse http://127.0.0.1:4175.

No Windows, também é possível executar `iniciar.cmd`. Mantenha o terminal aberto. O banco é criado automaticamente em `runtime/`. Para encerrar, pressione Ctrl+C. Use apenas uma instância por diretório de dados.

## Demonstração em cinco minutos

1. Em **Médico assistente**, selecione um paciente de demonstração e consulte os estudos validados do ClinicalTrials.gov.
2. Compare Horizonte (match promissor), Travessia (informação insuficiente) e Conexão (possível impedimento).
3. Abra Horizonte, leia as regras e fontes, registre a revisão e escolha o centro fictício para encaminhar.
4. Troque para **Centro de pesquisa**. Receba o caso, consulte o perfil enviado e solicite um documento.
5. Como médico, responda à pendência. Como centro, avance até avaliação e registre o resultado. Inclusão é uma ação posterior e separada.
6. Como **Administrador**, altere um estudo demonstrativo para concluído: ele sai da busca, mas seu histórico permanece.
7. Como **Farmacêutica**, veja a supressão de indicadores para grupos pequenos. Não existe acesso a pacientes nessa área.

A troca livre de papel existe somente para demonstrar. Não representa login institucional.

## O que funciona

- Interface responsiva em azul-marinho, teal e branco; catálogo com busca, origem e paginação.
- CRUD de pacientes fictícios, edição versionada, autorizações por finalidade, exportação, arquivamento e exclusão local.
- Dois bancos SQL: perfil clínico e identidade separados, com pseudônimo aleatório e conteúdo sensível criptografado com AES-256-GCM.
- CRUD de estudos fictícios, importação por NCT e sincronização pela API v2 do ClinicalTrials.gov.
- Pré-triagem determinística, critérios e justificativas; revisão médica obrigatória e revalidação antes do envio.
- Encaminhamento interno, pendências, responsáveis por papel, histórico e resultado informado pelo centro.
- Verificação de papel no servidor, sessão HttpOnly, proteção de origem/CSRF, auditoria e supressão de pequenos grupos.

## Limites explícitos

- Jev tem adaptador e teste de contrato. Jev e LLM **não estão conectados ao fluxo**; nenhuma chamada de IA é realizada pela interface. O motor ativo é local e demonstrativo.
- Critérios textuais reais permanecem pendentes; idade e sexo estruturados podem ser comparados. Não há interpretação clínica automática completa nem recomendação de tratamento.
- Nenhum caso é enviado a uma instituição externa. Centros e paciente da demonstração são fictícios.
- Pseudonimização não equivale a anonimização ou comprovação de conformidade com LGPD.
- Não há autenticação real, isolamento por instituição/centro, KMS, gestão de backups, hospedagem homologada ou servidor FHIR. Não utilizar dados reais.
- Métricas implementadas: contagens de encaminhamentos, pendências abertas, avaliações e inclusões. Tempo até primeira resposta pode ser calculado a partir dos eventos, mas ainda não tem painel próprio.

## Catálogo e sincronização

A semente preserva os 359 estudos do arquivo enviado. O pacote de demonstração inclui um snapshot local consultado à API: na última sincronização, os 359 registros responderam sem falhas e foram filtrados pelo status atual. Em uma instalação limpa sem o snapshot, ficam ocultos com `UNKNOWN` até sincronizar. Três protocolos fictícios existem somente para validar fluxos internos; a descoberta de pacientes mostra exclusivamente os estudos reais do ClinicalTrials.gov.

No administrador, **Validar**, **Importar por NCT** e **Sincronizar registro público** consultam o registro real. Um status global de recrutamento não garante vaga no centro. Novos encaminhamentos exigem que o centro selecionado também esteja informado como recrutando.

Registros reais ficam visíveis por até 24 horas desde a validação, se habilitados, não arquivados, com centro no Brasil e status RECRUITING ou NOT_YET_RECRUITING. Este último aparece claramente como ainda não recrutando. COMPLETED, TERMINATED, SUSPENDED, WITHDRAWN e demais estados ficam ocultos. Resposta 404 oculta o registro. Falhas transitórias preservam dados, mas não renovam sua validade.

`npm run sync` executa uma sincronização completa. Não rode simultaneamente ao servidor usando o mesmo diretório de dados. `LINKTRIAL_AUTO_SYNC=1` habilita sincronização a cada 24 horas enquanto o servidor permanece em execução; não é um serviço agendado do sistema operacional.

## Estrutura

- `public/`: interface sem bibliotecas externas.
- `server.mjs`: API HTTP e controles de sessão/origem.
- `src/schema.sql`: esquema relacional.
- `src/store.mjs`: persistência, criptografia e regras de negócio.
- `src/matching.mjs`: motor local, consenso experimental e adaptador Jev.
- `src/registry.mjs`: integração ClinicalTrials.gov.
- `tests/core.test.mjs`: testes de regras, privacidade e API.
- `docs/arquitetura-e-regras.md`: modelo e contratos.
- `docs/privacidade.md`: medidas e lacunas para operação real.

## Verificação

`npm test`: 19 testes passaram. `npm run check`: análise de sintaxe aprovada. A consulta real de NCT06119581 retornou RECRUITING e 29 centros no Brasil na verificação de 31/10/2026; esse resultado é temporal e deve ser reconsultado.

Variáveis opcionais: `PORT` (4175), `LINKTRIAL_DATA_DIR` (runtime), `LINKTRIAL_AUTO_SYNC` (desativado). O servidor escuta somente em 127.0.0.1.

## Locais dos estudos

Cada card apresenta até dois centros e cidades/UFs do Brasil, com a contagem de locais retornada pelo ClinicalTrials.gov. Se houver mais centros, o card indica quantos locais adicionais existem. Esses dados descrevem locais cadastrados na API; não confirmam que o centro ainda tenha vagas.
