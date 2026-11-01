# LinkTrial — valor de negócio, mercado, LGPD e split de valor

> Pitch MIT Hacking Medicine – Einstein · versão 31/10/2026.
> **Regra deste documento:** todo número tem fonte (acessada em 31/10/2026) ou está marcado como `[PREMISSA]` (hipótese nossa, editável) ou `[A VALIDAR]`. Interpretações jurídicas aqui **não substituem parecer jurídico** — validar com advogado de saúde/proteção de dados antes de operar com dado real.

---

## 1. O problema em números

| Fato | Número | Fonte |
|---|---|---|
| Casos novos de câncer/ano no Brasil (2026–2028) | **~781 mil** (~518 mil sem pele não melanoma) | INCA, Estimativa 2026 — [introdução](https://www.gov.br/inca/pt-br/assuntos/cancer/numeros/estimativa/introducao) |
| Pacientes que **não têm estudo disponível na própria instituição** | **55,6%** (IC95% 43,7–67,3%) | Unger et al., JNCI 2019, meta-análise, 8.883 pacientes — [PMC6410951](https://pmc.ncbi.nlm.nih.gov/articles/PMC6410951/) |
| Pacientes que de fato entram em estudo | **8,1%** (acadêmico 15,9% · comunidade 7,0%) | mesma fonte |
| Barreiras estruturais + clínicas | **77,1%** das não participações | mesma fonte |
| Centros que atingem a meta de recrutamento | **39%** (37% não atingem; 11% não recrutam ninguém); prazos tipicamente **dobram** | Tufts CSDD, citado por CTTI — [resumo](https://ctti-clinicaltrials.org/wp-content/uploads/2021/07/CTTI_Recruitment_Meeting_Summary.pdf) |
| Estudos oncológicos **abertos com centro no Brasil hoje** | **359** estudos · **2.335** pontos de recrutamento (estudo×centro) · 72% patrocínio da indústria | **dado próprio** — ClinicalTrials.gov API v2, sync LinkTrial 31/10/2026 |

**Tese:** o maior gargalo não é falta de estudo, é **o estudo certo não chegar ao paciente certo**. Em 55,6% dos casos, o estudo não está na instituição do paciente, mas pode estar em outro centro. O LinkTrial faz essa ponte.

## 2. Por que agora, no Brasil

- **Lei 14.874/2024** (pesquisa com seres humanos) moderniza o marco e define prazos — [texto](https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2024/lei/l14874.htm).
- **ANVISA RDC 945/2024**: novas diretrizes de ensaios clínicos — [regulamentação](https://www.gov.br/anvisa/pt-br/assuntos/medicamentos/pesquisaclinica/regulamentacao).
- **Interfarma/IQVIA (set/2025):** com o novo marco, o Brasil pode ir da **20ª para a 10ª** posição no ranking global de estudos, com **R$ 2,1 bi/ano** de investimento direto adicional, **R$ 6,3 bi/ano** de impacto econômico e **~286 mil pacientes** beneficiados; em 2024, **78,7%** dos estudos no país foram patrocinados pela indústria — [Interfarma](https://www.interfarma.org.br/pesquisa-clinica-pode-injetar-r-63-bilhoes-por-ano-na-economia-brasileira-e-beneficiar-mais-de-286-mil-pacientes/).
- **Interfarma, Indicadores 1º sem/2026:** Brasil com **2,1%** dos ensaios iniciados no mundo e a melhor posição no ranking dos últimos 5 anos; oncologia lidera as áreas — [PDF](https://www.interfarma.org.br/wp-content/uploads/2026/10/1S-Indicadores-de-Pesquisa-Clinica.pdf). *(A imprensa citou 2,9% e 12ª posição em jun/2026 — [Valor](https://valor.globo.com/empresas/noticia/2026/06/23/brasil-sobe-seis-posies-e-ocupa-12-posio-em-ranking-global-de-pesquisa-clnica.ghtml). Usar o dado do PDF primário e citar a data.)*

**Leitura para o pitch:** para subir no ranking, o país precisa **recrutar mais rápido**, porque patrocinador escolhe país pela capacidade de recrutar. O LinkTrial é infraestrutura para essa meta nacional.

## 3. Mercado

### TAM — serviços globais de recrutamento de pacientes
| Fonte (relatório comercial) | 2026 | Projeção |
|---|---|---|
| Research and Markets / TBRC | **US$ 3,65 bi** | US$ 4,98 bi em 2030 (CAGR 8,1%) — [link](https://www.researchandmarkets.com/reports/6174398/clinical-trial-patient-recruitment-services) |
| Mordor Intelligence | **US$ 1,14 bi** | US$ 1,66 bi em 2031 (CAGR 7,8%) — [link](https://www.mordorintelligence.com/es/industry-reports/clinical-trial-patient-recruitment-services-market) |

As estimativas divergem ~3× porque cada relatório define o escopo de um jeito. No slide, apresentar a **faixa US$ 1,1–3,7 bi** e citar ambos.

### SAM — Brasil, oncologia
- Investimento potencial adicional em pesquisa clínica no Brasil: **R$ 2,1 bi/ano** (Interfarma), dentro de **US$ 199 bi** de investimento global em pesquisa clínica (mesma fonte).
- Oncologia é a área líder no país (Interfarma 1S/2026). Oferta mensurável hoje: **359 estudos / 2.335 pontos** (dado próprio).
- `[A VALIDAR]`: a fração do orçamento de um estudo destinada a recrutamento no Brasil. Fonte possível: ABRACRO/CROs. Não temos número público confiável.

### SOM — bottom-up (fórmula editável)
```
Receita/ano = (estudos-clientes × taxa anual por estudo) + (centros-clientes × SaaS anual)
```
| Variável | Conservador | Base | Fonte |
|---|---|---|---|
| Estudos oncológicos abertos no BR | 359 | 359 | dado próprio |
| % que contrata o LinkTrial no ano 3 | 5% (18) | 10% (36) | `[PREMISSA]` |
| Taxa anual por estudo (feasibility + pré-triagem + painel) | R$ 60 mil | R$ 120 mil | `[PREMISSA]` |
| Centros de pesquisa clientes (SaaS de triagem) | 10 | 25 | `[PREMISSA]` |
| SaaS anual por centro | R$ 24 mil | R$ 36 mil | `[PREMISSA]` |
| **Receita ano 3** | **R$ 1,32 mi** | **R$ 5,22 mi** | cálculo |

Contas: conservador = 18 × 60k + 10 × 24k = 1,08 mi + 0,24 mi; base = 36 × 120k + 25 × 36k = 4,32 mi + 0,90 mi. O que move o número é **quantos estudos contratam** e o valor do contrato; os dois precisam ser validados em conversa com 3–5 patrocinadores/CROs.

> Referência de custo do setor: centralized outreach com mediana de US$ 1,33 mi por estudo e custo por paciente de US$ 143 a US$ 11.392 conforme a área. É um dado do Tufts, mas citado por fonte **secundária** ([IntuitionLabs](https://intuitionlabs.ai/pdfs/clinical-trial-patient-recruitment-vendors-compared.pdf)) — `[A VALIDAR na fonte primária]` antes de ir para o slide.

### Potencial de uso
- **Médico assistente** (SUS e privado): busca de estudo para o seu paciente em minutos, em português, sem saber inglês regulatório.
- **Coordenador de centro:** pré-triagem dos encaminhamentos recebidos e feasibility ("quantos pacientes meus cabem neste protocolo?").
- **Patrocinador/CRO:** escolha de centros e previsão de recrutamento com dado brasileiro.
- **Gestor/SUS:** mapa de onde há estudo aberto por UF e tumor. Já sai do sync: SP 324 estudos, RS 210, RN 100.

## 4. LGPD — problemas a resolver e como resolver

Base legal conferida no texto oficial — [Lei 13.709/2018](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm).

| # | Problema | Base legal | Solução no LinkTrial |
|---|---|---|---|
| 1 | Dado de saúde é **sensível** | art. 5º II; art. 11 | Base: **consentimento específico e destacado** (art. 11, I), colhido na consulta, com finalidade clara: "buscar estudos para mim". Alternativa a avaliar com o jurídico: tutela da saúde por profissional de saúde |
| 2 | **Indústria não pode comprar dado de saúde.** O art. 11 §4º veda compartilhar dado de saúde entre controladores "com objetivo de obter vantagem econômica" | art. 11 §4º (red. Lei 13.853/2019); as exceções exigem prestação de serviço de saúde **em benefício do titular** | **A indústria nunca recebe dado identificável.** Recebe só agregados anônimos (art. 12) para feasibility. O encaminhamento vai do médico para o **centro do estudo**, por iniciativa do paciente e com consentimento. O modelo de receita é por **serviço**, não por dado |
| 3 | IA em nuvem fora do Brasil (Jev/TypeSafe, LLM) = **transferência internacional** | art. 33; **Res. CD/ANPD 19/2024** (cláusulas-padrão, prazo de 12 meses para adequar contratos) — [ANPD](https://www.gov.br/anpd/pt-br/acesso-a-informacao/institucional/atos-normativos/regulamentacoes_anpd/resolucao-cd-anpd-no-19-de-23-de-agosto-de-2024) | **Pseudonimizar antes da IA**: sem nome, CPF, endereço ou datas exatas; só os campos clínicos mCODE mínimos. Contratos com cláusulas-padrão ANPD e retenção zero. Rota futura: modelo hospedado no Brasil. Dado pseudonimizado **continua sendo dado pessoal**, então a pseudonimização reduz o risco mas não dispensa as cláusulas |
| 4 | Quem é controlador? | arts. 5º VI/VII, 39 | Desenho recomendado: o **médico/instituição** é controlador do prontuário; o **LinkTrial** é operador no matching (contrato de operador); o **centro do estudo** vira controlador próprio após o encaminhamento consentido |
| 5 | Relatório de impacto (RIPD) | art. 38 | Fazer o RIPD antes do piloto: dados, fluxos, riscos de reidentificação, medidas. O sistema já gera trilha de auditoria por critério |
| 6 | Pesquisa vs assistência | art. 11 II c; art. 13 (órgão de pesquisa, pseudonimização, sem repasse a terceiros) | Matching e encaminhamento **não são pesquisa**. Medir desfechos do próprio LinkTrial (tempo até encaminhamento, inclusões) **é**, e vai ao CEP |
| 7 | Direitos do titular, incidentes, encarregado | arts. 18, 41, 48 | Portal do titular (acesso, revogação, exclusão), DPO nomeado, plano de resposta a incidente |

Estado atual do MVP: só usa pacientes **sintéticos**. Nenhum dado real até RIPD + parecer jurídico + CEP do piloto.

## 5. Ética médica e o médico que cadastra

Texto conferido no **Código de Ética Médica, Res. CFM 2.217/2018** — [PDF oficial](https://sistemas.cfm.org.br/normas/arquivos/resolucoes/BR/2018/2217_2018.pdf):

- **Art. 59**: é vedado ao médico "oferecer ou aceitar remuneração ou vantagens **por paciente encaminhado** ou recebido".
- **Art. 58**: vedado "o exercício mercantilista da medicina".
- **Art. 68**: vedado exercer a profissão "com interação ou dependência de [...] indústria farmacêutica".
- **Art. 104**: vedado "deixar de manter independência profissional e científica em relação a financiadores de pesquisa médica [...] obtendo vantagens pessoais".
- **Art. 102, parágrafo único**: terapêutica experimental é permitida quando aceita pelos órgãos competentes e **com consentimento** do paciente.
- **Art. 53**: o médico que recebe paciente para procedimento especializado deve **devolvê-lo ao médico assistente com as informações**. O LinkTrial operacionaliza esse retorno.

Referência internacional convergente: AMA, *Fee Splitting* — pagamento "solely for referral of a patient is fee splitting and is unethical" ([AMA](https://code-medical-ethics.ama-assn.org/ethics-opinions/fee-splitting)). IRBs acadêmicos proíbem *finder's fees* e bônus por velocidade de recrutamento a médicos, mas aceitam remunerar trabalho efetivo de recrutamento e triagem ([Univ. Utah IRB](https://irb.utah.edu/guidance-series/payments-for-referrals-to-research-studies/)).

**Conclusão: o médico que cadastra NÃO pode receber por paciente encaminhado.** O benefício dele é outro:

| Benefício ao médico cadastrante | Por que é legítimo |
|---|---|
| Ferramenta **gratuita** que acha estudo em minutos, em português | Não depende de volume de encaminhamento |
| **Prontuário estruturado em mCODE/FHIR** exportável: reaproveita no próprio serviço, registros e auditoria | Valor assistencial direto |
| **Retorno do caso** (art. 53): status do encaminhamento e devolução do paciente com informações | Continuidade do cuidado |
| Opção terapêutica concreta quando o SUS não oferece o padrão atual | Melhor desfecho para o paciente dele |
| Educação médica (alertas de estudos por perfil, painel por tumor) | Benefício não pecuniário e não atrelado a encaminhamento |
| Se a instituição do médico **vira centro**, ele pode ser subinvestigador remunerado **pelo trabalho**, via orçamento do estudo aprovado pelo CEP | Remuneração por serviço prestado, não por indicação |

## 6. Split de valor: quem paga, por quê, para onde vai

```
INDÚSTRIA/CRO ──(contrato de serviço: feasibility, pré-triagem, painel)──► LINKTRIAL (empresa)
INDÚSTRIA/CRO ──(orçamento do estudo aprovado pelo CEP)──► CENTRO DE PESQUISA ──► equipe do estudo (trabalho efetivo)
LINKTRIAL ──(ferramenta grátis, dados estruturados, retorno do caso)──► MÉDICO ASSISTENTE
ESTUDO ──(ressarcimento de transporte/alimentação — Lei 14.874 art. 20 §1º)──► PACIENTE
PACIENTE ──(nada)──► ninguém
```

| | Permitido | Zona cinzenta (evitar / parecer) | Vedado |
|---|---|---|---|
| Indústria → LinkTrial | Taxa fixa por estudo ou assinatura por serviço (feasibility, pré-triagem, painel), sem acesso a dado identificável | Taxa da empresa por paciente **randomizado** (prática de mercado entre empresas; avaliar percepção do CEP e garantir que nada chega ao médico) | Comprar ou receber dado de saúde identificável (LGPD art. 11 §4º) |
| → Médico assistente | Ferramenta gratuita, educação, retorno do caso | Prêmios ou "pontos" por uso | Qualquer valor por paciente encaminhado (CEM art. 59) |
| → Centro / equipe do estudo | Orçamento do estudo aprovado pelo CEP, por trabalho de triagem/condução | Bônus por velocidade de inclusão | *Finder's fee* a pesquisador |
| → Paciente | Ressarcimento de despesas (Lei 14.874 art. 20 §1º) | — | Remuneração ou vantagem pela participação (art. 20, *caput*; exceção só para fase I/bioequivalência em saudáveis, §2º) |

**Frase para o pitch:** *"O paciente não paga e não é produto: a indústria paga por um serviço que encurta o recrutamento, e o médico ganha uma ferramenta que melhora o cuidado, nunca dinheiro por encaminhamento."*

## 7. Riscos e próximos passos
1. **Parecer jurídico** (LGPD art. 11 §4º e papéis controlador/operador) antes de qualquer dado real.
2. **RIPD + CEP** para o piloto em 1 centro: medir tempo até encaminhamento e taxa de inclusão.
3. Validar o **preço** com 3–5 patrocinadores/CROs, que é a principal premissa do SOM.
4. Contratos com cláusulas-padrão ANPD com a TypeSafe e o provedor do LLM, ou modelo hospedado no Brasil.
5. Confirmar na fonte primária os custos de recrutamento citados pelo Tufts.
