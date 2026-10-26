# Fluxo de extração do Shop9

Etapas informadas pelo usuário; a automação ainda não está implementada nem
validada no Shop9. As capturas recebidas mostram janelas com tamanhos diferentes,
portanto coordenadas absolutas de tela não podem ser presumidas estáveis.

1. Com o Shop9 aberto e autenticado, acessar **Financeiro → Caixa → Relatórios
   → Relatório de caixa**.
2. Preservar a filial já selecionada. Preencher **Caixa** sempre com `01`.
3. Para cada dia do período inclusivo escolhido no aplicativo, preencher
   **Data**. A captura mostra **Agrupamento: Por Data** e **Tipo: Normal com
   Sequência**; não foi solicitada alteração desses campos.
4. Clicar em **Imprimir** e aguardar a prévia do relatório.
5. Na barra superior da prévia, clicar na **seta verde**, que abre
   **Exportação de Relatório**.
6. Usar formato **PDF** e substituir **Salvar em** pelo caminho completo,
   por exemplo `C:\Users\Luxottica\Desktop\Teste de Renomear\FECHAMENTO 25-10.pdf`.
   O destino solicitado pelo usuário é sempre essa pasta.
7. Preservar cabeçalho e rodapé: **Não exportar Cabeçalho e Rodapé** deve
   continuar desmarcado. **Exportar somente dados para Excel** também deve
   permanecer desmarcado.
8. Clicar em **Exportar**.

## Pontos ainda a confirmar e validar

- O que aparece depois de Exportar: confirmação, abertura do PDF ou retorno à
  prévia. Mapear como voltar aos filtros para o próximo dia.
- Comportamento para dias sem movimentação.
- Validar o controle das janelas no Windows e a saída PDF de cada dia. Não
  sobrescrever documentos existentes nem considerar um clique como prova de
  que um relatório foi gerado.
