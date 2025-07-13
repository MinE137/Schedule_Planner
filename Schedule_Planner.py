import sys
import ctypes
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
import tkinter.font as tkfont
from tkcalendar import DateEntry, Calendar
import json
from datetime import datetime, timedelta
import calendar as calmodule
import os

# DPI 설정: Windows에서 고해상도 모니터 지원
if sys.platform.startswith('win'):
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

# 폰트 설정: 한국어 지원 및 크기 확대
def setup_default_font():
    default_font = tkfont.nametofont("TkDefaultFont")
    default_font.configure(family="Malgun Gothic", size=13)
    for font_name in ["TkTextFont", "TkHeadingFont", "TkMenuFont", "TkCaptionFont", "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont"]:
        tkfont.nametofont(font_name).configure(family="Malgun Gothic", size=13)

# 알림 사운드 재생
def play_notification():
    try:
        import winsound
        winsound.MessageBeep()
    except:
        pass

class TaskDialog(simpledialog.Dialog):
    def __init__(self, parent, title, start_val="09:00", end_val="10:00", task_val="", priority="Medium", category="General", recurring=False):
        self.start_val, self.end_val = start_val, end_val
        self.task_val, self.priority = task_val, priority
        self.category, self.recurring = category, recurring
        super().__init__(parent, title)

    def body(self, master):
        labels = ["시작:", "종료:", "할 일:", "우선순위:", "카테고리:", "반복:"]
        for i, text in enumerate(labels):
            ttk.Label(master, text=text).grid(row=i, column=0, padx=8, pady=8)
        self.start = ttk.Entry(master, width=12)
        self.start.insert(0, self.start_val); self.start.grid(row=0, column=1)
        self.end = ttk.Entry(master, width=12)
        self.end.insert(0, self.end_val); self.end.grid(row=1, column=1)
        self.task = ttk.Entry(master, width=55)
        self.task.insert(0, self.task_val); self.task.grid(row=2, column=1)
        self.pri_cb = ttk.Combobox(master, values=["High","Medium","Low"], width=10)
        self.pri_cb.set(self.priority); self.pri_cb.grid(row=3, column=1)
        self.cat_entry = ttk.Entry(master, width=30)
        self.cat_entry.insert(0, self.category); self.cat_entry.grid(row=4, column=1)
        self.rec_var = tk.BooleanVar(value=self.recurring)
        ttk.Checkbutton(master, variable=self.rec_var).grid(row=5, column=1)
        return self.start

    def apply(self):
        s, e = self.start.get().strip(), self.end.get().strip()
        t = self.task.get().strip()
        try:
            s_dt = datetime.strptime(s, '%H:%M')
            e_dt = datetime.strptime(e, '%H:%M')
            if s_dt >= e_dt:
                raise ValueError
        except:
            messagebox.showerror("오류", "시간 형식 오류 또는 시작 ≥ 종료")
            self.result = None
            return
        if not t:
            messagebox.showerror("오류", "할 일을 입력하세요")
            self.result = None
            return
        self.result = {
            'start': s,
            'end': e,
            'task': t,
            'priority': self.pri_cb.get(),
            'category': self.cat_entry.get().strip(),
            'recurring': self.rec_var.get()
        }

class SchedulerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        try:
            self.tk.call('tk','scaling',2.5)
        except:
            pass
        setup_default_font()
        self.title("Schedule Planner")
        self.geometry("1000x800")
        self.resizable(True,True)

        # 설정 및 데이터 경로
        self.settings_path = os.path.expanduser("~/.scheduler_settings.json")
        self.data_path = os.path.expanduser("~/.scheduler_data.json")

        self.settings = self.load_settings()
        self.theme = self.settings.get('theme','light')
        self.data = {}
        self.load_all_data()

        self.setup_style()
        self.create_widgets()

        self.check_alarms()
        self.update_current_task()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def load_settings(self):
        if os.path.exists(self.settings_path):
            return json.load(open(self.settings_path,'r'))
        return {}

    def save_settings(self):
        json.dump(self.settings, open(self.settings_path,'w'), ensure_ascii=False, indent=4)

    def load_all_data(self):
        if os.path.exists(self.data_path):
            self.data = json.load(open(self.data_path,'r'))

    def save_all_data(self):
        json.dump(self.data, open(self.data_path,'w'), ensure_ascii=False, indent=4)

    def setup_style(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        bg, fg, sel_bg = (
            ('#2c3e50','#ecf0f1','#34495e') if self.theme=='dark'
            else ('#ffffff','#2c3e50','#cce5ff')
        )
        self.configure(bg=bg)
        style.configure('TLabel', background=bg, foreground=fg)
        style.configure('TButton', background=bg, foreground=fg)
        style.configure('Treeview', background=bg, fieldbackground=bg, foreground=fg, rowheight=50)
        style.map('Treeview', background=[('selected', sel_bg)])
        style.configure('Treeview.Heading', background='#4a90e2',
                        foreground='white', font=('Malgun Gothic',13),
                        padding=(5,10))

    def create_widgets(self):
        m = tk.Menu(self)
        v = tk.Menu(m, tearoff=0)
        v.add_command(label="다크 모드 토글 (Ctrl+T)", command=self.toggle_theme)
        v.add_command(label="월간 캘린더 보기", command=self.open_month_view)
        m.add_cascade(label="보기", menu=v)
        self.config(menu=m)
        self.bind_all('<Control-t>', lambda e: self.toggle_theme())

        top = ttk.Frame(self); top.pack(fill=tk.X, pady=10)
        ttk.Label(top,text="날짜:").pack(side=tk.LEFT,padx=10)
        self.date_entry = DateEntry(top, width=16, date_pattern='yyyy-MM-dd')
        self.date_entry.pack(side=tk.LEFT)
        self.date_entry.bind("<<DateEntrySelected>>", lambda e: self.load_tasks())

        years = [str(y) for y in range(2020,2031)]
        months = [f"{m:02d}" for m in range(1,13)]
        ttk.Label(top,text="년:").pack(side=tk.LEFT,padx=(15,0))
        self.year_cb = ttk.Combobox(top, values=years, width=10)
        self.year_cb.set(self.date_entry.get_date().year)
        self.year_cb.pack(side=tk.LEFT)
        self.year_cb.bind('<<ComboboxSelected>>', lambda e: self.update_ym())

        ttk.Label(top,text="월:").pack(side=tk.LEFT,padx=(10,0))
        self.month_cb = ttk.Combobox(top, values=months, width=8)
        self.month_cb.set(f"{self.date_entry.get_date().month:02d}")
        self.month_cb.pack(side=tk.LEFT)
        self.month_cb.bind('<<ComboboxSelected>>', lambda e: self.update_ym())

        ttk.Button(top,text="<", command=self.prev_date, width=4).pack(side=tk.LEFT,padx=5)
        ttk.Button(top,text=">", command=self.next_date, width=4).pack(side=tk.LEFT)

        self.current_label = ttk.Label(
            top, text="현재: 없음", font=(None,13,'bold'),
            foreground='#d35400'
        )
        self.current_label.pack(side=tk.RIGHT,padx=15)

        ttk.Label(top,text="검색:").pack(side=tk.LEFT,padx=(15,0))
        self.search_var = tk.StringVar()
        ent = ttk.Entry(top, textvariable=self.search_var,
                        width=35)
        ent.pack(side=tk.LEFT)
        ent.bind('<KeyRelease>', lambda e: self.load_tasks())

        cols = ('start','end','task','priority','category')
        mid = ttk.Frame(self); mid.pack(fill=tk.BOTH, expand=True, pady=10)
        self.tree = ttk.Treeview(mid, columns=cols, show='headings')
        headings = {'start':'시작','end':'종료','task':'할 일',
                    'priority':'우선순위','category':'카테고리'}
        widths = [140,140,520,140,140]
        for c,w in zip(cols,widths):
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=w)
        sb = ttk.Scrollbar(mid, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        bottom = ttk.Frame(self); bottom.pack(fill=tk.X, pady=10)
        for txt, cmd in [("추가",self.add_task), ("수정",self.edit_task), ("삭제",self.delete_task)]:
            ttk.Button(bottom, text=txt, command=cmd, width=12).pack(side=tk.LEFT, padx=10)
        self.load_tasks()

    def update_ym(self):
        y = int(self.year_cb.get()); m = int(self.month_cb.get())
        d = self.date_entry.get_date().day
        last = calmodule.monthrange(y,m)[1]
        if d>last: d=last
        self.date_entry.set_date(datetime(y,m,d))
        self.load_tasks()

    def filter_tasks(self, items):
        q = self.search_var.get().lower()
        return [i for i in items if q in i['task'].lower()] if q else items

    def load_tasks(self):
        # 화면 초기화
        for i in self.tree.get_children():
            self.tree.delete(i)

        sel_date = self.date_entry.get_date().strftime('%Y-%m-%d')
        today_str = datetime.now().strftime('%Y-%m-%d')
        items = self.filter_tasks(self.data.get(sel_date, []))

        current = "없음"
        now = datetime.now()

        for e in sorted(items,
                        key=lambda x: datetime.strptime(x['start'], '%H:%M')):
            start_dt = datetime.strptime(f"{sel_date} {e['start']}", '%Y-%m-%d %H:%M')
            end_dt = datetime.strptime(f"{sel_date} {e['end']}", '%Y-%m-%d %H:%M')

            disp_task = f"{e['task']} ({e['start']}-{e['end']})"

            if sel_date == today_str and start_dt <= now <= end_dt:
                rem = (end_dt - now).seconds // 60
                disp_task += f", {rem}분 남음"
                current = disp_task

            self.tree.insert('', tk.END, values=(
                e['start'], e['end'], disp_task,
                e['priority'], e['category']
            ))

        self.current_label.config(text=f"현재: {current}")

    def add_task(self):
        dlg = TaskDialog(self, "추가")
        if dlg.result:
            d = self.date_entry.get_date().strftime('%Y-%m-%d')
            self.data.setdefault(d, []).append(dlg.result)
            if dlg.result['recurring']:
                nxt = self.date_entry.get_date() + timedelta(days=1)
                self.data.setdefault(nxt.strftime('%Y-%m-%d'), []).append(dlg.result)
            self.save_all_data()
            self.load_tasks()

    def edit_task(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("경고", "수정할 항목을 선택하세요.")
            return
        vals = self.tree.item(sel[0])['values']
        task_text = vals[2].split(' (')[0]
        dlg = TaskDialog(self, "수정", vals[0], vals[1], task_text, vals[3], vals[4])
        if dlg.result:
            d = self.date_entry.get_date().strftime('%Y-%m-%d')
            lst = self.data.get(d, [])
            for i,e in enumerate(lst):
                if (e['start'], e['end'], e['task'],
                    e['priority'], e['category']) == (
                    vals[0], vals[1], task_text,
                    vals[3], vals[4]
                ):
                    lst[i] = dlg.result
                    break
            self.save_all_data()
            self.load_tasks()

    def delete_task(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("경고", "삭제할 항목을 선택하세요.")
            return
        if messagebox.askyesno("확인", "정말 삭제하시겠습니까?"):
            d = self.date_entry.get_date().strftime('%Y-%m-%d')
            vals = self.tree.item(sel[0])['values']
            task_text = vals[2].split(' (')[0]
            self.data[d] = [
                e for e in self.data.get(d, [])
                if not (
                    e['start']==vals[0] and e['end']==vals[1] and
                    e['task']==task_text and e['priority']==vals[3] and
                    e['category']==vals[4]
                )
            ]
            self.save_all_data()
            self.load_tasks()

    def prev_date(self):
        self.date_entry.set_date(self.date_entry.get_date() - timedelta(days=1))
        self.sync_ym()
        self.load_tasks()

    def next_date(self):
        self.date_entry.set_date(self.date_entry.get_date() + timedelta(days=1))
        self.sync_ym()
        self.load_tasks()

    def sync_ym(self):
        d = self.date_entry.get_date()
        self.year_cb.set(d.year)
        self.month_cb.set(f"{d.month:02d}")

    def toggle_theme(self):
        self.theme = 'dark' if self.theme=='light' else 'light'
        self.settings['theme'] = self.theme
        self.save_settings()
        self.setup_style()

    def open_month_view(self):
        win = tk.Toplevel(self)
        win.title("월간 캘린더")
        cal = Calendar(win, selectmode='day', date_pattern='yyyy-MM-dd')
        cal.pack(padx=10, pady=10)
        ttk.Button(win, text="선택",command=lambda: [self.date_entry.set_date(cal.selection_get()),self.sync_ym(),self.load_tasks(),win.destroy()]).pack(pady=5)

    def update_current_task(self):
        self.load_tasks()
        self.after(60000, self.update_current_task)

    def check_alarms(self):
        now = datetime.now()
        today = now.strftime('%Y-%m-%d')
        for e in self.data.get(today, []):
            if e['start'] == now.strftime('%H:%M'):
                messagebox.showinfo("알림", f"{e['task']} 시작 시간입니다.")
                play_notification()
        self.after(60000, self.check_alarms)

    def on_close(self):
        self.save_all_data()
        self.destroy()

if __name__ == "__main__":
    SchedulerApp().mainloop()