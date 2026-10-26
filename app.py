"""Aplicativo local para renomear relatórios PDF pela data do cabeçalho."""

import os
import re
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from pypdf import PdfReader


def target_name(path):
    reader = PdfReader(path)
    if not reader.pages:
        raise ValueError('PDF sem páginas.')
    text = reader.pages[0].extract_text(extraction_mode='layout') or ''
    dates = re.findall(r'\bData\s*:\s*(\d{2}/\d{2}/\d{4})\b', text, re.IGNORECASE)
    if len(set(dates)) != 1:
        raise ValueError('Campo Data ausente ou ambíguo; arquivo preservado.')
    date = datetime.strptime(dates[0], '%d/%m/%Y')
    return f'FECHAMENTO {date:%d-%m}.pdf'


def rename_safely(source, destination):
    # A criação exclusiva impede sobrescrever outro arquivo, inclusive se ele
    # surgir depois da prévia. Hard links mantêm o conteúdo original intacto.
    os.link(source, destination)
    try:
        source.unlink()
    except OSError:
        destination.unlink()
        raise


class App:
    def __init__(self, root):
        self.root = root
        root.title('Renomear fechamentos PDF')
        root.geometry('900x500')
        self.rows = []
        self.folder = tk.StringVar(value='Selecione a pasta com os PDFs.')
        ttk.Label(root, textvariable=self.folder, padding=12).pack(anchor='w')
        toolbar = ttk.Frame(root, padding=12)
        toolbar.pack(fill='x')
        self.choose = ttk.Button(toolbar, text='Selecionar pasta', command=self.select)
        self.choose.pack(side='left')
        self.rename = ttk.Button(toolbar, text='Renomear arquivos', command=self.apply, state='disabled')
        self.rename.pack(side='left', padx=12)
        ttk.Label(root, text='Usa o campo Data do cabeçalho. PDFs de subpastas não são incluídos.', padding=12).pack(anchor='w')
        self.table = ttk.Treeview(root, columns=('original', 'new', 'status'), show='headings')
        for key, title in [('original', 'Arquivo atual'), ('new', 'Novo nome'), ('status', 'Situação')]:
            self.table.heading(key, text=title)
            self.table.column(key, width=280)
        self.table.pack(fill='both', expand=True, padx=12, pady=12)
        self.status = tk.StringVar(value='Nenhum arquivo será enviado para a internet.')
        ttk.Label(root, textvariable=self.status, padding=12).pack(anchor='w')

    def select(self):
        folder = filedialog.askdirectory(title='Selecione a pasta dos PDFs')
        if not folder:
            return
        self.rows = []
        self.folder.set(folder)
        self.choose.config(state='disabled')
        self.rename.config(state='disabled')
        self.status.set('Lendo PDFs…')
        self.table.delete(*self.table.get_children())
        threading.Thread(target=self.scan, args=(Path(folder),), daemon=True).start()

    def scan(self, folder):
        rows = []
        try:
            for path in sorted(folder.iterdir()):
                if not path.is_file() or path.suffix.lower() != '.pdf':
                    continue
                try:
                    name = target_name(path)
                    state = 'Já renomeado' if path.name == name else 'Pronto'
                    rows.append([path, name, state])
                except Exception as exc:
                    rows.append([path, '', f'Não processado: {exc}'])
            counts = {}
            existing = {p.name.casefold() for p in folder.iterdir()}
            for _, name, _ in rows:
                counts[name.casefold()] = counts.get(name.casefold(), 0) + 1
            for path, name, state in rows:
                if state == 'Pronto' and (name.casefold() in existing or counts[name.casefold()] > 1):
                    state = 'Conflito de nome; arquivo preservado'
                self.root.after(0, self.add_row, path, name, state)
            self.root.after(0, self.finish_scan, None)
        except Exception as exc:
            self.root.after(0, self.finish_scan, str(exc))

    def add_row(self, path, name, state):
        item = self.table.insert('', 'end', values=(path.name, name, state))
        self.rows.append((item, path, name, state))

    def finish_scan(self, error):
        self.choose.config(state='normal')
        ready = sum(row[3] == 'Pronto' for row in self.rows)
        self.rename.config(state='normal' if ready else 'disabled')
        self.status.set(f'{len(self.rows)} PDF(s) encontrado(s); {ready} pronto(s) para renomear.' if not error else f'Erro ao ler pasta: {error}')

    def apply(self):
        ready = [row for row in self.rows if row[3] == 'Pronto']
        if not messagebox.askyesno('Confirmar renomeação', f'Renomear {len(ready)} PDF(s) conforme a prévia?'):
            return
        success = 0
        for item, path, name, _ in ready:
            try:
                # Revalida a data caso o PDF tenha mudado desde a leitura.
                if target_name(path) != name:
                    raise ValueError('A data mudou desde a prévia. Selecione a pasta novamente.')
                rename_safely(path, path.with_name(name))
                state = 'Renomeado'
                success += 1
            except Exception as exc:
                state = f'Não renomeado: {exc}'
            self.table.item(item, values=(path.name, name, state))
        self.rename.config(state='disabled')
        self.rows = []
        self.status.set(f'{success} de {len(ready)} arquivo(s) renomeado(s). Selecione a pasta novamente para atualizar.')

if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()
