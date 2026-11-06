"""Windows administration window. Reuses the template's native tray and Python web service model."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import webbrowser
from .settings import Settings
from .runtime import make_server, run_server


class BackendController:
    def __init__(self):
        self.server = None
        self.thread = None
        self.error = None

    def start(self, directory, port):
        if self.running: return
        if not 1024 <= int(port) <= 65535: raise ValueError("Porta inválida.")
        self.server = make_server(Settings(data_dir=Path(directory).resolve(), port=int(port), host="127.0.0.1"))
        self.error = None
        def serve():
            try: run_server(self.server)
            except BaseException as exc: self.error = type(exc).__name__
        self.thread = threading.Thread(target=serve, name="ResellerAPI", daemon=True)
        self.thread.start()

    def stop(self):
        if self.server: self.server.should_exit = True
        if self.thread: self.thread.join(timeout=45)
        if self.thread and self.thread.is_alive():
            raise RuntimeError("Há uma operação em encerramento. Não inicie outra instância nesta pasta.")
        self.server = self.thread = None

    @property
    def running(self):
        return bool(self.thread and self.thread.is_alive() and self.server and self.server.started)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--background", action="store_true")
    args = parser.parse_args(argv)
    home = Path(os.getenv("LOCALAPPDATA", str(Path.home()))) / "ResellerManager"
    home.mkdir(parents=True, exist_ok=True)
    preferences = home / "desktop.json"
    config = {}
    if preferences.exists():
        try: config = json.loads(preferences.read_text(encoding="utf-8"))
        except (ValueError, OSError): pass
    root = tk.Tk(); root.title("Reseller Manager | Administração"); root.geometry("820x600"); root.minsize(700, 520)
    root.configure(bg="#f3f6f9")
    style = ttk.Style(root); style.theme_use("clam")
    style.configure("TFrame", background="#f3f6f9")
    style.configure("TLabel", background="#f3f6f9", foreground="#203a49", font=("Segoe UI", 10))
    style.configure("TButton", padding=(14, 9), font=("Segoe UI", 10))
    style.configure("Title.TLabel", font=("Segoe UI", 22, "bold"), foreground="#095c76")
    icon = Path(__file__).resolve().parent / "static/icon.ico"
    if sys.platform == "win32": root.iconbitmap(str(icon))
    frame = ttk.Frame(root, padding=30); frame.pack(fill="both", expand=True)
    ttk.Label(frame, text="Reseller Manager", style="Title.TLabel").pack(anchor="w")
    ttk.Label(frame, text="API de revendas • Clientes • Renovações • Integrações").pack(anchor="w", pady=(5, 22))
    status = tk.StringVar(value="Iniciando serviço local…")
    ttk.Label(frame, textvariable=status).pack(anchor="w", pady=(0, 14))
    tabs = ttk.Notebook(frame); tabs.pack(fill="both", expand=True)
    service = ttk.Frame(tabs, padding=20); settings = ttk.Frame(tabs, padding=20); support = ttk.Frame(tabs, padding=20)
    tabs.add(service, text="Serviço local"); tabs.add(settings, text="Configuração"); tabs.add(support, text="Dados e segurança")
    data = tk.StringVar(value=config.get("data", str(home / "data")))
    port = tk.StringVar(value=str(config.get("port", 48190)))
    backend = BackendController(); tray = None; stopped = False
    def url(): return "http://127.0.0.1:" + port.get()
    def open_panel(): webbrowser.open(url())
    def show(): root.deiconify(); root.lift(); root.focus_force()
    def start():
        try:
            if backend.thread and backend.thread.is_alive(): return
            backend.start(data.get(), int(port.get()))
        except Exception as exc: messagebox.showerror("Reseller Manager", str(exc), parent=root)
    def stop():
        status.set("Encerrando com segurança…")
        def work():
            try: backend.stop()
            except RuntimeError: pass
        threading.Thread(target=work, daemon=True).start()
    def save():
        try:
            if backend.thread and backend.thread.is_alive(): raise ValueError("Pare o serviço antes de mudar a pasta ou porta.")
            n=int(port.get())
            if not 1024 <= n <= 65535: raise ValueError("Porta inválida.")
            preferences.write_text(json.dumps({"data": str(Path(data.get()).resolve()), "port": n}, indent=2), encoding="utf-8")
            messagebox.showinfo("Reseller Manager", "Configuração salva.", parent=root)
        except (ValueError,OSError) as exc: messagebox.showerror("Reseller Manager", str(exc), parent=root)
    def copy_token():
        file=Path(data.get())/"admin.token"
        if not file.exists(): return messagebox.showwarning("Token", "Inicie o serviço para gerar o token inicial.", parent=root)
        root.clipboard_clear(); root.clipboard_append(file.read_text().strip())
        messagebox.showinfo("Token copiado", "Use este token no painel local. Não é a credencial do kOfficePanel. Limpe sua área de transferência após utilizar.", parent=root)
    def open_data():
        path=Path(data.get()); path.mkdir(parents=True,exist_ok=True)
        if sys.platform=="win32": os.startfile(path)
        else: webbrowser.open(path.as_uri())
    def exit_app():
        nonlocal stopped
        if backend.thread and backend.thread.is_alive():
            if not messagebox.askyesno("Encerrar", "O serviço será parado e os agendamentos não executarão enquanto estiver fechado. Encerrar?", parent=root): return
            status.set("Encerrando; preservando a fila…"); root.update_idletasks()
            try: backend.stop()
            except RuntimeError as exc: messagebox.showerror("Serviço", str(exc), parent=root); return
        stopped=True
        if tray: tray.close()
        root.destroy()
    ttk.Label(service, text="O painel abre no navegador. Esta janela mantém o servidor local ativo.\nO serviço escuta somente em 127.0.0.1 no modo desktop.", justify="left").pack(anchor="w", pady=(0, 20))
    for label, command in [("Abrir painel",open_panel),("Copiar token de primeiro acesso",copy_token),("Iniciar serviço",start),("Parar serviço",stop)]:
        ttk.Button(service,text=label,command=command).pack(anchor="w",pady=5)
    ttk.Label(settings,text="Pasta privada de dados").pack(anchor="w")
    ttk.Entry(settings,textvariable=data,width=70).pack(fill="x",pady=7)
    def choose():
        chosen=filedialog.askdirectory(parent=root,initialdir=data.get())
        if chosen:data.set(chosen)
    ttk.Button(settings,text="Selecionar pasta…",command=choose).pack(anchor="w")
    ttk.Label(settings,text="Porta local").pack(anchor="w",pady=(15,0));ttk.Entry(settings,textvariable=port,width=12).pack(anchor="w",pady=7)
    ttk.Button(settings,text="Salvar configuração",command=save).pack(anchor="w",pady=12)
    ttk.Label(support,text="Faça backup da pasta inteira com o serviço parado.\nO banco e master.key precisam permanecer juntos.\nNunca publique admin.token, master.key ou o banco no Git.\n\nLogs locais não incluem URLs de chamadas ao fornecedor.\nUma operação interrompida exige conferência, não reenvio.",justify="left").pack(anchor="w",pady=(0,15))
    ttk.Button(support,text="Abrir pasta de dados",command=open_data).pack(anchor="w",pady=5)
    ttk.Button(support,text="Documentação da API",command=lambda:webbrowser.open(url()+"/docs")).pack(anchor="w",pady=5)
    ttk.Label(frame,text="v0.1.0 · Wallace Kleiton — WWSoftware’s").pack(anchor="w",pady=(17,0))
    if sys.platform=="win32":
        try:
            from .desktop_tray import Tray
            tray=Tray(root,icon,{1:("Abrir administração",show),2:("Abrir painel",open_panel),3:("Sair",exit_app)},str(os.getpid()))
        except Exception: tray=None
    def close():
        if tray and tray.available: root.withdraw()
        else: exit_app()
    root.protocol("WM_DELETE_WINDOW",close)
    def poll():
        if stopped:return
        if backend.running:status.set("Serviço ativo — "+url())
        elif backend.thread and backend.thread.is_alive():status.set("Iniciando / encerrando serviço…")
        elif backend.error:status.set("Serviço indisponível. Confira porta, pasta e logs locais.")
        else:status.set("Serviço parado")
        root.after(700,poll)
    start();poll()
    if args.background and tray and tray.available:root.withdraw()
    root.mainloop()
