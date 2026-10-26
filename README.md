# Renomear fechamentos PDF

Aplicativo desktop em Python que seleciona uma pasta, lê o campo `Data: DD/MM/AAAA`
na primeira página de cada PDF e apresenta uma prévia de `FECHAMENTO DD-MM.pdf`.
Após conferir a prévia, clique em **Renomear arquivos** e confirme.

## Aba Extração: automação do Shop9 no Windows

A janela tem as abas **Renomeação** e **Extração**. A extração controla o mouse
e o teclado para repetir o fluxo do Shop9 a cada dia do período inclusivo.

O destino é fixo: `C:\Users\Luxottica\Desktop\Teste de Renomear`, com Caixa `01`
e formato PDF. O fluxo está documentado em [SHOP9.md](SHOP9.md).

### Primeira configuração

1. Abra e autentique o Shop9. Deixe apenas uma instância aberta, na tela inicial.
2. No aplicativo, abra **Extração → Configurar cliques do Shop9**.
3. Siga as instruções do assistente: ative a janela do Shop9, posicione o mouse
   no alvo indicado e pressione **F8**, sem clicar. O assistente registra a
   posição. Em seguida, faça manualmente o clique que a próxima etapa pedir.
4. Ao chegar à exportação, mantenha **formato PDF** selecionado e as opções de
   remover cabeçalho/rodapé e exportar somente dados para Excel desmarcadas.
5. Registre também o X da exportação e o X da prévia. Se a exportação fecha
   automaticamente após Exportar, use **Pular** na etapa de fechar exportação.
6. Ao concluir, feche a prévia e os filtros e volte à tela inicial do Shop9.

Os cliques ficam salvos em `%LOCALAPPDATA%\FechamentoPDF\shop9.json`. Nenhuma
senha é solicitada ou armazenada. Os pontos são relativos à janela identificada
por título, classe e processo; seu tamanho precisa permanecer igual ao da
configuração. Reconfigure se mudar a resolução, escala do Windows ou layout.
As janelas precisam pertencer ao mesmo processo do Shop9.

### Extrair

Selecione datas inicial e final e clique em **Extrair**. Para um único dia,
selecione a mesma data nos dois campos. Comece testando um dia com movimento.
Após confirmar, há cinco segundos para deixar o Shop9 pronto. Não use mouse
ou teclado durante a execução. **ESC** interrompe, e o botão **Parar** também
solicita a interrupção. Se interromper, confira as janelas e volte à tela inicial
antes de reiniciar.

O aplicativo preenche Caixa `01` e a data, abre a prévia, exporta para um arquivo
temporário exclusivo na pasta fixa e aguarda até 60 segundos pelo PDF. Confere
a data completa (incluindo o ano) no conteúdo antes de renomear para
`FECHAMENTO DD-MM.pdf`. Fecha as janelas configuradas e segue para o próximo dia.
Arquivos finais já existentes são preservados e pulados; não se presume que
eles pertencem à nova execução. Um PDF temporário com falha fica na pasta com
prefixo `_shop9_` para conferência. O limite por execução é 366 dias, sem nomes
repetidos entre anos.

A extração interrompe se a janela não for identificada, o tamanho mudar, a data
do PDF divergir ou o arquivo não aparecer. Dias sem movimento e mensagens do
Shop9 ainda precisam de validação no computador do usuário; uma mensagem
inesperada interrompe o fluxo e deve ser conferida manualmente.

## Windows: abrir com dois cliques

1. Instale [Python 3.10 ou superior](https://www.python.org/downloads/windows/),
   com Tcl/Tk habilitado e a opcao **Add Python to PATH** marcada.
2. Extraia todos os arquivos do ZIP para uma pasta no computador.
3. Dê dois cliques em **ABRIR.bat**. Na primeira vez, o aplicativo cria seu
   ambiente local `.venv` e instala as dependências pela internet. Nas próximas
   vezes, reutiliza a instalação.
4. Clique em **Selecionar pasta**, escolha a pasta dos PDFs e confira a prévia.
5. Clique em **Renomear arquivos** e confirme a operação.

O pacote contém código Python e um iniciador para Windows; não é um executável
independente. A janela de terminal permanece aberta durante o uso para mostrar
eventuais erros. A interface, o iniciador e os cliques no Shop9 ainda precisam
ser validados no Windows. Em Linux passaram nove testes de lógica com interação
simulada, além da conferência do fluxo usando o PDF de exemplo real. Isso não
substitui a validação da automação no Shop9.

## Executar pelo terminal

Requer Python 3.10 ou superior com Tkinter.

```sh
python -m pip install -r requirements.txt
python app.py
```

No Windows, o instalador oficial do Python inclui Tkinter. Em Ubuntu/Debian,
instale também o pacote `python3-tk` se necessário.

Para verificar a lógica de extração sem interagir com o Shop9:

```sh
python -m unittest -v test_shop9
```

Os documentos são processados localmente, sem envio para serviços externos.
A data do rodapé não é usada. Apenas PDFs diretamente na pasta selecionada são
processados; PDFs digitalizados sem texto precisam de OCR e não são renomeados.
PDFs ilegíveis, datas inválidas, campos ambíguos e conflitos de nomes são
exibidos na lista. Nenhum arquivo existente é sobrescrito. Dois PDFs com a mesma
data (inclusive de anos diferentes) ficam pendentes para resolução manual.

A renomeação segura usa hard links na própria pasta. Se o sistema de arquivos
não oferecer esse recurso, o aplicativo informa a falha e mantém o original.
