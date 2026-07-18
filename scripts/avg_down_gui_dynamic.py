#!/usr/bin/env python3
"""
avg_down_gui_dynamic.py

Run:
    python avg_down_gui_dynamic.py

Interactive tkinter GUI with sliders and live calculation of additional shares
required to reach a target average price.
"""

import tkinter as tk
from tkinter import ttk
import math

def compute_required_shares(S0, P0, Pb, Pt):
    try:
        S0 = float(S0)
        P0 = float(P0)
        Pb = float(Pb)
        Pt = float(Pt)
    except Exception:
        return None, "Invalid numeric input."

    if S0 < 0 or P0 < 0 or Pb < 0 or Pt < 0:
        return None, "Inputs must be non-negative."

    if abs(Pt - Pb) < 1e-12:
        if abs(P0 - Pt) < 1e-12:
            return 0.0, "Already at target average."
        return math.inf, "Buy price equals target price; infinite shares required."

    numerator = S0 * (P0 - Pt)
    denominator = Pt - Pb
    x = numerator / denominator

    if x < 0:
        return math.inf, "Target cannot be reached by buying at this buy price."

    return x, "OK"

def format_money(x):
    try:
        return f"₹{float(x):,.2f}"
    except Exception:
        return str(x)

def update_from_inputs(*_):
    # Read entries and slider values
    s0 = entry_shares.get()
    p0 = entry_current_price.get()
    pb = buy_price_var.get()
    pt = target_price_var.get()
    rounding = rounding_var.get()

    result, reason = compute_required_shares(s0, p0, pb, pt)
    if result is None:
        label_result_value.config(text="Input error")
        label_details.config(text=reason)
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
        label_result_value.config(text="Input error")
        label_details.config(text="Invalid numeric input.")
        return

    cash_required = x_int * pb_f
    new_total_shares = s0_f + x_int
    new_total_cost = s0_f * p0_f + cash_required
    new_avg = new_total_cost / new_total_shares if new_total_shares > 0 else float('nan')

    label_result_value.config(
        text=f"{x_float:.6f} exact  →  {x_int} shares (rounded {rounding})"
    )
    label_details.config(
        text=f"Cash required {format_money(cash_required)}  •  New average {format_money(new_avg)}"
    )

def on_entry_change(event):
    # Keep sliders in sync with typed values where applicable
    try:
        pb_val = float(entry_buy_price.get())
        buy_price_var.set(pb_val)
    except Exception:
        pass
    try:
        pt_val = float(entry_target.get())
        target_price_var.set(pt_val)
    except Exception:
        pass
    update_from_inputs()

def on_slider_change_buy(val):
    entry_buy_price_var.set(f"{float(val):.2f}")
    update_from_inputs()

def on_slider_change_target(val):
    entry_target_var.set(f"{float(val):.2f}")
    update_from_inputs()

def on_clear():
    entry_shares.delete(0, tk.END)
    entry_shares.insert(0, "100")
    entry_current_price.delete(0, tk.END)
    entry_current_price.insert(0, "320.16")
    buy_price_var.set(280.0)
    target_price_var.set(281.75)
    entry_buy_price_var.set("280.00")
    entry_target_var.set("281.75")
    rounding_var.set("nearest")
    update_from_inputs()

# Build GUI
root = tk.Tk()
root.title("Average Price Calculator Dynamic")

frm = ttk.Frame(root, padding=12)
frm.grid(row=0, column=0, sticky="NSEW")

# Current holdings
ttk.Label(frm, text="Current shares").grid(row=0, column=0, sticky="W")
entry_shares = ttk.Entry(frm, width=14)
entry_shares.grid(row=0, column=1, sticky="W")
entry_shares.insert(0, "100")
entry_shares.bind("<KeyRelease>", on_entry_change)

ttk.Label(frm, text="Current average price ₹").grid(row=1, column=0, sticky="W")
entry_current_price = ttk.Entry(frm, width=14)
entry_current_price.grid(row=1, column=1, sticky="W")
entry_current_price.insert(0, "320.16")
entry_current_price.bind("<KeyRelease>", on_entry_change)

# Buy price with slider
ttk.Label(frm, text="Buy price per share ₹").grid(row=2, column=0, sticky="W")
buy_price_var = tk.DoubleVar(value=280.0)
slider_buy = ttk.Scale(frm, from_=0.0, to=1000.0, orient="horizontal",
                       variable=buy_price_var, command=on_slider_change_buy)
slider_buy.grid(row=2, column=1, sticky="EW", padx=(0,8))
entry_buy_price_var = tk.StringVar(value="280.00")
entry_buy_price = ttk.Entry(frm, width=10, textvariable=entry_buy_price_var)
entry_buy_price.grid(row=2, column=2, sticky="W")
entry_buy_price.bind("<KeyRelease>", on_entry_change)

# Target price with slider
ttk.Label(frm, text="Target average price ₹").grid(row=3, column=0, sticky="W")
target_price_var = tk.DoubleVar(value=281.75)
slider_target = ttk.Scale(frm, from_=0.0, to=1000.0, orient="horizontal",
                          variable=target_price_var, command=on_slider_change_target)
slider_target.grid(row=3, column=1, sticky="EW", padx=(0,8))
entry_target_var = tk.StringVar(value="281.75")
entry_target = ttk.Entry(frm, width=10, textvariable=entry_target_var)
entry_target.grid(row=3, column=2, sticky="W")
entry_target.bind("<KeyRelease>", on_entry_change)

# Rounding options
rounding_var = tk.StringVar(value="nearest")
ttk.Label(frm, text="Rounding").grid(row=4, column=0, sticky="W")
round_frame = ttk.Frame(frm)
round_frame.grid(row=4, column=1, sticky="W")
ttk.Radiobutton(round_frame, text="Nearest", variable=rounding_var, value="nearest",
                command=update_from_inputs).pack(side="left")
ttk.Radiobutton(round_frame, text="Up", variable=rounding_var, value="up",
                command=update_from_inputs).pack(side="left")
ttk.Radiobutton(round_frame, text="Down", variable=rounding_var, value="down",
                command=update_from_inputs).pack(side="left")

# Buttons
btn_frame = ttk.Frame(frm, padding=(0,8,0,0))
btn_frame.grid(row=5, column=0, columnspan=3, sticky="EW")
btn_calc = ttk.Button(btn_frame, text="Recalculate", command=update_from_inputs)
btn_calc.pack(side="left", padx=(0,8))
btn_clear = ttk.Button(btn_frame, text="Reset", command=on_clear)
btn_clear.pack(side="left")

# Results
ttk.Separator(frm, orient="horizontal").grid(row=6, column=0, columnspan=3, sticky="EW", pady=8)
label_result_title = ttk.Label(frm, text="Result", font=("Segoe UI", 10, "bold"))
label_result_title.grid(row=7, column=0, sticky="W")
label_result_value = ttk.Label(frm, text="", foreground="blue")
label_result_value.grid(row=7, column=1, columnspan=2, sticky="W")
label_details = ttk.Label(frm, text="", foreground="gray")
label_details.grid(row=8, column=0, columnspan=3, sticky="W")

# Make window responsive
for i in range(3):
    frm.columnconfigure(i, weight=1)

root.resizable(False, False)

# Initialize display
on_clear()
root.mainloop()
