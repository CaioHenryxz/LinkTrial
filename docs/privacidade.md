# Privacidade — implementado e pendente

## Controles presentes

- Somente dados fictícios e aviso persistente na interface.
- UUID e pseudônimo aleatórios; nome separado em vault.sqlite.
- AES-256-GCM para identidade, perfil, resultado da análise, notas e pendências.
- Papéis conferidos no servidor; identidade consultável apenas pelo papel médico e com auditoria.
- Sessão local HttpOnly e SameSite=Strict; verificação de Origin e CSRF nas mutações; escuta em loopback.
- Histórico de autorizações por finalidade, revogação, exportação e exclusão local.
- Payload mínimo para o adaptador de IA; nenhuma chamada externa de IA ativa.
- Visão da indústria sem identificação ou prontuário individual, com supressão de grupos pequenos.

## O que essas medidas não garantem

Pseudonimização mantém possibilidade de associação e não remove a natureza de dado pessoal. Separar tabelas/bancos e criptografar não torna o sistema automaticamente conforme à LGPD. Dados de saúde exigem análise específica da finalidade e da base legal aplicável. O registro de consentimento demonstrativo não resolve sozinho essa análise.

A mesma instância tem acesso aos dois bancos e às chaves locais. O seletor de papéis permite simular qualquer papel; não há autenticação de pessoas nem isolamento entre centros. Um centro da demonstração vê todos os encaminhamentos autorizados, e não somente os de uma instituição autenticada. Não inserir dados reais.

A exclusão elimina registros e dependências nos bancos desta instalação, com secure_delete ativado. Não representa eliminação certificada em SSD, cópias, backups, exportações ou retenções legais. Auditoria conserva eventos sem vínculo identificável direto após exclusão; pseudônimos e metadados também demandam proteção em produção.

## Pendências para um piloto real

| Área | Definição necessária |
|---|---|
| Governança | Controlador/operador, finalidade, base legal por operação, avisos e contratos |
| Acesso | Login institucional, MFA, autorização por vínculo/centro, menor privilégio, expiração e revisão de acessos |
| Criptografia | KMS/cofre separado, rotação, segregação de responsáveis, recuperação e proteção dos backups |
| Ciclo de vida | Prazos de retenção, descarte, solicitações do titular e exceções justificadas |
| Fornecedores | Contratos, tratamento/retencão de prompts, suboperadores e transferências internacionais quando aplicáveis |
| Operação | HTTPS, monitoramento, incidentes, disponibilidade, testes de segurança e continuidade |
| IA clínica | Validação supervisionada, prevenção de evidências inventadas, versões, qualidade e monitoramento |
| Agregados | Análise de reidentificação, combinação de filtros, consultas repetidas e política de divulgação |

Essas são lacunas de implementação e governança, não uma certificação ou parecer jurídico. Hospedar no Brasil, por si só, não resolve as obrigações.

Fontes oficiais consultadas em 31/10/2026:

- LGPD: https://normas.leg.br/?urn=urn%3Alex%3Abr%3Afederal%3Alei%3A2018-08-14%3B13709
- ANPD, direitos dos titulares: https://www.gov.br/anpd/pt-br/assuntos/titular-de-dados-1/direito-dos-titulares
- ANPD, glossário: https://www.gov.br/anpd/pt-br/centrais-de-conteudo/materiais-educativos-e-publicacoes/glossario-anpd
