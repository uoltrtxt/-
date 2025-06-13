import os, psutil, openai, threading
import tkinter as tk
from tkinter import ttk, scrolledtext

# 환경 변수에서 API 키 로드
openai.api_key = os.environ.get("OPENAI_API_KEY")

# --- GUI 초기화 ---
root = tk.Tk()
root.title("Process and Network Monitor")
root.geometry("800x600")
notebook = ttk.Notebook(root)
notebook.pack(fill='both', expand=True)

# 탭 프레임 생성
frame_proc = ttk.Frame(notebook)
frame_net  = ttk.Frame(notebook)
notebook.add(frame_proc, text="실행중인 것들")
notebook.add(frame_net,  text="네트워크 정보")

# --- 탭1: 프로세스 목록 ---
proc_list   = tk.Listbox(frame_proc)
proc_list.pack(side='left', fill='both', expand=True, padx=5, pady=5)
proc_detail = scrolledtext.ScrolledText(frame_proc, width=50)
proc_detail.pack(side='right', fill='both', expand=True, padx=5, pady=5)

# --- 탭2: 네트워크 연결 목록 ---
net_list   = tk.Listbox(frame_net)
net_list.pack(side='left', fill='both', expand=True, padx=5, pady=5)
net_detail = scrolledtext.ScrolledText(frame_net, width=50)
net_detail.pack(side='right', fill='both', expand=True, padx=5, pady=5)

# 언어 선택 옵션
lang_var = tk.StringVar(value='ko')  # 'ko' or 'en'
lang_frame = ttk.Frame(root)
ttk.Radiobutton(lang_frame, text="한국어", variable=lang_var, value='ko').pack(side='left')
ttk.Radiobutton(lang_frame, text="English", variable=lang_var, value='en').pack(side='left')
lang_frame.pack(pady=5)

# 프로세스 목록 초기화
for proc in psutil.process_iter(['pid','name']):
    name = proc.info['name'] or "<unknown>"
    pid  = proc.info['pid']
    proc_list.insert('end', f"{name} (PID {pid})")

# 네트워크 목록 초기화
for conn in psutil.net_connections(kind='inet'):
    l = f"{conn.laddr.ip}:{conn.laddr.port}"
    r = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "-"
    pname = ""
    if conn.pid:
        try:
            pname = psutil.Process(conn.pid).name()
        except:
            pname = "<ended>"
    net_list.insert('end', f"{pname} (PID {conn.pid}) {l} → {r} [{conn.status}]")

# 프로세스 선택 시 GPT 분석
def on_proc_select(event):
    sel = proc_list.curselection()
    if not sel: return
    idx  = sel[0]
    text = proc_list.get(idx)
    pid  = int(text.split("PID")[1].split(")")[0])

    def task():
        try:
            p = psutil.Process(pid)
            info = {
                "name": p.name(),
                "pid": pid,
                "cpu": p.cpu_percent(interval=0.1),
                "mem": p.memory_info().rss / (1024*1024)
            }
            if lang_var.get() == 'ko':
                prompt = (
                    f"프로세스 '{info['name']}' (PID {pid})\n"
                    f"- 역할: 무엇을 하는 프로그램인가?\n"
                    f"- 언어: 어떤 언어로 작성되었을까?\n"
                    f"- 자원: CPU {info['cpu']}%, 메모리 {info['mem']:.1f}MB 사용"
                )
            else:
                prompt = (
                    f"Process '{info['name']}' (PID {pid})\n"
                    f"- Function: What does it do?\n"
                    f"- Language: Likely code language?\n"
                    f"- Resources: CPU {info['cpu']}%, Memory {info['mem']:.1f}MB"
                )

            # v1 API 호출
            resp = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role":"user","content":prompt}]
            )
            ans = resp.choices[0].message.content.strip()
        except Exception as e:
            ans = f"오류 발생: {e}"

        proc_detail.after(0, lambda: proc_detail.insert('end', f"[{info['name']}]\n{ans}\n\n"))

    threading.Thread(target=task, daemon=True).start()

# 네트워크 선택 시 GPT 분석
def on_net_select(event):
    sel = net_list.curselection()
    if not sel: return
    text = net_list.get(sel[0]).split()
    pname, laddr, _, raddr, status = text[0], text[2], text[3], text[4], text[-1].strip('[]')

    def task():
        if lang_var.get() == 'ko':
            prompt = (
                f"프로세스 '{pname}'의 연결: {laddr} → {raddr} 상태 {status}\n"
                f"이 통신의 목적과 원격 서버 역할은?"
            )
        else:
            prompt = (
                f"Process '{pname}' connection: {laddr} -> {raddr} status {status}\n"
                f"What is the purpose and role of the remote server?"
            )
        try:
            resp = openai.chat.completions.create(
                model="o4-mini",
                messages=[{"role":"user","content":prompt}]
            )
            ans = resp.choices[0].message.content.strip()
        except Exception as e:
            ans = f"Error: {e}"

        net_detail.after(0, lambda: net_detail.insert('end', f"[{pname}]\n{ans}\n\n"))

    threading.Thread(target=task, daemon=True).start()

proc_list.bind("<Double-Button-1>", on_proc_select)
net_list.bind("<Double-Button-1>", on_net_select)

root.mainloop()





