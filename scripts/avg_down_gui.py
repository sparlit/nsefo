#!/usr/bin/env python3
"""
avg_down_gui.py

Run:
    python avg_down_gui.py

A simple tkinter GUI to compute additional shares required to reach a target average price.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import math

def compute_required_shares(S0, P0, Pb, Pt):
    """
    Returns (x_float, reason) where x_float is fractional shares required or math.inf.
    """
    # Validate numeric inputs
    try:
        S0 = float(S0)
        P0 = float(P0)
        Pb = float(Pb)
        Pt = float(Pt)
    except Exception:
        return None, "Invalid numeric input."

    if S0 < 0 or P0 < 0 or Pb < 0 or Pt < 0:
        return None, "Inputs must be non-negative."

    # If target equals buy price
    if abs(Pt - Pb) < 1e-12:
        if abs(P0 - Pt) < 1e-12:
            return 0.0, "You already have the target average."
        return math.inf, "Buy price equals target price; infinite shares required to reach target exactly."

    numerator = S0 * (P0 - Pt)
    denominator = Pt - Pb

    # If denominator zero handled above. If x negative -> unreachable by buying at Pb
    x = numerator / denominator

    if x < 0:
        return math.inf, "Target average cannot be reached by buying at this buy price."

    return x, "Computed fractional shares required."

def on_calculate():
    s0 = entry_shares.get().strip()
    p0 = entry_current_price.get().strip()
    pb = entry_buy_price.get().strip()
    pt = entry_target.get().strip()
    rounding = rounding_var.get()

    result, reason = compute_required_shares(s0, p0, pb, pt)
    if result is None:
        messagebox.showerror("Input error", reason)
        return

    if math.isinf(result):
        label_result_value.config(text="Impossible with given buy price")
        label_details.config(text=reason)
        return

    x_float = result
    if rounding == "up":
        x_int = math.ceil(x_float)
    elif rounding == "down":
        x_int = math.floor(x_float)
    else:
        x_int = int(round(x_float))

    try:
        pb_f = float(pb)
        s0_f = float(s0)
        p0_f = float(p0)
    except Exception:
        messagebox.showerror("Input error", "Invalid numeric input.")
        return

    cash_required = x_int * pb_f
    new_total_shares = s0_f + x_int
    new_total_cost = s0_f * p0_f + cash_required
    new_avg = new_total_cost / new_total_shares if new_total_shares > 0 else float('nan')

    label_result_value.config(text=f"{x_float:.6f} (exact)  →  {x_int} shares (rounded)")
    label_details.config(text=f"Cash required ₹{cash_required:,.2f}  •  New average ₹{new_avg:,.4f}")

def on_clear():
    entry_shares.delete(0, tk.END)
    entry_current_price.delete(0, tk.END)
    entry_buy_price.delete(0, tk.END)
    entry_target.delete(0, tk.END)
    rounding_var.set("nearest")
    label_result_value.config(text="")
    label_details.config(text="")

# Build GUI
root = tk.Tk()
root.title("Average Price Calculator")

frm = ttk.Frame(root, padding=12)
frm.grid(row=0, column=0, sticky="NSEW")

# Inputs
ttk.Label(frm, text="Current shares").grid(row=0, column=0, sticky="W")
entry_shares = ttk.Entry(frm, width=20)
entry_shares.grid(row=0, column=1, sticky="W")
entry_shares.insert(0, "100")

ttk.Label(frm, text="Current average price (₹)").grid(row=1, column=0, sticky="W")
entry_current_price = ttk.Entry(frm, width=20)
entry_current_price.grid(row=1, column=1, sticky="W")
entry_current_price.insert(0, "320.16")

ttk.Label(frm, text="Buy price per share (₹)").grid(row=2, column=0, sticky="W")
entry_buy_price = ttk.Entry(frm, width=20)
entry_buy_price.grid(row=2, column=1, sticky="W")
entry_buy_price.insert(0, "280")

ttk.Label(frm, text="Target average price (₹)").grid(row=3, column=0, sticky="W")
entry_target = ttk.Entry(frm, width=20)
entry_target.grid(row=3, column=1, sticky="W")
entry_target.insert(0, "281.75")

# Rounding options
rounding_var = tk.StringVar(value="nearest")
ttk.Label(frm, text="Rounding").grid(row=4, column=0, sticky="W")
round_frame = ttk.Frame(frm)
round_frame.grid(row=4, column=1, sticky="W")
ttk.Radiobutton(round_frame, text="Nearest", variable=rounding_var, value="nearest").pack(side="left")
ttk.Radiobutton(round_frame, text="Up", variable=rounding_var, value="up").pack(side="left")
ttk.Radiobutton(round_frame, text="Down", variable=rounding_var, value="down").pack(side="left")

# Buttons
btn_frame = ttk.Frame(frm, padding=(0,8,0,0))
btn_frame.grid(row=5, column=0, columnspan=2, sticky="EW")
btn_calc = ttk.Button(btn_frame, text="Calculate", command=on_calculate)
btn_calc.pack(side="left", padx=(0,8))
btn_clear = ttk.Button(btn_frame, text="Clear", command=on_clear)
btn_clear.pack(side="left")

# Results
ttk.Separator(frm, orient="horizontal").grid(row=6, column=0, columnspan=2, sticky="EW", pady=8)
label_result_title = ttk.Label(frm, text="Result", font=("Segoe UI", 10, "bold"))
label_result_title.grid(row=7, column=0, sticky="W")
label_result_value = ttk.Label(frm, text="", foreground="blue")
label_result_value.grid(row=7, column=1, sticky="W")
label_details = ttk.Label(frm, text="", foreground="gray")
label_details.grid(row=8, column=0, columnspan=2, sticky="W")

# Make window responsive
for i in range(2):
    frm.columnconfigure(i, weight=1)

root.resizable(False, False)
root.mainloop()
