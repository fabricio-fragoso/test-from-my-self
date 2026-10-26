# Fluxo de extração do Shop9

Etapas informadas pelo usuário e implementadas em `shop9.py`. A interação real
precisa ser configurada e validada no Shop9 do usuário. As capturas recebidas
mostram janelas com tamanhos diferentes: o assistente registra pontos relativos
às janelas no Windows, sem presumir as coordenadas das capturas.

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
   usando um nome temporário exclusivo `_shop9_<identificador>.pdf` na pasta
   `C:\Users\Luxottica\Desktop\Teste de Renomear`. Após validar a data no PDF,
   o aplicativo renomeia sem sobrescrever para `FECHAMENTO 25-10.pdf`, por exemplo.
7. Preservar cabeçalho e rodapé: **Não exportar Cabeçalho e Rodapé** deve
   continuar desmarcado. **Exportar somente dados para Excel** também deve
   permanecer desmarcado.
8. Clicar em **Exportar**.
9. O usuário confirmou que não aparece outra ação: o arquivo é exportado e
   basta fechar a janela. O assistente registra os fechamentos da exportação
   (opcional se já fechar automaticamente) e da prévia para retornar aos filtros.
10. Repetir a partir do preenchimento do Caixa e Data para o próximo dia.

## Pontos ainda a confirmar e validar

- Comportamento para dias sem movimentação.
- Validar o controle das janelas no Windows e a saída PDF de cada dia. Não
  sobrescrever documentos existentes nem considerar um clique como prova de
  que um relatório foi gerado. O app só conta como salvo um PDF cuja data
  completa foi conferida e cujo nome final foi criado sem sobrescrita.
