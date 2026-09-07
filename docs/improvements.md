# Especificação das melhorias pendentes

Este documento detalha as tarefas de comunicação e confiabilidade listadas em
`docs/tasks.md`. Cada implementação deve atualizar os testes e registrar no
log os dados necessários para análise posterior.

## 1. Retries e circuit breaker do provedor

### Problema

Falhas transitórias do provedor podem transformar uma decisão válida em
`wait`, reduzindo a capacidade de sobrevivência do agente.

### Implementação esperada

- Usar no máximo duas novas tentativas por decisão.
- Aplicar backoff entre tentativas.
- Repetir somente erros classificados como transitórios.
- Registrar tentativa, duração, erro e resultado final.
- Após falhas consecutivas, permitir fallback para outro modelo configurado
  ou para a ação segura.

### Critérios de aceitação

- A simulação não é encerrada por uma falha do provedor.
- Uma resposta válida após retry é executada normalmente.
- Falha definitiva gera evento de falha e fallback.
- Testes cobrem sucesso inicial, sucesso após retry e falha definitiva.

## 2. Timeout e latência por agente

### Implementação esperada

- Configurar timeout individual por agente ou modelo.
- Cancelar a requisição quando o limite for excedido.
- Registrar timeout e duração no evento de falha.
- Expor latência mínima, máxima e média nos relatórios.

### Critérios de aceitação

- Uma requisição lenta não bloqueia indefinidamente a rodada.
- O fallback é executado após timeout.
- Testes cobrem timeout e registro da duração.

## 3. Validação completa de ações

### Implementação esperada

Validar, antes da execução:

- formato e campos obrigatórios do JSON;
- ação suportada;
- quantidade positiva e disponível;
- localização atual e destino válido;
- agente destinatário existente e vivo;
- destinatário de mensagem válido;
- pré-condições da ação, como pesquisar antes de coletar.

### Critérios de aceitação

- Nenhuma ação inválida altera o estado do ambiente.
- Toda rejeição gera evento explicativo.
- O agente recebe o motivo da rejeição na observação seguinte.
- Existem testes para cada classe de argumento inválido.

## 4. Intenção versus ação executada

### Implementação esperada

Manter separados no log:

- decisão declarada pelo agente;
- validação da decisão;
- ação efetivamente executada;
- resultado ou motivo da rejeição.

### Critérios de aceitação

- É possível reconstruir a diferença entre intenção e resultado a partir do
  JSONL.
- Mensagens do agente não são tratadas como prova de que uma ação ocorreu.

## 5. Estado de coordenação e acordos

### Implementação esperada

Criar estado compartilhado e limitado para registrar:

- alimento descoberto por local;
- reservas e agente beneficiário;
- alimento coletado e consumido;
- necessidade estimada de cada agente;
- acordos públicos e privados.

Cada acordo deve possuir criador, destinatário, rodada de criação, status,
validade e motivo de encerramento.

### Critérios de aceitação

- Reservas não podem exceder o alimento disponível.
- Coleta, consumo ou morte invalidam ou ajustam reservas afetadas.
- Acordos podem ser confirmados, cumpridos, quebrados ou expirados.
- O estado ativo é incluído nas observações seguintes sem crescimento
  ilimitado do prompt.

## 6. Confirmação e resultado das mensagens

### Implementação esperada

- Diferenciar mensagem enviada, entregue, lida e confirmada.
- Identificar mensagens por um ID único.
- Informar ao remetente quando o destinatário confirmar ou rejeitar um acordo.
- Expirar mensagens e acordos após prazo configurável.

### Critérios de aceitação

- O remetente não assume cumprimento sem confirmação.
- Mensagens privadas continuam visíveis somente ao destinatário correto.
- Testes cobrem entrega, confirmação, rejeição e expiração.

## 7. Comportamento emergencial de sobrevivência

### Implementação esperada

Quando a fome estiver próxima do limite e a decisão LLM falhar, executar uma
política determinística configurável, priorizando:

1. comer alimento disponível no inventário;
2. coletar alimento já pesquisado;
3. pesquisar ou mover-se para uma localização promissora;
4. usar `wait` somente quando não houver alternativa válida.

### Critérios de aceitação

- O agente não escolhe `wait` quando possui alimento utilizável no inventário.
- A política respeita as pré-condições do ambiente.
- Testes cobrem cada nível de emergência.

## 8. Compatibilidade específica por modelo

### Implementação esperada

Permitir configurar por agente:

- modelo/preset;
- temperatura;
- limite de tokens;
- timeout;
- suporte a Structured Outputs;
- modelo de fallback.

Documentar incompatibilidades conhecidas sem expor credenciais.

### Critérios de aceitação

- Cada agente usa a configuração atribuída a ele.
- Parâmetros enviados ao provedor aparecem nos testes de requisição.
- Um modelo incompatível é detectado antes ou durante a execução e gera
  diagnóstico claro.

## 9. Métricas de cooperação e relatórios

### Implementação esperada

Adicionar métricas por agente e por rodada para:

- acordos criados, confirmados, cumpridos, quebrados e expirados;
- alimento reservado, coletado, transferido e consumido;
- mensagens enviadas e confirmadas;
- ações inválidas e fallbacks;
- latência e falhas do LLM;
- sobrevivência, fome e causa da morte.

### Critérios de aceitação

- Os resultados podem ser comparados por agente, modelo, seed e cenário.
- O relatório distingue falha do modelo, falha de validação e falha de
  estratégia.
- Testes verificam os contadores a partir de um cenário determinístico.

## Ordem sugerida de implementação

1. Validação completa de ações.
2. Separação entre intenção e ação executada.
3. Retries, timeout e fallback de modelo.
4. Política emergencial de sobrevivência.
5. Estado de coordenação e acordos.
6. Confirmação de mensagens.
7. Compatibilidade específica por modelo.
8. Métricas e relatórios.
