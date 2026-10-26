# Renomear fechamentos PDF

Aplicativo desktop em Python que seleciona uma pasta, lê o campo `Data: DD/MM/AAAA`
na primeira página de cada PDF e apresenta uma prévia de `FECHAMENTO DD-MM.pdf`.
Após conferir a prévia, clique em **Renomear arquivos** e confirme.

## Aba Extração (interface inicial)

A janela agora tem as abas **Renomeação** e **Extração**. Em Extração, selecione
as datas inicial e final pelo calendário, escolha a pasta de destino e utilize
o botão **Extrair**. Para um único dia, use a mesma data nos dois campos.

A integração de extração ainda depende da identificação do sistema de origem
e dos passos necessários para gerar o relatório. Por enquanto, o botão valida
as datas e informa essa pendência; não gera, baixa ou salva relatórios.

## Windows: abrir com dois cliques

1. Instale [Python 3.10 ou superior](https://www.python.org/downloads/windows/),
   com Tcl/Tk habilitado e a opcao **Add Python to PATH** marcada.
2. Extraia todos os arquivos do ZIP para uma pasta no computador.
3. Dê dois cliques em **ABRIR.bat**. Na primeira vez, o aplicativo cria seu
   ambiente local `.venv` e instala a dependência pela internet. Nas próximas
   vezes, reutiliza a instalação.
4. Clique em **Selecionar pasta**, escolha a pasta dos PDFs e confira a prévia.
5. Clique em **Renomear arquivos** e confirme a operação.

O pacote contém código Python e um iniciador para Windows; não é um executável
independente. A janela de terminal permanece aberta durante o uso para mostrar
eventuais erros. A interface e o iniciador precisam ser validados no Windows;
a extração da data e a renomeação foram verificadas em Linux com o PDF de exemplo.

## Executar pelo terminal

Requer Python 3.10 ou superior com Tkinter.

```sh
python -m pip install -r requirements.txt
python app.py
```

No Windows, o instalador oficial do Python inclui Tkinter. Em Ubuntu/Debian,
instale também o pacote `python3-tk` se necessário.

Os documentos são processados localmente, sem envio para serviços externos.
A data do rodapé não é usada. Apenas PDFs diretamente na pasta selecionada são
processados; PDFs digitalizados sem texto precisam de OCR e não são renomeados.
PDFs ilegíveis, datas inválidas, campos ambíguos e conflitos de nomes são
exibidos na lista. Nenhum arquivo existente é sobrescrito. Dois PDFs com a mesma
data (inclusive de anos diferentes) ficam pendentes para resolução manual.

A renomeação segura usa hard links na própria pasta. Se o sistema de arquivos
não oferecer esse recurso, o aplicativo informa a falha e mantém o original.
