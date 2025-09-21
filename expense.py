import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkcalendar import Calendar, DateEntry
from datetime import datetime
import csv
from collections import defaultdict
import matplotlib.pyplot as plt

expenses = []   # list of [date_str, name, category, amount_float]
last_shown = [] # used to export filtered data
savings_goal = 0.0

# ---------------------------
# Helper Functions
# ---------------------------
def parse_date_str(date_str):
    """Return datetime from 'YYYY-MM-DD' or try other common formats."""
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue
    raise ValueError(f"Unknown date format: {date_str}")

def refresh_table(data=None):
    """Refresh Treeview with provided data or the full expenses list."""
    global last_shown
    tree.delete(*tree.get_children())
    data = data if data is not None else expenses
    last_shown = data[:]  # shallow copy for export
    for r in data:
        # show amount with 2 decimals
        tree.insert("", tk.END, values=(r[0], r[1], r[2], f"{r[3]:.2f}"))
    update_status()

def update_status():
    """Update the summary/status area with totals and goal progress."""
    total_expense = sum(a for d, n, c, a in expenses if c.lower() != "income")
    total_income = sum(a for d, n, c, a in expenses if c.lower() == "income")
    balance = total_income - total_expense
    status_text = (f"Income: ₹{total_income:.2f}    |    "
                   f"Expense: ₹{total_expense:.2f}    |    "
                   f"Balance: ₹{balance:.2f}")
    status_label.config(text=status_text)
    # Savings goal progress
    if savings_goal > 0:
        progress = (balance / savings_goal) * 100
        prog_text = f"Savings goal: ₹{savings_goal:.2f} ({progress:.1f}%)"
    else:
        prog_text = "Savings goal: Not set"
    goal_label.config(text=prog_text)

def clear_inputs():
    name_entry.delete(0, tk.END)
    category_entry.delete(0, tk.END)
    amount_entry.delete(0, tk.END)
    # leave date as is

# ---------------------------
# Core Actions
# ---------------------------
def add_record():
    """Add expense or income record from inputs."""
    date_val = date_entry.get()
    name = name_entry.get().strip()
    category = category_entry.get().strip()
    amount_s = amount_entry.get().strip()

    if not (date_val and name and category and amount_s):
        messagebox.showwarning("Missing fields", "Please fill Date, Name, Category and Amount.")
        return

    try:
        amount = float(amount_s)
    except ValueError:
        messagebox.showerror("Invalid amount", "Please enter a valid number for amount.")
        return

    # Normalise date to YYYY-MM-DD for storage
    try:
        dt = parse_date_str(date_val)
        date_norm = dt.strftime("%Y-%m-%d")
    except ValueError:
        messagebox.showerror("Invalid date", "Could not parse the date. Use YYYY-MM-DD or pick from calendar.")
        return

    expenses.append([date_norm, name, category, amount])
    refresh_table()
    clear_inputs()

def delete_selected():
    sel = tree.selection()
    if not sel:
        messagebox.showwarning("No selection", "Please select a row to delete.")
        return
    # remove selected items from expenses (match by values)
    removed = 0
    for iid in sel:
        vals = tree.item(iid)["values"]
        # vals: [date, name, category, amount_str]
        amt = float(vals[3])
        record = [vals[0], vals[1], vals[2], amt]
        # remove first matching record
        for i, rec in enumerate(expenses):
            if rec[0] == record[0] and rec[1] == record[1] and rec[2] == record[2] and abs(rec[3] - record[3]) < 1e-9:
                del expenses[i]
                removed += 1
                break
        tree.delete(iid)
    if removed:
        update_status()

def save_csv():
    path = filedialog.asksaveasfilename(defaultextension=".csv",
                                        filetypes=[("CSV files", "*.csv")])
    if not path:
        return
    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Name", "Category", "Amount"])
            for r in expenses:
                writer.writerow([r[0], r[1], r[2], f"{r[3]:.2f}"])
        messagebox.showinfo("Saved", f"Saved {len(expenses)} records to:\n{path}")
    except Exception as e:
        messagebox.showerror("Save failed", str(e))

