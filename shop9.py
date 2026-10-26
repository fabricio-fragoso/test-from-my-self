"""Automação Windows calibrada no computador que executa o Shop9."""

import json
import os
import threading
import time
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

STEPS = (
    ('financeiro', 'Na tela inicial do Shop9, aponte para Financeiro.'),
    ('caixa_menu', 'Clique em Financeiro. Aponte para Caixa.'),
    ('relatorios', 'Clique em Caixa. Aponte para Relatórios.'),
    ('relatorio_caixa', 'Clique em Relatórios. Aponte para Relatório de caixa.'),
    ('caixa', 'Abra Relatório de caixa. Aponte para a parte editável do campo Caixa.'),
    ('data', 'Preencha Caixa com 01. Aponte para o dia no campo Data.'),
    ('imprimir', 'Informe uma data com movimento. Aponte para Imprimir.'),
    ('seta', 'Clique em Imprimir, aguarde a prévia e aponte para a seta verde.'),
    ('salvar', 'Clique na seta verde. Com formato PDF, aponte para o texto de Salvar em.'),
    ('exportar', 'Aponte para Exportar. Não é necessário exportar durante a configuração.'),
    ('fechar_exportacao', 'Aponte para o X da janela Exportação de Relatório. Se ela fecha sozinha após exportar, use Pular.'),
    ('fechar_previa', 'Feche a janela de exportação. Aponte para o X da PRÉVIA do relatório, sem fechar o Shop9.'),
)


def config_path():
    return Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'FechamentoPDF' / 'shop9.json'


def validate_config(config):
    if config.get('version') != 1:
        raise ValueError('Configuração incompatível. Configure os cliques novamente.')
    for key, _ in STEPS:
        point = config.get('points', {}).get(key)
        if key == 'fechar_exportacao' and point is None:
            continue
        if not isinstance(point, dict) or not point.get('title') or not point.get('class'):
            raise ValueError(f'Clique não configurado: {key}.')
        if not all(isinstance(point.get(k), int) for k in ('x', 'y', 'width', 'height')):
            raise ValueError(f'Posição inválida: {key}.')
        if not (0 <= point['x'] < point['width'] and 0 <= point['y'] < point['height']):
            raise ValueError(f'Posição fora da janela: {key}.')
    return config


def load_config():
    return validate_config(json.loads(config_path().read_text(encoding='utf-8')))


def save_config(points):
    config = validate_config({'version': 1, 'points': points})
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


class Cancelled(Exception):
    pass


