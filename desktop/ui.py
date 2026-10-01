"""Native Tkinter interface for OSY Connect."""
from datetime import date
from pathlib import Path
import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageOps, ImageTk

from .data import Store, CHOICES, FIELDS, LABELS, age, export_csv
from .printing import id_pdf, report_pdf

GREEN = "#14765b"
INK = "#24352f"
MUTED = "#718178"
BG = "#f4f7f5"


def open_file(path):
    if sys.platform == "win32":
        os.startfile(str(path))
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


class Application(tk.Tk):
    def __init__(self, folder):
        super().__init__()
        self.title("OSY Connect | Youth Monitoring")
        self.geometry("1180x790")
        self.minsize(960, 650)
        self.configure(bg=BG)
        self.store = Store(folder)
        self.username = None
        self.editor = None
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.style = ttk.Style(self)
        self.style.theme_use("clam")
        self.option_add("*Font", ("Segoe UI", 10))
        self.style.configure("TFrame", background=BG)
        self.style.configure("TLabel", background=BG, foreground=INK, font=("Segoe UI", 10))
        self.style.configure("Muted.TLabel", foreground=MUTED)
        self.style.configure("Title.TLabel", font=("Segoe UI", 25, "bold"))
        self.style.configure("Heading.TLabel", font=("Segoe UI", 13, "bold"))
        self.style.configure("TButton", padding=(12, 9), font=("Segoe UI", 10))
        self.style.configure("Primary.TButton", background=GREEN, foreground="white", borderwidth=0)
        self.style.map("Primary.TButton", background=[("active", "#10533f"), ("disabled", "#b4c5bc")])
        self.style.configure("TEntry", padding=7)
        self.style.configure("TCombobox", padding=6)
        self.style.configure("Treeview", rowheight=36, font=("Segoe UI", 10), background="white", fieldbackground="white")
        self.style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), padding=9)
        self.style.map("Treeview", background=[("selected", GREEN)], foreground=[("selected", "white")])
        self.auth_screen()

    def report_callback_exception(self, kind, value, traceback):
        import traceback as trace
        trace.print_exception(kind, value, traceback)
        messagebox.showerror("Unable to complete action", str(value), parent=self)

    def close(self):
        if self.editor and self.editor.winfo_exists() and not self.editor.cancel():
            return
        self.store.close()
        self.destroy()

    def clear(self):
        for widget in self.winfo_children():
            widget.destroy()

    def auth_screen(self):
        self.clear()
        setup = not self.store.is_ready()
        wrapper = ttk.Frame(self, padding=40)
        wrapper.place(relx=.5, rely=.5, anchor="center", width=475)
        ttk.Label(wrapper, text="OSY Connect", style="Title.TLabel").pack(anchor="w")
        ttk.Label(wrapper, text="Out-of-School Youth Monitoring", style="Muted.TLabel").pack(anchor="w", pady=(4, 26))
        ttk.Label(wrapper, text="Create your administrator account" if setup else "Welcome back", style="Heading.TLabel").pack(anchor="w", pady=(0, 16))
        variables = {}
        for key, label in [("username", "Username"), ("password", "Password")] + ([("confirm", "Confirm password")] if setup else []):
            ttk.Label(wrapper, text=label).pack(anchor="w", pady=(8, 4))
            variable = tk.StringVar()
            entry = ttk.Entry(wrapper, textvariable=variable, show="" if key == "username" else "●")
            entry.pack(fill="x")
            variables[key] = variable
            if key == "username":
                entry.focus_set()
        self.auth_vars = variables
        error = ttk.Label(wrapper, text="", foreground="#b13d35", wraplength=390)
        error.pack(fill="x", pady=(12, 0))

        def submit(event=None):
            try:
                if setup:
                    self.store.setup(variables["username"].get(), variables["password"].get(), variables["confirm"].get())
                self.username = self.store.login(variables["username"].get(), variables["password"].get())
                self.unbind("<Return>")
                self.shell()
            except ValueError as exc:
                error.config(text=str(exc))

        self.auth_submit = submit
        ttk.Button(wrapper, text="Create account & start" if setup else "Sign in", command=submit, style="Primary.TButton").pack(fill="x", pady=12)
        ttk.Label(wrapper, text="Your records stay on this computer.\nNo browser or XAMPP is required.", style="Muted.TLabel").pack(anchor="w", pady=(12, 0))
        self.bind("<Return>", submit)

    def shell(self):
        self.clear()
        sidebar = tk.Frame(self, bg="white", width=215, padx=16, pady=26)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text="OSY Connect", bg="white", fg=GREEN, font=("Segoe UI", 21, "bold")).pack(anchor="w")
        tk.Label(sidebar, text="YOUTH MONITORING", bg="white", fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(4, 30))
        self.nav_buttons = {}
        for text, command in [("Dashboard", self.dashboard), ("OSY records", self.records_page),
                              ("Register OSY", self.edit_record), ("ID generation", lambda: self.records_page("ID generation")),
                              ("Reports", lambda: self.records_page("Reports")), ("Data & backups", self.data_page)]:
            button = tk.Button(sidebar, text=text, command=command, anchor="w", bg="white", fg=INK,
                               activebackground="#e9f3ee", relief="flat", borderwidth=0, padx=14, pady=12, cursor="hand2")
            button.pack(fill="x", pady=3)
            self.nav_buttons[text] = button
        ttk.Button(sidebar, text="Log out", command=self.logout).pack(side="bottom", fill="x", pady=8)
        tk.Label(sidebar, text=self.username, bg="white", fg=MUTED, wraplength=180).pack(side="bottom", anchor="w")
        outer = ttk.Frame(self)
        outer.pack(side="left", fill="both", expand=True)
        bar = ttk.Frame(outer, padding=(28, 18))
        bar.pack(fill="x")
        ttk.Label(bar, text="OSY Connect  /  Desktop", style="Muted.TLabel").pack(side="left")
        ttk.Label(bar, text=date.today().strftime("%B %d, %Y"), style="Muted.TLabel").pack(side="right")
        ttk.Separator(outer).pack(fill="x")
        self.content = ttk.Frame(outer, padding=(28, 24))
        self.content.pack(fill="both", expand=True)
        self.status = tk.StringVar(value="Ready • Local database")
        ttk.Label(outer, textvariable=self.status, style="Muted.TLabel", padding=(28, 8)).pack(fill="x")
        self.dashboard()

    def logout(self):
        if self.editor and self.editor.winfo_exists() and not self.editor.cancel():
            return
        self.username = None
        self.auth_screen()

    def page(self, name, description):
        for child in self.content.winfo_children():
            child.destroy()
        for key, button in self.nav_buttons.items():
            button.config(bg="#e9f3ee" if key == name else "white", fg=GREEN if key == name else INK)
        heading = ttk.Frame(self.content)
        heading.pack(fill="x", pady=(0, 22))
        ttk.Label(heading, text=name, style="Title.TLabel").pack(anchor="w")
        ttk.Label(heading, text=description, style="Muted.TLabel").pack(anchor="w", pady=(5, 0))

    def dashboard(self):
        self.page("Dashboard", "Your community at a glance. Archived records are excluded.")
        rows = self.store.records()
        cards = ttk.Frame(self.content)
        cards.pack(fill="x")
        for index, (label, value) in enumerate([
            ("Registered OSY", len(rows)), ("Male", sum(r["sex"] == "Male" for r in rows)),
            ("Female", sum(r["sex"] == "Female" for r in rows)), ("Active OSY", sum(r["status"] == "Active" for r in rows))]):
            cards.columnconfigure(index, weight=1, uniform="stats")
            card = tk.Frame(cards, bg="white", padx=18, pady=16, highlightbackground="#e0e8e2", highlightthickness=1)
            card.grid(row=0, column=index, sticky="ew", padx=(0, 10))
            tk.Label(card, text=label, fg=MUTED, bg="white", font=("Segoe UI", 10)).pack(anchor="w")
            tk.Label(card, text=str(value), fg=GREEN, bg="white", font=("Segoe UI", 28, "bold")).pack(anchor="w", pady=(8, 0))
        summaries = ttk.Frame(self.content)
        summaries.pack(fill="x", pady=22)
        ages = [age(r["birthdate"]) for r in rows]
        groups = [("15–17", sum(15 <= a <= 17 for a in ages)), ("18–20", sum(18 <= a <= 20 for a in ages)),
                  ("21–24", sum(21 <= a <= 24 for a in ages)), ("Other ages", sum(a < 15 or a > 24 for a in ages))]
        ttk.Label(summaries, text="Youth by age group", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(summaries, text="     ".join(f"{label}: {n}" for label, n in groups)).pack(anchor="w", pady=10)
        employed = sum(r["employment_status"] == "Employed" for r in rows)
        ttk.Label(summaries, text=f"Employment overview    •    Employed: {employed}    •    Unemployed: {len(rows) - employed}", style="Muted.TLabel").pack(anchor="w")
        title = ttk.Frame(self.content)
        title.pack(fill="x", pady=(0, 10))
        ttk.Label(title, text="Recent registrations", style="Heading.TLabel").pack(side="left")
        ttk.Button(title, text="+ Register OSY", style="Primary.TButton", command=self.edit_record).pack(side="right")
        recent = sorted(rows, key=lambda r: (r["created_at"], r["id"]), reverse=True)[:5]
        self.make_table(recent)

    def make_table(self, rows):
        frame = ttk.Frame(self.content)
        frame.pack(fill="both", expand=True)
        columns = ("osy_id", "full_name", "sex", "employment_status", "status", "date_registered")
        tree = ttk.Treeview(frame, columns=columns, show="headings", selectmode="browse")
        for key, title, width in zip(columns, ("OSY ID", "Full name", "Sex", "Employment", "Status", "Registered"), (145, 230, 75, 115, 85, 110)):
            tree.heading(key, text=title)
            tree.column(key, width=width, minwidth=65)
        vertical = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        for row in rows:
            tree.insert("", "end", iid=str(row["id"]), values=[row[key] for key in columns])
        tree.bind("<Double-1>", lambda e: self.selected_action(tree, self.profile))
        tree.bind("<Return>", lambda e: self.selected_action(tree, self.profile))
        self.tree = tree
        if not rows:
            self.status.set("No matching records. Register a youth or adjust your filters.")
        return tree

    def selected_action(self, tree, action):
        selected = tree.selection()
        if not selected:
            messagebox.showinfo("Select a record", "Select a record from the list first.", parent=self)
            return
        action(int(selected[0]))

    def records_page(self, mode="OSY records"):
        self.page(mode, "Search, filter and select a record. Double-click a row to view the full profile.")
        filters = ttk.Frame(self.content)
        filters.pack(fill="x", pady=(0, 12))
        search = tk.StringVar()
        ttk.Label(filters, text="Name or OSY ID").grid(row=0, column=0, sticky="w")
        entry = ttk.Entry(filters, textvariable=search, width=24)
        entry.grid(row=1, column=0, sticky="ew", padx=(0, 8))
        choices = {}
        for col, key in enumerate(("sex", "status", "employment_status"), 1):
            variable = tk.StringVar(value="All")
            choices[key] = variable
            ttk.Label(filters, text=LABELS[key]).grid(row=0, column=col, sticky="w")
            combo = ttk.Combobox(filters, textvariable=variable, values=("All",) + CHOICES[key], state="readonly", width=13)
            combo.grid(row=1, column=col, padx=(0, 8), sticky="ew")
            combo.bind("<<ComboboxSelected>>", lambda e: refresh())
        archived = tk.BooleanVar(value=False)
        controls = ttk.Frame(self.content)
        controls.pack(fill="x", pady=(0, 12))
        ttk.Checkbutton(controls, text="Archived records", variable=archived, command=lambda: refresh()).pack(side="left")
        count = ttk.Label(controls, style="Muted.TLabel")
        count.pack(side="right")
        toolbar = ttk.Frame(self.content)
        toolbar.pack(fill="x", pady=(0, 12))
        tree = self.make_table([])
        self.visible_rows = []

        def refresh():
            self.visible_rows = self.store.records(search.get(), archived.get(), **{k: v.get() for k, v in choices.items()})
            tree.delete(*tree.get_children())
            for row in self.visible_rows:
                tree.insert("", "end", iid=str(row["id"]), values=[row[key] for key in tree["columns"]])
            count.config(text=f"{len(self.visible_rows)} record(s)")
            archive_button.config(text="Restore" if archived.get() else "Archive")
            self.status.set("Showing archived records" if archived.get() else "Showing current records")

        def archive_selected(record_id):
            verb = "Restore" if archived.get() else "Archive"
            if messagebox.askyesno(verb + " record", f"{verb} {self.store.get(record_id)['full_name']}?", parent=self):
                self.store.archive(record_id, not archived.get())
                refresh()

        def report():
            description = ("Archived records" if archived.get() else "Current records")
            if search.get().strip():
                description += " | Search: " + search.get().strip()
            description += "".join(f" | {LABELS[k]}: {v.get()}" for k, v in choices.items() if v.get() != "All")
            self.save_report(self.visible_rows, description)

        for label, action in [("View profile", self.profile), ("Edit", self.edit_record), ("Preview ID", self.preview_id)]:
            ttk.Button(toolbar, text=label, command=lambda a=action: self.selected_action(tree, a)).pack(side="left", padx=(0, 6))
        archive_button = ttk.Button(toolbar, text="Archive", command=lambda: self.selected_action(tree, archive_selected))
        archive_button.pack(side="left")
        ttk.Button(toolbar, text="Export CSV", command=lambda: self.save_csv(self.visible_rows)).pack(side="right", padx=(6, 0))
        ttk.Button(toolbar, text="Report PDF", command=report, style="Primary.TButton").pack(side="right")
        ttk.Button(filters, text="Search", command=refresh).grid(row=1, column=4)
        entry.bind("<Return>", lambda e: refresh())
        self.refresh_records = refresh
        refresh()

    def edit_record(self, record_id=None):
        if self.editor and self.editor.winfo_exists():
            self.editor.lift()
            return
        self.editor = RecordEditor(self, self.store.get(record_id) if record_id else None)

    def profile(self, record_id):
        record = self.store.get(record_id)
        self.page("Profile", record["osy_id"] + (" • Archived record" if record["archived_at"] else ""))
        actions = ttk.Frame(self.content)
        actions.pack(fill="x", pady=(0, 18))
        ttk.Button(actions, text="Back to records", command=self.records_page).pack(side="left")
        ttk.Button(actions, text="Edit profile", command=lambda: self.edit_record(record_id)).pack(side="right", padx=(8, 0))
        ttk.Button(actions, text="Preview ID", command=lambda: self.preview_id(record_id), style="Primary.TButton").pack(side="right")
        area = ScrollArea(self.content)
        area.pack(fill="both", expand=True)
        body = area.inner
        photo = self.store.photo_path(record["photo"])
        if photo:
            with Image.open(photo) as source:
                self.profile_image = ImageTk.PhotoImage(ImageOps.fit(source, (96, 112)))
            ttk.Label(body, image=self.profile_image).grid(row=0, column=0, sticky="nw", pady=(0, 15))
        ttk.Label(body, text=record["full_name"], style="Heading.TLabel", wraplength=600).grid(row=0, column=1, sticky="nw", padx=18, pady=(0, 15))
        for index, key in enumerate(FIELDS[1:], 1):
            ttk.Label(body, text=LABELS[key], style="Muted.TLabel").grid(row=index, column=0, sticky="nw", pady=7)
            value = record[key] or "—"
            if key == "birthdate":
                value += f" ({age(record[key])} years old)"
            ttk.Label(body, text=value, wraplength=590, justify="left").grid(row=index, column=1, sticky="nw", padx=18, pady=7)

    def preview_id(self, record_id):
        record = self.store.get(record_id)
        dialog = tk.Toplevel(self)
        dialog.title("ID preview • " + record["osy_id"])
        dialog.geometry("710x545")
        dialog.resizable(False, False)
        dialog.configure(bg=BG)
        dialog.transient(self)
        ttk.Label(dialog, text="Identification card", style="Heading.TLabel", padding=18).pack(anchor="w")
        card = tk.Frame(dialog, bg="white", width=650, height=350, highlightthickness=1, highlightbackground="#dce5df")
        card.pack(padx=25)
        card.pack_propagate(False)
        tk.Label(card, text="OUT-OF-SCHOOL YOUTH\nIDENTIFICATION CARD", bg=GREEN, fg="white", font=("Segoe UI", 14, "bold"), anchor="w", padx=20, pady=10).pack(fill="x")
        main = tk.Frame(card, bg="white", padx=18, pady=15)
        main.pack(fill="both", expand=True)
        photo = self.store.photo_path(record["photo"])
        if photo:
            with Image.open(photo) as source:
                dialog.photo = ImageTk.PhotoImage(ImageOps.fit(source, (112, 138)))
            tk.Label(main, image=dialog.photo, bg="white").pack(side="left", anchor="n", padx=(0, 18))
        else:
            tk.Label(main, text="".join(w[0] for w in record["full_name"].split()[:2]), bg="#e9f3ee", fg=GREEN, width=5, height=4, font=("Segoe UI", 24, "bold")).pack(side="left", anchor="n", padx=(0, 18))
        details = tk.Frame(main, bg="white")
        details.pack(side="left", fill="both", expand=True)
        for value, size, color in [(record["full_name"], 12, INK), (record["osy_id"], 11, GREEN),
                                   ("Birthdate: " + record["birthdate"], 9, INK), ("Address: " + record["address"], 8, INK),
                                   ("Status: " + record["status"] + (" / Archived" if record["archived_at"] else ""), 9, INK)]:
            tk.Label(details, text=value, bg="white", fg=color, font=("Segoe UI", size), wraplength=445, justify="left", anchor="w").pack(fill="x", pady=2)
        tk.Label(card, text=self.store.organization() + "     |     Authorized signature", bg="#e9f3ee", fg=INK, wraplength=620, pady=8, font=("Segoe UI", 8)).pack(fill="x", side="bottom")
        ttk.Label(dialog, text="PDF size: 86 × 54 mm. Print from your PDF viewer using Actual size / 100%.\nFor long names or addresses, check the exported PDF before printing.", style="Muted.TLabel", padding=14).pack()
        ttk.Button(dialog, text="Save PDF for printing", style="Primary.TButton", command=lambda: self.save_id(record)).pack()

    def save_id(self, record):
        destination = filedialog.asksaveasfilename(parent=self, title="Save ID card", defaultextension=".pdf", initialfile=record["osy_id"] + ".pdf", filetypes=[("PDF document", "*.pdf")])
        if destination:
            id_pdf(record, destination, self.store.organization(), self.store.photo_path(record["photo"]))
            self.export_done(destination)

    def save_report(self, rows, description):
        destination = filedialog.asksaveasfilename(parent=self, title="Save master list", defaultextension=".pdf", initialfile="OSY-master-list.pdf", filetypes=[("PDF document", "*.pdf")])
        if destination:
            report_pdf(rows, destination, self.store.organization(), description)
            self.export_done(destination)

    def save_csv(self, rows):
        destination = filedialog.asksaveasfilename(parent=self, title="Export records", defaultextension=".csv", initialfile="OSY-records.csv", filetypes=[("CSV file", "*.csv")])
        if destination:
            export_csv(rows, destination)
            messagebox.showinfo("Export complete", f"Exported {len(rows)} record(s).\n{destination}", parent=self)

    def export_done(self, path):
        self.status.set("Saved: " + str(path))
        if messagebox.askyesno("PDF saved", "Open the PDF now? Use your PDF viewer's Print command to print it.", parent=self):
            open_file(path)

    def data_page(self):
        self.page("Data & backups", "Move your records between computers and keep a complete backup.")
        ttk.Label(self.content, text="Organization printed on reports and IDs", style="Heading.TLabel").pack(anchor="w")
        organization = tk.StringVar(value=self.store.organization())
        ttk.Entry(self.content, textvariable=organization, width=55).pack(anchor="w", pady=10)

        def save_organization():
            self.store.set_organization(organization.get())
            self.status.set("Organization saved.")

        ttk.Button(self.content, text="Save organization", command=save_organization).pack(anchor="w")
        ttk.Separator(self.content).pack(fill="x", pady=20)
        ttk.Label(self.content, text="Back up database and photos", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(self.content, text="Creates one ZIP containing records, administrator account, settings and photos.\nTo restore: close the app, keep a copy of the existing data folder, then extract\nthe ZIP contents into desktop-data on the destination computer.", style="Muted.TLabel").pack(anchor="w", pady=10)
        ttk.Button(self.content, text="Create backup ZIP", command=self.backup, style="Primary.TButton").pack(anchor="w")
        ttk.Separator(self.content).pack(fill="x", pady=20)
        ttk.Label(self.content, text="Import existing records", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(self.content, text="Import a CSV export of the old osy_records table with column names in its first row.\nYou can select the old storage/photos folder to bring profile photos along.\nExisting IDs are preserved. Duplicate IDs cancel the entire import.\nYour desktop administrator account stays separate from the old PHP login.", style="Muted.TLabel").pack(anchor="w", pady=10)
        ttk.Button(self.content, text="Import records CSV", command=self.import_records).pack(anchor="w")
        ttk.Label(self.content, text="Data folder: " + str(self.store.folder), style="Muted.TLabel", wraplength=750).pack(anchor="w", pady=20)

    def backup(self):
        destination = filedialog.asksaveasfilename(parent=self, title="Save complete backup", defaultextension=".zip", initialfile=f"OSY-backup-{date.today()}.zip", filetypes=[("ZIP backup", "*.zip")])
        if destination:
            self.store.backup(destination)
            messagebox.showinfo("Backup complete", "Database and photos saved to:\n" + destination, parent=self)

    def import_records(self):
        source = filedialog.askopenfilename(parent=self, title="Choose records CSV", filetypes=[("CSV file", "*.csv")])
        if not source:
            return
        photos = None
        if messagebox.askyesno("Import photos", "Do you have a photos folder to import with these records?", parent=self):
            photos = filedialog.askdirectory(parent=self, title="Select the old storage/photos folder")
            if not photos:
                return
        if not messagebox.askyesno("Import records", "Add all records in this CSV to the desktop database?\nDuplicate IDs or invalid rows will cancel the whole import.", parent=self):
            return
        count, missing = self.store.import_csv(source, photos)
        messagebox.showinfo("Import complete", f"Imported {count} record(s).\nPhotos not found: {missing}.", parent=self)


class ScrollArea(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        self.window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda event: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda event: self.canvas.itemconfigure(self.window, width=event.width))
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.owner = self.winfo_toplevel()
        self.wheel_binding = self.owner.bind("<MouseWheel>", self.wheel, add="+")
        self.bind("<Destroy>", self.cleanup)

    def wheel(self, event):
        if str(event.widget).startswith(str(self) + ".") and not isinstance(event.widget, (tk.Text, ttk.Combobox)):
            self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def cleanup(self, event):
        if event.widget == self:
            try:
                self.owner.unbind("<MouseWheel>", self.wheel_binding)
            except tk.TclError:
                pass


class RecordEditor(tk.Toplevel):
    def __init__(self, app, record=None):
        super().__init__(app)
        self.app = app
        self.record = record
        self.photo_source = None
        self.remove_photo = False
        self.title("Edit OSY record" if record else "Register OSY")
        self.geometry("830x760")
        self.minsize(700, 560)
        self.configure(bg=BG)
        self.transient(app)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.cancel)
        ttk.Label(self, text="Edit OSY record" if record else "Register OSY", style="Title.TLabel", padding=(24, 18)).pack(anchor="w")
        ttk.Label(self, text="Fields marked * are required. Dates use YYYY-MM-DD.", style="Muted.TLabel", padding=(24, 0)).pack(anchor="w")
        footer = ttk.Frame(self, padding=18)
        footer.pack(side="bottom", fill="x")
        ttk.Button(footer, text="Cancel", command=self.cancel).pack(side="left")
        ttk.Button(footer, text="Save changes" if record else "Save registration", command=self.save, style="Primary.TButton").pack(side="right")
        self.error = ttk.Label(self, text="", foreground="#b13d35", wraplength=750, padding=(24, 4))
        self.error.pack(side="bottom", fill="x")
        area = ScrollArea(self)
        area.pack(fill="both", expand=True, padx=24, pady=15)
        area.inner.columnconfigure(0, weight=1)
        area.inner.columnconfigure(1, weight=1)
        values = record or {"date_registered": date.today().isoformat(), "status": "Active", "employment_status": "Unemployed"}
        self.variables = {}
        self.texts = {}
        required = {"full_name", "birthdate", "sex", "address", "educational_attainment", "employment_status", "date_registered", "status"}
        row = 0
        for key in FIELDS:
            ttk.Label(area.inner, text=LABELS[key] + (" *" if key in required else "")).grid(row=row, column=0, sticky="nw", pady=(9, 3), padx=(0, 16))
            if key in ("address", "reason_stopped"):
                widget = tk.Text(area.inner, height=3, width=46, wrap="word", font=("Segoe UI", 10), relief="solid", borderwidth=1, padx=7, pady=7)
                widget.insert("1.0", values.get(key, ""))
                self.texts[key] = widget
            else:
                variable = tk.StringVar(value=values.get(key, ""))
                self.variables[key] = variable
                if key in CHOICES:
                    widget = ttk.Combobox(area.inner, textvariable=variable, values=CHOICES[key], state="readonly")
                else:
                    widget = ttk.Entry(area.inner, textvariable=variable)
            widget.grid(row=row, column=1, sticky="ew", pady=(5, 3))
            if key == "full_name":
                widget.focus_set()
            row += 1
            if key == "birthdate":
                self.age_label = ttk.Label(area.inner, style="Muted.TLabel")
                self.age_label.grid(row=row, column=1, sticky="w")
                self.variables[key].trace_add("write", lambda *args: self.update_age())
                self.update_age()
                row += 1
        ttk.Label(area.inner, text="Profile photo (optional)").grid(row=row, column=0, sticky="nw", pady=12)
        photo_buttons = ttk.Frame(area.inner)
        photo_buttons.grid(row=row, column=1, sticky="ew", pady=12)
        self.photo_label = ttk.Label(photo_buttons, text="Existing photo" if record and record["photo"] else "No photo selected", wraplength=400)
        self.photo_label.pack(anchor="w", pady=(0, 6))
        ttk.Button(photo_buttons, text="Choose photo", command=self.choose_photo).pack(side="left")
        ttk.Button(photo_buttons, text="Remove", command=self.clear_photo).pack(side="left", padx=5)
        ttk.Label(area.inner, text="JPG, PNG or WebP, up to 2 MB.", style="Muted.TLabel").grid(row=row + 1, column=1, sticky="w")
        self.initial = self.values()

    def update_age(self):
        try:
            value = age(self.variables["birthdate"].get())
            self.age_label.config(text=f"Age: {value} years" if value >= 0 else "")
        except ValueError:
            self.age_label.config(text="")

    def values(self):
        return {**{key: value.get() for key, value in self.variables.items()},
                **{key: widget.get("1.0", "end-1c") for key, widget in self.texts.items()}}

    def choose_photo(self):
        path = filedialog.askopenfilename(parent=self, title="Choose a profile photo", filetypes=[("Profile photos", "*.jpg *.jpeg *.png *.webp")])
        if path:
            self.photo_source = path
            self.remove_photo = False
            self.photo_label.config(text=Path(path).name)

    def clear_photo(self):
        self.photo_source = None
        self.remove_photo = True
        self.photo_label.config(text="No photo selected")

    def cancel(self):
        if self.values() != self.initial or self.photo_source or self.remove_photo:
            if not messagebox.askyesno("Discard changes", "Close without saving your changes?", parent=self):
                return False
        self.destroy()
        return True

    def save(self):
        try:
            record_id = self.app.store.save(self.values(), self.record["id"] if self.record else None, self.photo_source, self.remove_photo)
        except (ValueError, OSError) as error:
            self.error.config(text=str(error))
            return
        self.destroy()
        self.app.profile(record_id)
        self.app.status.set("Record saved successfully.")