def load_csv():
    path = filedialog.askopenfilename(filetypes=[("CSV files", "*.csv")])
    if not path:
        return
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
        # detect header
        if rows and [c.strip().lower() for c in rows[0]] == ["date", "name", "category", "amount"]:
            rows = rows[1:]
        new = []
        for row in rows:
            if len(row) != 4:
                continue
            d, n, c, a = [x.strip() for x in row]
            try:
                amt = float(a)
            except:
                continue
            # normalise date
            try:
                dt = parse_date_str(d)
                d_norm = dt.strftime("%Y-%m-%d")
            except:
                d_norm = d  # keep as-is if parsing fails
            new.append([d_norm, n, c, amt])
        expenses.clear()
        expenses.extend(new)
        refresh_table()
        messagebox.showinfo("Loaded", f"Loaded {len(expenses)} records from:\n{path}")
    except Exception as e:
        messagebox.showerror("Load failed", str(e))

# ---------------------------
# Calendar Widget (popup)
# ---------------------------
def open_calendar():
    """Open a small calendar popup; selecting a date will set date_entry."""
    top = tk.Toplevel(root)
    top.title("Pick a date")
    # center popup relative to main window
    top.transient(root)
    cal = Calendar(top, selectmode="day", date_pattern="yyyy-mm-dd")
    cal.pack(padx=10, pady=10)
    def set_and_close():
        date = cal.get_date()
        # date is in yyyy-mm-dd because of pattern
        date_entry.set_date(date)
        top.destroy()
    select_btn = tk.Button(top, text="Select", command=set_and_close, bg=accent_color, fg="black")
    select_btn.pack(pady=(0,10))

# ---------------------------
# Filtering & Export filtered
# ---------------------------
def apply_filters():
    """Filter by month/year and/or category substring."""
    cat = filter_cat.get().strip().lower()
    mon = filter_month.get()
    yr = filter_year.get()
    filtered = []

    for r in expenses:
        # r: date, name, category, amount
        try:
            dt = parse_date_str(r[0])
        except:
            # attempt parse with stored format
            try:
                dt = datetime.strptime(r[0], "%Y-%m-%d")
            except:
                continue
        ok = True
        if mon != "All":
            ok = ok and (dt.month == int(mon))
        if yr != "All":
            ok = ok and (dt.year == int(yr))
        if cat:
            ok = ok and (cat in r[2].lower())
        if ok:
            filtered.append(r)
    refresh_table(filtered)

def export_filtered():
    if not last_shown:
        messagebox.showwarning("No data", "No filtered data to export. Apply filters first.")
        return
    path = filedialog.asksaveasfilename(defaultextension=".csv",
                                        filetypes=[("CSV files", "*.csv")])
    if not path:
        return
    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Name", "Category", "Amount"])
            for r in last_shown:
                writer.writerow([r[0], r[1], r[2], f"{r[3]:.2f}"])
        messagebox.showinfo("Exported", f"Exported {len(last_shown)} rows to:\n{path}")
    except Exception as e:
        messagebox.showerror("Export failed", str(e))

# ---------------------------
# Charts
# ---------------------------
def chart_by_category(data=None):
    if data is None:
        data = expenses
    if not data:
        messagebox.showwarning("No data", "No data to chart.")
        return
    totals = defaultdict(float)
    for r in data:
        totals[r[2]] += r[3]
    categories = list(totals.keys())
    amounts = list(totals.values())
    plt.figure(figsize=(7,5))
    plt.bar(categories, amounts)
    plt.title("Expenses by Category")
    plt.xlabel("Category")
    plt.ylabel("Amount (₹)")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.show()

def monthly_trend():
    if not expenses:
        messagebox.showwarning("No data", "No data to chart.")
        return
    month_totals = defaultdict(float)  # YYYY-MM -> sum expenses (excluding income)
    for r in expenses:
        try:
            dt = parse_date_str(r[0])
        except:
            continue
        key = dt.strftime("%Y-%m")
        if r[2].lower() != "income":
            month_totals[key] += r[3]
    if not month_totals:
        messagebox.showinfo("No expense data", "No expense (non-income) data to show.")
        return
    keys = sorted(month_totals.keys())
    vals = [month_totals[k] for k in keys]
    plt.figure(figsize=(8,4))
    plt.plot(keys, vals, marker='o')
    plt.title("Monthly Expense Trend")
    plt.xlabel("Month")
    plt.ylabel("Amount (₹)")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.show()