class WindowsDriver:
    def __init__(self, stop=None):
        if os.name != 'nt':
            raise RuntimeError('A automação do Shop9 está disponível somente no Windows.')
        from windows_native import NativeWindows
        self.native = NativeWindows()
        self.stop = stop or threading.Event()
        self.pid = None

    def pressed(self, key):
        return self.native.pressed(key)

    def check_stop(self):
        if self.stop.is_set() or self.pressed(0x1B):
            raise Cancelled('Extração interrompida. Os PDFs já salvos foram preservados.')

    def pause(self, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.check_stop()
            self.stop.wait(min(0.1, max(0, deadline - time.monotonic())))

    def capture(self):
        x, y = self.native.cursor()
        handle = self.native.root_at(x, y)
        if handle != self.native.foreground():
            raise ValueError('Ative a janela do Shop9 antes de marcar o clique.')
        pid = self.native.pid(handle)
        if pid == os.getpid() or (self.pid is not None and pid != self.pid):
            raise ValueError('Aponte para uma janela do mesmo processo do Shop9.')
        title = self.native.title(handle)
        if not title:
            raise ValueError('Janela sem título. Não foi possível identificar o Shop9.')
        left, top, right, bottom = self.native.rectangle(handle)
        self.pid = pid
        return {'title': title, 'class': self.native.window_class(handle),
                'x': x - left, 'y': y - top, 'width': right - left, 'height': bottom - top}

    def locate(self, point, timeout=30):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.check_stop()
            matches = [handle for handle in self.native.windows()
                       if self.native.title(handle) == point['title']
                       and self.native.window_class(handle) == point['class']
                       and (self.pid is None or self.native.pid(handle) == self.pid)]
            if len(matches) > 1:
                raise RuntimeError('Há mais de uma janela compatível. Deixe apenas um Shop9 aberto.')
            if matches:
                handle = matches[0]
                self.native.restore(handle)
                left, top, right, bottom = self.native.rectangle(handle)
                if right - left != point['width'] or bottom - top != point['height']:
                    raise RuntimeError('O tamanho da janela mudou. Restaure o tamanho usado na configuração ou configure novamente.')
                self.pid = self.native.pid(handle)
                return handle
            self.pause(0.2)
        raise RuntimeError(f'Janela não encontrada: {point["title"]}. Confira a tela atual do Shop9.')

    def click(self, point):
        handle = self.locate(point)
        self.native.activate(handle)
        self.pause(0.2)
        if self.native.foreground() != handle:
            raise RuntimeError('Não foi possível ativar a janela do Shop9.')
        self.check_stop()
        left, top, _, _ = self.native.rectangle(handle)
        self.native.click(left + point['x'], top + point['y'])
        self.pause(0.8)
        return handle

    def fill(self, point, text):
        handle = self.click(point)
        self.check_stop()
        if self.native.foreground() != handle:
            raise RuntimeError('A janela ativa mudou. Extração interrompida antes de digitar.')
        self.native.select_all()
        self.pause(0.05)
        for char in text:
            self.check_stop()
            if self.native.foreground() != handle:
                raise RuntimeError('A janela ativa mudou durante a digitação. Extração interrompida.')
            self.native.type_character(char)
            self.pause(0.06)
        self.native.tab()
        self.pause(0.4)


def extract_period(start, end, folder, points, driver, read_date, publish, log):
    """Para cada dia, só publica o PDF após conferir a data completa no conteúdo."""
    folder = Path(folder)
    days = (end - start).days + 1
    if days <= 0 or days > 366:
        raise ValueError('Selecione um período de 1 a 366 dias.')
    dates = [start + timedelta(days=index) for index in range(days)]
    names = [f'FECHAMENTO {day:%d-%m}.pdf' for day in dates]
    if len(set(names)) != len(names):
        raise ValueError('O período contém dias de anos diferentes que geram o mesmo nome.')
    folder.mkdir(parents=True, exist_ok=True)
    pending = [(day, folder / name) for day, name in zip(dates, names) if not (folder / name).exists()]
    skipped = days - len(pending)
    log(f'{len(pending)} dia(s) pendente(s); {skipped} arquivo(s) existente(s) serão preservados.')
    if not pending:
        return 0, skipped
    log('Deixe o Shop9 na tela INICIAL. Início em 5 segundos. ESC interrompe.')
    driver.pause(5)
    for key in ('financeiro', 'caixa_menu', 'relatorios', 'relatorio_caixa'):
        driver.click(points[key])
    saved = 0
    for day, destination in pending:
        driver.check_stop()
        log(f'Extraindo {day:%d/%m/%Y} — Caixa 01…')
        driver.fill(points['caixa'], '01')
        # A máscara de data do Shop9 recebe os oito dígitos sem separadores.
        driver.fill(points['data'], day.strftime('%d%m%Y'))
        driver.click(points['imprimir'])
        driver.click(points['seta'])
        temporary = folder / f'_shop9_{uuid4().hex}.pdf'
        driver.fill(points['salvar'], str(temporary))
        driver.click(points['exportar'])
        deadline = time.monotonic() + 60
        last_error = None
        previous = None
        while True:
            driver.check_stop()
            try:
                stat = temporary.stat()
                signature = (stat.st_size, stat.st_mtime_ns)
                if not stat.st_size or signature != previous:
                    previous = signature
                    raise ValueError('Aguardando a escrita do PDF terminar.')
                actual_date = read_date(temporary)
            except Exception as exc:
                last_error = exc
            else:
                if actual_date != day:
                    raise RuntimeError(f'O PDF de {day:%d/%m/%Y} contém a data {actual_date:%d/%m/%Y}. '
                                       f'Extração parada; arquivo para conferência: {temporary}')
                break
            if time.monotonic() >= deadline:
                raise RuntimeError(f'PDF não confirmado em 60 segundos: {temporary}. '
                                   f'Confira o Shop9 e o campo Salvar em. Detalhe: {last_error}')
            driver.pause(0.5)
        publish(temporary, destination)
        saved += 1
        log(f'Salvo: {destination.name}')
        if points.get('fechar_exportacao') is not None:
            driver.click(points['fechar_exportacao'])
        driver.click(points['fechar_previa'])
    return saved, skipped
