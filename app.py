from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import csv, os
from datetime import datetime
from collections import defaultdict
from werkzeug.utils import secure_filename

app = Flask(__name__)
DATA_FILE = "expenses.csv"
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

savings_goal = 0.0
CATEGORIES = ["All", "Food", "Travel", "Bills", "Shopping", "Income", "Other"]

# --------------------------
# Helpers
# --------------------------
def init_file():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Name", "Category", "Amount"])

def load_expenses():
    with open(DATA_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)

def save_expense(date, name, category, amount):
    with open(DATA_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([date, name, category, amount])

def overwrite_expenses(rows):
    with open(DATA_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Date", "Name", "Category", "Amount"])
        writer.writerows(rows)

# --------------------------
# Routes
# --------------------------
@app.route("/", methods=["GET", "POST"])
def index():
    global savings_goal
    init_file()
    expenses = load_expenses()

    # Filters
    cat = request.args.get("cat", "All")
    mon = request.args.get("month", "All")
    yr = request.args.get("year", "All")

    filtered = []
    for e in expenses:
        ok = True
        try:
            dt = datetime.strptime(e["Date"], "%Y-%m-%d")
        except:
            continue
        if mon != "All":
            ok &= (dt.month == int(mon))
        if yr != "All":
            ok &= (dt.year == int(yr))
        if cat != "All":
            ok &= (cat.lower() == e["Category"].lower())
        if ok:
            filtered.append(e)

    # Totals
    total_exp = sum(float(e["Amount"]) for e in filtered if e["Category"].lower() != "income")
    total_inc = sum(float(e["Amount"]) for e in filtered if e["Category"].lower() == "income")
    balance = total_inc - total_exp

    return render_template("index.html", expenses=filtered,
                           total_exp=total_exp, total_inc=total_inc,
                           balance=balance, goal=savings_goal,
                           categories=CATEGORIES, selected_cat=cat)

@app.route("/add", methods=["POST"])
def add():
    date = request.form.get("date") or datetime.now().strftime("%Y-%m-%d")
    name = request.form["name"]
    category = request.form["category"]
    amount = request.form["amount"]
    save_expense(date, name, category, amount)
    return redirect(url_for("index"))

@app.route("/add_income", methods=["POST"])
def add_income():
    amount = request.form.get("income_amount")
    if not amount:
        return redirect(url_for("index"))
    try:
        amt = float(amount)
    except:
        return redirect(url_for("index"))
    today = datetime.now().strftime("%Y-%m-%d")
    save_expense(today, "Income", "Income", amt)
    return redirect(url_for("index"))

@app.route("/delete", methods=["POST"])
def delete():
    idx = int(request.form["index"])
    expenses = load_expenses()
    rows = [[e["Date"], e["Name"], e["Category"], e["Amount"]] for i, e in enumerate(expenses) if i != idx]
    overwrite_expenses(rows)
    return redirect(url_for("index"))

@app.route("/set_goal", methods=["POST"])
def set_goal():
    global savings_goal
    try:
        savings_goal = float(request.form["goal"])
    except:
        savings_goal = 0.0
    return redirect(url_for("index"))

@app.route("/chart_data")
def chart_data():
    expenses = load_expenses()
    totals = defaultdict(float)
    for e in expenses:
        totals[e["Category"]] += float(e["Amount"])
    return jsonify(totals)

@app.route("/monthly_trend")
def monthly_trend():
    expenses = load_expenses()
    monthly = defaultdict(float)
    for e in expenses:
        try:
            dt = datetime.strptime(e["Date"], "%Y-%m-%d")
        except:
            continue
        if e["Category"].lower() != "income":
            key = dt.strftime("%Y-%m")
            monthly[key] += float(e["Amount"])
    return jsonify(monthly)

@app.route("/export")
def export_filtered():
    return send_file(DATA_FILE, as_attachment=True)

@app.route("/load", methods=["POST"])
def load_csv():
    file = request.files["file"]
    if file and file.filename.endswith(".csv"):
        filename = secure_filename(file.filename)
        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        file.save(path)
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        if rows and rows[0] == ["Date", "Name", "Category", "Amount"]:
            rows = rows[1:]
        overwrite_expenses(rows)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