# ---------------------------
# Savings Goal
# ---------------------------
def set_goal():
    global savings_goal
    s = goal_entry.get().strip()
    if not s:
        savings_goal = 0.0
        update_status()
        messagebox.showinfo("Goal cleared", "Savings goal cleared.")
        return
    try:
        g = float(s)
        if g < 0:
            raise ValueError
        savings_goal = g
        update_status()
        messagebox.showinfo("Goal set", f"Savings goal set to ₹{g:.2f}")
    except:
        messagebox.showerror("Invalid", "Enter a valid positive number for goal.")

# ---------------------------
# UI setup
# ---------------------------
root = tk.Tk()
root.title("Fabulous Expense Tracker")
root.geometry("1000x700")
root.minsize(900,600)
root.configure(bg="#0b0f12")  # deep black

# Accent colors (not gloomy)
accent_color = "#1dd3b0"   # turquoise-ish
button_color = "#ffd166"   # warm yellow
muted_bg = "#0f1720"
panel_bg = "#0f1720"
text_fg = "#F8F9FA"

# Header
header = tk.Frame(root, bg=panel_bg, pady=12)
header.pack(fill="x")
title = tk.Label(header, text="💠 Fabulous Expense Tracker", bg=panel_bg, fg=text_fg,
                 font=("Segoe UI", 18, "bold"))
title.pack(side="left", padx=14)

# Left: Input panel
left = tk.Frame(root, bg=panel_bg, bd=0, padx=12, pady=12)
left.pack(side="left", fill="y")

tk.Label(left, text="Date", bg=panel_bg, fg=text_fg).grid(row=0, column=0, sticky="w")
date_entry = DateEntry(left, date_pattern="yyyy-mm-dd", background="white", foreground="black", borderwidth=1)
date_entry.grid(row=0, column=1, pady=6, padx=6)

cal_btn = tk.Button(left, text="📅", command=open_calendar, bg=accent_color, fg="black", width=3)
cal_btn.grid(row=0, column=2, padx=4)

tk.Label(left, text="Name", bg=panel_bg, fg=text_fg).grid(row=1, column=0, sticky="w")
name_entry = tk.Entry(left, width=22)
name_entry.grid(row=1, column=1, columnspan=2, pady=6, padx=6)

tk.Label(left, text="Category", bg=panel_bg, fg=text_fg).grid(row=2, column=0, sticky="w")
category_entry = tk.Entry(left, width=22)
category_entry.grid(row=2, column=1, columnspan=2, pady=6, padx=6)

tk.Label(left, text="Amount (₹)", bg=panel_bg, fg=text_fg).grid(row=3, column=0, sticky="w")
amount_entry = tk.Entry(left, width=22)
amount_entry.grid(row=3, column=1, columnspan=2, pady=6, padx=6)

add_btn = tk.Button(left, text="Add Record", bg=button_color, fg="black", width=20, command=add_record)
add_btn.grid(row=4, column=0, columnspan=3, pady=10)

delete_btn = tk.Button(left, text="Delete Selected", bg="#ff6b6b", fg="black", width=20, command=delete_selected)
delete_btn.grid(row=5, column=0, columnspan=3, pady=6)

# Income quick add
tk.Label(left, text="Quick Add Income (₹)", bg=panel_bg, fg=text_fg).grid(row=6, column=0, sticky="w", pady=(12,0))
income_q = tk.Entry(left, width=12)
income_q.grid(row=6, column=1, pady=(12,0))
def quick_income():
    s = income_q.get().strip()
    if not s:
        return
    try:
        amt = float(s)
    except:
        messagebox.showerror("Invalid", "Enter valid number for income.")
        return
    # add income record with category "Income"
    today = datetime.now().strftime("%Y-%m-%d")
    expenses.append([today, "Income", "Income", amt])
    income_q.delete(0, tk.END)
    refresh_table()
