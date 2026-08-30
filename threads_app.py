import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import os
import csv
from datetime import datetime
from dotenv import load_dotenv, set_key
from apify_client import ApifyClient
from tkcalendar import DateEntry

load_dotenv()


class ThreadsScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Threads Scraper")
        self.root.geometry("980x820")
        self.root.minsize(760, 600)
        self.root.resizable(True, True)

        # Color scheme
        self.colors = {
            'bg': '#f4f5f9',
            'surface': '#ffffff',
            'primary': '#6c5ce7',
            'primary_dark': '#5849c2',
            'success': '#00b894',
            'danger': '#ff6b6b',
            'warning': '#fdae2b',
            'text': '#2d3436',
            'text_muted': '#8395a7',
            'border': '#e3e6ee',
            'input_bg': '#f8f9fc',
            'log_bg': '#1e1e2e',
            'log_fg': '#cdd6f4',
        }

        self.root.configure(bg=self.colors['bg'])

        # Variables
        self.api_token = tk.StringVar(value=os.getenv("APIFY_API_TOKEN", ""))
        self.actor_id = tk.StringVar(value=os.getenv("APIFY_ACTOR_ID", "automation-lab/threads-scraper"))
        self.max_posts = tk.IntVar(value=20)
        self.output_file = tk.StringVar(value="results.csv")
        self.posted_after_enabled = tk.BooleanVar(value=False)
        self.posted_before_enabled = tk.BooleanVar(value=False)
        self.is_running = False

        self._setup_styles()
        self._build_ui()

    # ---------------------------------------------------------------- styles
    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        c = self.colors

        style.configure('Title.TLabel', font=('Segoe UI', 22, 'bold'),
                         foreground=c['text'], background=c['bg'])
        style.configure('Subtitle.TLabel', font=('Segoe UI', 10),
                         foreground=c['text_muted'], background=c['bg'])
        style.configure('CardTitle.TLabel', font=('Segoe UI', 12, 'bold'),
                         foreground=c['text'], background=c['surface'])
        style.configure('Field.TLabel', font=('Segoe UI', 9, 'bold'),
                         foreground=c['text'], background=c['surface'])
        style.configure('Hint.TLabel', font=('Segoe UI', 8),
                         foreground=c['text_muted'], background=c['surface'])

        style.configure('TEntry', fieldbackground=c['input_bg'],
                         bordercolor=c['border'], borderwidth=1, relief='solid',
                         padding=6)
        style.configure('TSpinbox', fieldbackground=c['input_bg'],
                         bordercolor=c['border'], padding=6, arrowsize=14)

        style.configure('TCheckbutton', background=c['surface'],
                         foreground=c['text_muted'], font=('Segoe UI', 8))
        style.map('TCheckbutton', background=[('active', c['surface'])])

        style.configure('Primary.TButton', background=c['primary'], foreground='white',
                         font=('Segoe UI', 11, 'bold'), padding=(16, 12), borderwidth=0)
        style.map('Primary.TButton',
                  background=[('active', c['primary_dark']), ('disabled', c['border'])])

        style.configure('Secondary.TButton', background=c['input_bg'], foreground=c['text'],
                         font=('Segoe UI', 9), padding=(10, 7), borderwidth=1, relief='solid')
        style.map('Secondary.TButton', background=[('active', c['border'])])

        style.configure('Horizontal.TProgressbar', background=c['primary'],
                         troughcolor=c['input_bg'], borderwidth=0, thickness=6)

    # ---------------------------------------------------------------- helpers
    def _card(self, parent, title=None):
        """A flat white card with a border, consistent padding, used for every section."""
        wrapper = tk.Frame(parent, bg=self.colors['surface'],
                            highlightbackground=self.colors['border'],
                            highlightthickness=1, bd=0)
        wrapper.pack(fill=tk.X, pady=(0, 16))
        inner = tk.Frame(wrapper, bg=self.colors['surface'])
        inner.pack(fill=tk.BOTH, expand=True, padx=20, pady=16)
        if title:
            ttk.Label(inner, text=title, style='CardTitle.TLabel').pack(anchor=tk.W, pady=(0, 12))
        return inner

    def _field_label(self, parent, text, hint=None):
        ttk.Label(parent, text=text, style='Field.TLabel').pack(anchor=tk.W)
        if hint:
            ttk.Label(parent, text=hint, style='Hint.TLabel').pack(anchor=tk.W, pady=(1, 6))
        else:
            tk.Frame(parent, height=6, bg=self.colors['surface']).pack()

    def _date_picker_field(self, parent, label_text, enabled_var):
        """Label + checkbox (enable filter) + calendar date picker. Returns the DateEntry."""
        header_row = tk.Frame(parent, bg=self.colors['surface'])
        header_row.pack(fill=tk.X)
        ttk.Label(header_row, text=label_text, style='Field.TLabel').pack(side=tk.LEFT)

        picker = DateEntry(
            parent, date_pattern='yyyy-mm-dd', width=14, state='disabled',
            font=('Segoe UI', 10), background=self.colors['primary'],
            foreground='white', bordercolor=self.colors['border'],
            headersbackground=self.colors['primary'], headersforeground='white',
            selectbackground=self.colors['primary'], normalbackground=self.colors['surface'],
            weekendbackground=self.colors['surface'], borderwidth=1
        )

        def on_toggle():
            picker.configure(state='normal' if enabled_var.get() else 'disabled')

        ttk.Checkbutton(header_row, text="enable", variable=enabled_var,
                         command=on_toggle).pack(side=tk.RIGHT)

        tk.Frame(parent, height=6, bg=self.colors['surface']).pack()
        picker.pack(fill=tk.X)
        return picker

    # ---------------------------------------------------------------- build UI
    def _build_ui(self):
        outer = tk.Frame(self.root, bg=self.colors['bg'])
        outer.pack(fill=tk.BOTH, expand=True)

        # ---- Header (fixed, does not scroll) ----
        header = tk.Frame(outer, bg=self.colors['bg'])
        header.pack(fill=tk.X, padx=24, pady=(20, 12))
        ttk.Label(header, text="🧵 Threads Scraper Pro", style='Title.TLabel').pack(anchor=tk.W)
        ttk.Label(header, text="Scrape Threads posts by keyword using the Apify API",
                  style='Subtitle.TLabel').pack(anchor=tk.W, pady=(2, 0))

        # ---- Scrollable body ----
        body_container = tk.Frame(outer, bg=self.colors['bg'])
        body_container.pack(fill=tk.BOTH, expand=True, padx=24, pady=(0, 20))

        canvas = tk.Canvas(body_container, bg=self.colors['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(body_container, orient='vertical', command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=self.colors['bg'])

        scroll_window = canvas.create_window((0, 0), window=scroll_frame, anchor='nw')

        def on_frame_configure(_event):
            canvas.configure(scrollregion=canvas.bbox('all'))

        def on_canvas_configure(event):
            # keep the inner frame exactly as wide as the canvas so cards stretch properly
            canvas.itemconfig(scroll_window, width=event.width)

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), 'units')

        scroll_frame.bind('<Configure>', on_frame_configure)
        canvas.bind('<Configure>', on_canvas_configure)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind_all('<MouseWheel>', on_mousewheel)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # ---- API Configuration card ----
        api_card = self._card(scroll_frame, "🔑  API Configuration")

        self._field_label(api_card, "API Token")
        token_row = tk.Frame(api_card, bg=self.colors['surface'])
        token_row.pack(fill=tk.X, pady=(0, 14))
        token_row.columnconfigure(0, weight=1)
        token_entry = ttk.Entry(token_row, textvariable=self.api_token, show='•', font=('Consolas', 10))
        token_entry.grid(row=0, column=0, sticky='ew')
        ttk.Button(token_row, text="💾 Save", command=self.save_token,
                   style='Secondary.TButton').grid(row=0, column=1, padx=(10, 0))

        self._field_label(api_card, "Actor ID")
        ttk.Entry(api_card, textvariable=self.actor_id, font=('Consolas', 9)).pack(fill=tk.X)

        # ---- Search Configuration card ----
        search_card = self._card(scroll_frame, "🔍  Search Configuration")

        self._field_label(search_card, "Search Keywords", "Enter one keyword per line")
        self.queries_text = scrolledtext.ScrolledText(
            search_card, height=6, font=('Segoe UI', 10),
            bg=self.colors['input_bg'], fg=self.colors['text'],
            relief='solid', borderwidth=1, padx=10, pady=10, wrap='word'
        )
        self.queries_text.pack(fill=tk.BOTH, expand=True, pady=(0, 16))

        options_grid = tk.Frame(search_card, bg=self.colors['surface'])
        options_grid.pack(fill=tk.X)
        for i in range(3):
            options_grid.columnconfigure(i, weight=1, uniform='opt')

        col0 = tk.Frame(options_grid, bg=self.colors['surface'])
        col0.grid(row=0, column=0, sticky='ew', padx=(0, 12))
        self._field_label(col0, "Max Posts / Query")
        ttk.Spinbox(col0, from_=1, to=1000, textvariable=self.max_posts,
                    font=('Segoe UI', 10)).pack(fill=tk.X)

        col1 = tk.Frame(options_grid, bg=self.colors['surface'])
        col1.grid(row=0, column=1, sticky='ew', padx=12)
        self.posted_after_picker = self._date_picker_field(
            col1, "Posted After", self.posted_after_enabled)

        col2 = tk.Frame(options_grid, bg=self.colors['surface'])
        col2.grid(row=0, column=2, sticky='ew', padx=(12, 0))
        self.posted_before_picker = self._date_picker_field(
            col2, "Posted Before", self.posted_before_enabled)

        # ---- Output card ----
        output_card = self._card(scroll_frame, "💾  Output")
        self._field_label(output_card, "Output File")
        output_row = tk.Frame(output_card, bg=self.colors['surface'])
        output_row.pack(fill=tk.X)
        output_row.columnconfigure(0, weight=1)
        ttk.Entry(output_row, textvariable=self.output_file,
                  font=('Segoe UI', 10)).grid(row=0, column=0, sticky='ew')
        ttk.Button(output_row, text="📁 Browse", command=self.browse_output,
                   style='Secondary.TButton').grid(row=0, column=1, padx=(10, 0))

        # ---- Run button ----
        self.run_button = ttk.Button(scroll_frame, text="🚀  Start Scraping",
                                      command=self.start_scraping, style='Primary.TButton')
        self.run_button.pack(fill=tk.X, pady=(4, 16))

        # ---- Status card ----
        status_card = self._card(scroll_frame)
        status_row = tk.Frame(status_card, bg=self.colors['surface'])
        status_row.pack(fill=tk.X)
        ttk.Label(status_row, text="Status:", style='Field.TLabel').pack(side=tk.LEFT)
        self.status_label = tk.Label(status_row, text="Ready", font=('Segoe UI', 10, 'bold'),
                                      fg=self.colors['success'], bg=self.colors['surface'])
        self.status_label.pack(side=tk.LEFT, padx=(8, 0))

        self.progress = ttk.Progressbar(status_card, mode='indeterminate',
                                         style='Horizontal.TProgressbar')
        self.progress.pack(fill=tk.X, pady=(12, 0))

        # ---- Logs card ----
        logs_card = self._card(scroll_frame, "📜  Activity Logs")
        self.log_text = scrolledtext.ScrolledText(
            logs_card, height=10, font=('Consolas', 9),
            bg=self.colors['log_bg'], fg=self.colors['log_fg'],
            relief='flat', padx=12, pady=10, state='disabled', wrap='word'
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

    # ---------------------------------------------------------------- logic
    def log(self, message):
        """Add message to log area"""
        self.log_text.configure(state='normal')
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state='disabled')

    def update_status(self, message, status_type="info"):
        """Update status label"""
        colors = {
            'success': self.colors['success'],
            'error': self.colors['danger'],
            'warning': self.colors['warning'],
            'info': self.colors['primary']
        }
        self.status_label.config(text=message, fg=colors.get(status_type, colors['info']))

    def save_token(self):
        """Save API token to .env file"""
        token = self.api_token.get().strip()
        if not token:
            messagebox.showwarning("Warning", "API Token cannot be empty")
            return

        env_file = ".env"
        if not os.path.exists(env_file):
            with open(env_file, "w") as f:
                f.write(f"APIFY_API_TOKEN={token}\n")
        else:
            set_key(env_file, "APIFY_API_TOKEN", token)

        self.log("✓ API Token saved to .env file")
        messagebox.showinfo("Success", "API Token saved successfully!")

    def browse_output(self):
        """Open file dialog for output file selection"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=self.output_file.get()
        )
        if filename:
            self.output_file.set(filename)

    def validate_inputs(self):
        """Validate all inputs before running"""
        if not self.api_token.get().strip():
            messagebox.showerror("Error", "API Token is required")
            return False

        queries = self.queries_text.get("1.0", tk.END).strip()
        if not queries:
            messagebox.showerror("Error", "At least one search keyword is required")
            return False

        if self.max_posts.get() < 1:
            messagebox.showerror("Error", "Max posts must be at least 1")
            return False

        return True

    def start_scraping(self):
        """Start scraping in a separate thread"""
        if self.is_running:
            messagebox.showwarning("Warning", "Scraping is already in progress")
            return

        if not self.validate_inputs():
            return

        # Start scraping in background thread
        self.is_running = True
        self.run_button.config(state='disabled')
        self.progress.start(10)
        self.update_status("Running...", "info")
        self.log("🚀 Starting scraping process...")

        thread = threading.Thread(target=self.run_scraping, daemon=True)
        thread.start()

    def run_scraping(self):
        """Main scraping logic (runs in background thread)"""
        try:
            # Parse queries
            queries_text = self.queries_text.get("1.0", tk.END).strip()
            queries = [q.strip() for q in queries_text.split("\n") if q.strip()]

            self.log(f"📋 Queries: {', '.join(queries)}")
            self.log(f"📊 Max posts per query: {self.max_posts.get()}")

            # Build run input
            run_input = {
                "mode": "search",
                "searchQueries": queries,
                "maxPosts": self.max_posts.get(),
                "includeProfile": False,
            }

            if self.posted_after_enabled.get():
                run_input["postedAfter"] = self.posted_after_picker.get()
                self.log(f"📅 Filter: Posted after {run_input['postedAfter']}")

            if self.posted_before_enabled.get():
                run_input["postedBefore"] = self.posted_before_picker.get()
                self.log(f"📅 Filter: Posted before {run_input['postedBefore']}")

            # Initialize Apify client
            client = ApifyClient(self.api_token.get().strip())
            actor_id = self.actor_id.get().strip()

            self.log(f"⚙️  Running actor: {actor_id}")
            self.log("⏳ Waiting for results...")

            # Run the actor
            run = client.actor(actor_id).call(run_input=run_input)

            # Handle response (compatible with both old and new apify-client)
            status = run.get("status") if isinstance(run, dict) else run.status
            dataset_id = run.get("defaultDatasetId") if isinstance(run, dict) else run.default_dataset_id

            if status != "SUCCEEDED":
                raise Exception(f"Actor run failed with status: {status}")

            self.log(f"✅ Actor run succeeded! Dataset ID: {dataset_id}")
            self.log("📥 Fetching results...")

            # Fetch results
            items = list(client.dataset(dataset_id).iterate_items())

            if not items:
                self.log("⚠️  No results found")
                self.root.after(0, lambda: self.update_status("No results found", "warning"))
                self.root.after(0, lambda: messagebox.showinfo("Info", "No results found"))
                return

            # Save to CSV
            output_path = self.output_file.get()
            with open(output_path, "w", encoding="utf-8", newline="") as f:
                fieldnames = list(items[0].keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(items)

            self.log(f"💾 Saved {len(items)} posts to {output_path}")

            # Show preview
            self.log("\n--- 📋 Preview (first 5 posts) ---")
            for item in items[:5]:
                username = item.get("username", "")
                text = (item.get("text") or "")[:60].replace("\n", " ")
                likes = item.get("likeCount", 0)
                self.log(f"  @{username} | ❤️  {likes} | {text}...")

            # Success
            self.root.after(0, lambda: self.update_status(f"✅ Complete! {len(items)} posts saved", "success"))
            self.root.after(0, lambda: messagebox.showinfo(
                "Success", f"Scraping complete!\n\n{len(items)} posts saved to:\n{output_path}"))

        except Exception as e:
            error_msg = str(e)
            self.log(f"❌ ERROR: {error_msg}")
            self.root.after(0, lambda: self.update_status("Error occurred", "error"))
            self.root.after(0, lambda: messagebox.showerror("Error", f"Scraping failed:\n\n{error_msg}"))

        finally:
            # Reset UI state
            self.is_running = False
            self.root.after(0, lambda: self.run_button.config(state='normal'))
            self.root.after(0, lambda: self.progress.stop())


def main():
    root = tk.Tk()
    app = ThreadsScraperApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()