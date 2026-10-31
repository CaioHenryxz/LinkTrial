# Arquitetura e regras da LinkTrial

## Decisão de implementação

Para tornar os HTMLs fornecidos em um MVP executável, foi usado um monólito local: interface HTML/CSS/JavaScript, API Node.js 24 e SQLite. Isso permite executar sem instalar dependências e concentra as regras no servidor. Os arquivos originais não foram alterados. React, Spring Boot e PostgreSQL continuam sendo opções para evolução; não são necessários para demonstrar este fluxo.

## Entidades

| Entidade | Finalidade e invariantes |
|---|---|
| patients | UUID interno, pseudônimo aleatório, instituição demonstrativa, perfil criptografado, versão e arquivamento |
| identities (vault.sqlite) | Nome fictício criptografado vinculado por UUID; separado do banco clínico |
| consents | Histórico por finalidade matching/referral, versão do aviso, concessão/revogação e ator |
| studies | Identificador, origem, situação no registro, habilitação, arquivamento, validade e conteúdo público |
| study_versions | Fotografias versionadas dos protocolos para rastreabilidade |
| matches | Versões do paciente/estudo e análise criptografada |
| reviews | Decisão do médico, nota e perfil na revisão, criptografados |
| referrals | Paciente, estudo, centro, revisão, etapa, resultado e eventual inclusão |
| pending_items | Pendência e resposta criptografadas, com datas |
| events | Linha do tempo, ação, papel responsável e data |
| audit | Acesso e mutações sem nomes nem conteúdo clínico nos eventos |
| sync_runs | Execuções, progresso e falhas da sincronização |

O esquema executável está em `src/schema.sql`. Valores de consultas são parametrizados. Identidade e dados clínicos usam chaves separadas, armazenadas localmente no mesmo arquivo de chave exclusivamente para o protótipo.

## Regras do fluxo

1. Criar perfil exige declaração de dados fictícios. Apenas campos clínicos permitidos entram no perfil; nome fica no cofre.
2. Ausência de informação é `null`/unknown, nunca correspondência presumida.
3. A busca exige autorização para pré-triagem. A concessão para encaminhar é independente.
4. Match promissor exige todos os critérios avaliados com correspondência, sem lacunas ou impedimentos. Não produz elegibilidade final.
5. Critérios de exclusão têm semântica invertida: presença do impedimento gera barreira.
6. Estudos reais conservam o texto de elegibilidade original. Coortes e texto complexo não são inferidos pelo motor local.
7. Revisão exige confirmação, justificativa e decisão forward/hold. Só forward permite encaminhamento.
8. Antes do envio, conferir novamente status, autorizações, versão clínica, versão do estudo e revisão com menos de 24 horas.
9. O centro selecionado precisa ter status RECRUITING. Isso não confirma disponibilidade de vaga.
10. Não duplicar encaminhamento do mesmo paciente para o mesmo estudo nesta versão.
11. Etapas: encaminhado → recebido → em avaliação → agendado → concluído. Pendências abertas bloqueiam avanço.
12. O centro declara elegível/não elegível/inconclusivo. Inclusão é registrada separadamente e apenas após resultado elegível.
13. Revogação de encaminhamento ou arquivamento do perfil suspende acesso do centro. Histórico permanece acessível ao médico; exclusão do paciente remove dependências locais.
14. Arquivar estudo é exclusão lógica: retira da busca preservando histórico; sincronização não reativa arquivamento manual.
15. Papel de farmacêutica recebe somente agregados. Grupos menores que cinco são suprimidos; isso é um controle demonstrativo, não garantia de anonimização.

## Jev + LLM

Posição prevista: perfil mínimo → pré-filtros → Jev e LLM → verificação determinística → revisão humana.

`callJev()` implementa o contrato Choice da API System One e remove identificadores, pseudônimos, notas e datas do payload. A função não é chamada pelo aplicativo. Não há chave embutida ou ativação automática.

Contrato previsto para LLM: `analyze({clinical, criteria})` retorna `{id,result,quote,evidence:[{field,value}]}` por critério. Deve tratar coortes, condições temporais, inclusão/exclusão e ausência de dados. Provedor e modelo ainda precisam ser escolhidos e integrados.

`validateModelConsensus()` só aceita resultado compatible/barrier quando existe concordância, confiança Jev >= 0,9, citação literal do critério e evidências presentes no perfil. Caso contrário retorna unknown. O limiar é uma hipótese de implementação, sem calibração clínica. Correspondência literal e concordância não comprovam correção semântica; antes de ativar, implementar avaliação com casos rotulados, rastreabilidade de modelos, coortes, contexto temporal e revisão de segurança clínica. Nunca usar esse consenso para confirmar elegibilidade.

Referência consultada: https://docs.typesafe.ai/api/system-one e https://docs.typesafe.ai/primitives/choice.

## FHIR/mCODE

O perfil local é um subconjunto demonstrativo, não um recurso FHIR validado nem implementação conforme ao mCODE. Mapeamento candidato:

| Dado local | Recurso candidato |
|---|---|
| Identificador pseudonimizado | Patient.identifier |
| Diagnóstico oncológico | Condition, perfil oncológico mCODE aplicável |
| Estadiamento e ECOG | Observation |
| EGFR / ALK | Observation e DiagnosticReport genômicos |
| Tratamentos e linhas anteriores | MedicationAdministration/MedicationStatement e histórico de procedimentos |
| Autorizações | Consent |
| Encaminhamento e acompanhamento | ServiceRequest e Task |
| Rastreabilidade | Provenance e AuditEvent |

Não criar códigos clínicos automaticamente com base em rótulos de tela. A evolução deve fixar uma versão publicada do guia, terminologias, unidades, evidências, datas e validação de perfis. O endereço build.fhir.org fornecido é uma compilação contínua e pode mudar. O esquema local não preserva ainda a granularidade completa da jornada oncológica.

## Evolução prioritária

1. Autenticação institucional e vínculo paciente-médico-centro, com escopo por organização.
2. PostgreSQL com migrações, transações robustas, cofre/KMS separado, recuperação e retenção.
3. mCODE versionado e validado, com procedência/data dos exames e tratamentos.
4. Integração Jev/LLM após avaliação de privacidade, contratos e testes clínicos supervisionados.
5. Sincronização agendada confiável, alertas de alteração e confirmação operacional de centros.
6. Métricas de tempo de resposta e pendências, com política de agregação e validação no piloto.

Referência mCODE consultada: https://build.fhir.org/ig/HL7/fhir-mCODE-ig/ (compilação contínua STU4, baseada em FHIR R4).