tk.Button(left, text="Add Income", bg=accent_color, fg="black", command=quick_income).grid(row=6, column=2, padx=4, pady=(12,0))

# Savings goal
tk.Label(left, text="Savings Goal (₹)", bg=panel_bg, fg=text_fg).grid(row=7, column=0, sticky="w", pady=(14,0))
goal_entry = tk.Entry(left, width=12)
goal_entry.grid(row=7, column=1, pady=(14,0))
tk.Button(left, text="Set Goal", bg="#9b5de5", fg="white", command=set_goal).grid(row=7, column=2, padx=4, pady=(14,0))

# Filters
tk.Label(left, text="--- Filters ---", bg=panel_bg, fg=text_fg, font=("Segoe UI", 10, "bold")).grid(row=8, column=0, columnspan=3, pady=(18,6))

tk.Label(left, text="Category contains:", bg=panel_bg, fg=text_fg).grid(row=9, column=0, sticky="w")
filter_cat = tk.Entry(left, width=18)
filter_cat.grid(row=9, column=1, columnspan=2, pady=4)

tk.Label(left, text="Month:", bg=panel_bg, fg=text_fg).grid(row=10, column=0, sticky="w")
months = ["All"] + [str(i) for i in range(1,13)]
filter_month = ttk.Combobox(left, values=months, width=6, state="readonly")
filter_month.set("All")
filter_month.grid(row=10, column=1, pady=4)

tk.Label(left, text="Year:", bg=panel_bg, fg=text_fg).grid(row=11, column=0, sticky="w")
this_year = datetime.now().year
years = ["All"] + [str(y) for y in range(this_year-5, this_year+6)]
filter_year = ttk.Combobox(left, values=years, width=8, state="readonly")
filter_year.set("All")
filter_year.grid(row=11, column=1, pady=4)

tk.Button(left, text="Apply Filters", bg="#6c5ce7", fg="white", command=apply_filters).grid(row=12, column=0, columnspan=3, pady=8)
tk.Button(left, text="Export Filtered", bg="#00b894", fg="black", command=export_filtered).grid(row=13, column=0, columnspan=3, pady=6)

# Left padding filler
left.grid_rowconfigure(14, weight=1)

# Right: Table & Charts
right = tk.Frame(root, bg="#071019", padx=10, pady=10)
right.pack(side="left", fill="both", expand=True)

# Top controls
top_controls = tk.Frame(right, bg="#071019")
top_controls.pack(fill="x", pady=(0,6))
tk.Button(top_controls, text="Load CSV", bg="#f78fb3", fg="black", command=load_csv).pack(side="left", padx=6)
tk.Button(top_controls, text="Save CSV", bg="#00b894", fg="black", command=save_csv).pack(side="left", padx=6)
tk.Button(top_controls, text="Category Chart", bg="#00a8ff", fg="black", command=lambda: chart_by_category()).pack(side="left", padx=6)
tk.Button(top_controls, text="Monthly Trend", bg="#ff9f1c", fg="black", command=monthly_trend).pack(side="left", padx=6)

# Treeview
cols = ("Date", "Name", "Category", "Amount (₹)")
tree = ttk.Treeview(right, columns=cols, show="headings", height=18)
for c in cols:
    tree.heading(c, text=c)
    tree.column(c, anchor="center")
tree.pack(fill="both", expand=True)

# Status and goal
status_bar = tk.Frame(right, bg="#071019")
status_bar.pack(fill="x", pady=(8,0))
status_label = tk.Label(status_bar, text="Income: ₹0.00    |    Expense: ₹0.00    |    Balance: ₹0.00",
                        bg="#071019", fg=text_fg, font=("Segoe UI", 10))
status_label.pack(side="left", padx=6)
goal_label = tk.Label(status_bar, text="Savings goal: Not set", bg="#071019", fg=text_fg, font=("Segoe UI", 10, "italic"))
goal_label.pack(side="right", padx=6)
footer = tk.Label(root, text="Tip: Mark incomes with Category = 'Income' so they count as income.", bg="#0b0f12", fg="#b2bec3")
footer.pack(side="bottom", fill="x", pady=6)
refresh_table()
root.mainloop()
