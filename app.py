"""Aplicativo local para renomear relatórios PDF pela data do cabeçalho."""

import os
import calendar
import re
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from pypdf import PdfReader


def selected_period(start, end):
    start_date = datetime.strptime(start, '%d/%m/%Y').date()
    end_date = datetime.strptime(end, '%d/%m/%Y').date()
    if start_date > end_date:
        raise ValueError('A data inicial deve ser anterior ou igual à data final.')
    return start_date, end_date


class DatePicker(ttk.Frame):
    """Campo de data com calendário, sem dependências adicionais."""

    def __init__(self, parent):
        super().__init__(parent)
        self.value = tk.StringVar(value=datetime.now().strftime('%d/%m/%Y'))
        ttk.Entry(self, textvariable=self.value, width=14).pack(side='left')
        ttk.Button(self, text='Calendário', command=self.open_calendar).pack(side='left', padx=6)
        self.popup = None

    def open_calendar(self):
        if self.popup is not None and self.popup.winfo_exists():
            self.popup.lift()
            return
        try:
            current = datetime.strptime(self.value.get(), '%d/%m/%Y')
        except ValueError:
            current = datetime.now()
        self.year, self.month = current.year, current.month
        self.popup = tk.Toplevel(self)
        self.popup.title('Selecionar data')
        self.popup.transient(self.winfo_toplevel())
        self.popup.resizable(False, False)
        self.draw_calendar()

    def draw_calendar(self):
        for child in self.popup.winfo_children():
            child.destroy()
        header = ttk.Frame(self.popup, padding=8)
        header.pack(fill='x')
        ttk.Button(header, text='<', width=3, command=lambda: self.change_month(-1)).pack(side='left')
        ttk.Label(header, text=f'{self.month:02d}/{self.year:04d}', anchor='center', width=18).pack(side='left')
        ttk.Button(header, text='>', width=3, command=lambda: self.change_month(1)).pack(side='left')
        days = ttk.Frame(self.popup, padding=8)
        days.pack()
        for column, name in enumerate(('Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom')):
            ttk.Label(days, text=name, anchor='center').grid(row=0, column=column)
        for row, week in enumerate(calendar.monthcalendar(self.year, self.month), 1):
            for column, day in enumerate(week):
                if day:
                    ttk.Button(days, text=str(day), width=4,
                               command=lambda day=day: self.select_day(day)).grid(row=row, column=column)

    def change_month(self, step):
        index = (self.year - 1) * 12 + self.month - 1 + step
        if not 0 <= index < 9999 * 12:
            return
        self.year, month = divmod(index, 12)
        self.year += 1
        self.month = month + 1
        self.draw_calendar()

    def select_day(self, day):
        self.value.set(f'{day:02d}/{self.month:02d}/{self.year:04d}')
        self.popup.destroy()


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
        tabs = ttk.Notebook(root)
        tabs.pack(fill='both', expand=True)
        rename_tab = ttk.Frame(tabs)
        extraction_tab = ttk.Frame(tabs, padding=20)
        tabs.add(rename_tab, text='Renomeação')
        tabs.add(extraction_tab, text='Extração')
        self.build_extraction_tab(extraction_tab)
        self.rows = []
        self.folder = tk.StringVar(value='Selecione a pasta com os PDFs.')
        ttk.Label(rename_tab, textvariable=self.folder, padding=12).pack(anchor='w')
        toolbar = ttk.Frame(rename_tab, padding=12)
        toolbar.pack(fill='x')
        self.choose = ttk.Button(toolbar, text='Selecionar pasta', command=self.select)
        self.choose.pack(side='left')
        self.rename = ttk.Button(toolbar, text='Renomear arquivos', command=self.apply, state='disabled')
        self.rename.pack(side='left', padx=12)
        ttk.Label(rename_tab, text='Usa o campo Data do cabeçalho. PDFs de subpastas não são incluídos.', padding=12).pack(anchor='w')
        self.table = ttk.Treeview(rename_tab, columns=('original', 'new', 'status'), show='headings')
        for key, title in [('original', 'Arquivo atual'), ('new', 'Novo nome'), ('status', 'Situação')]:
            self.table.heading(key, text=title)
            self.table.column(key, width=280)
        self.table.pack(fill='both', expand=True, padx=12, pady=12)
        self.status = tk.StringVar(value='Nenhum arquivo será enviado para a internet.')
        ttk.Label(rename_tab, textvariable=self.status, padding=12).pack(anchor='w')

    def build_extraction_tab(self, tab):
        ttk.Label(tab, text='Extração de relatórios', font=('Segoe UI', 14, 'bold')).pack(anchor='w', pady=(0, 16))
        fields = ttk.Frame(tab)
        fields.pack(anchor='w')
        ttk.Label(fields, text='Data inicial').grid(row=0, column=0, sticky='w')
        ttk.Label(fields, text='Data final').grid(row=0, column=1, sticky='w', padx=(20, 0))
        self.start_date = DatePicker(fields)
        self.start_date.grid(row=1, column=0, pady=8, sticky='w')
        self.end_date = DatePicker(fields)
        self.end_date.grid(row=1, column=1, pady=8, padx=(20, 0), sticky='w')
        ttk.Label(tab, text='Para um único dia, selecione a mesma data nos dois campos.').pack(anchor='w', pady=(0, 16))
        self.extraction_folder = tk.StringVar(value='')
        ttk.Button(tab, text='Selecionar pasta de destino', command=self.select_extraction_folder).pack(anchor='w')
        ttk.Label(tab, textvariable=self.extraction_folder, wraplength=800).pack(anchor='w', pady=8)
        ttk.Button(tab, text='Extrair', command=self.extract).pack(anchor='w', pady=8)
        ttk.Label(tab, text='Aguardando definição do sistema de origem para habilitar a extração automática.',
                  wraplength=800).pack(anchor='w', pady=12)

    def select_extraction_folder(self):
        folder = filedialog.askdirectory(title='Onde salvar os relatórios?')
        if folder:
            self.extraction_folder.set(folder)

    def extract(self):
        try:
            selected_period(self.start_date.value.get(), self.end_date.value.get())
        except ValueError:
            messagebox.showerror('Verifique as datas', 'Informe datas válidas em DD/MM/AAAA, com a data inicial anterior ou igual à final.')
            return
        messagebox.showinfo('Extração pendente',
                            'O sistema de origem do relatório ainda precisa ser configurado. '
                            'Nenhum relatório foi extraído ou salvo.')

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
