#!/usr/bin/env python3
"""
avg_down_gui_lots.py

Run:
    python avg_down_gui_lots.py

Tkinter GUI that calculates additional shares required to reach a target average,
with lot and lot size controls, auto-calculation modes, sliders, and live updates.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import math

# ---------- Core math helpers ----------
def compute_required_shares(S0, P0, Pb, Pt):
    """
    Compute fractional additional shares x required so that new average equals Pt:
      x = S0 * (P0 - Pt) / (Pt - Pb)
    Returns (x_float, reason) where x_float may be math.inf if impossible.
    """
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
        return math.inf, "Buy price equals reference price; infinite shares required."

    numerator = S0 * (P0 - Pt)
    denominator = Pt - Pb
    x = numerator / denominator

    if x < 0:
        return math.inf, "Target cannot be reached by buying at this buy price."

    return x, "OK"

def new_average_after_buy(S0, P0, x, Pb):
    """Return new average after buying x shares at price Pb."""
    try:
        S0 = float(S0)
        P0 = float(P0)
        x = float(x)
        Pb = float(Pb)
    except Exception:
        return float('nan')
    if S0 + x <= 0:
        return float('nan')
    total_cost = S0 * P0 + x * Pb
    return total_cost / (S0 + x)

def format_money(x):
    try:
        return f"₹{float(x):,.2f}"
    except Exception:
        return str(x)

# ---------- GUI logic ----------
def update_from_inputs(*_):
    # Read base inputs
    try:
        s0 = float(entry_shares.get())
        p0 = float(entry_current_price.get())
    except Exception:
        label_result_value.config(text="Invalid current holdings")
        return

    pb = buy_price_var.get()
    rounding = rounding_var.get()
    auto_breakeven = auto_breakeven_var.get()
    auto_apply_lots = auto_apply_lots_var.get()
    auto_target_from_lots = auto_target_from_lots_var.get()
    auto_lots_from_target = auto_lots_from_target_var.get()

    # Lot inputs
    try:
        lot_count = int(entry_lot_count.get())
        lot_size = int(entry_lot_size.get())
    except Exception:
        lot_count = 0
        lot_size = 0

    lot_shares = lot_count * lot_size
    entry_lot_shares_var.set(str(lot_shares))

    # Determine additional shares to use for "simulate buy"
    if auto_apply_lots:
        additional_shares_for_sim = lot_shares
    else:
        # if user typed additional shares manually, use that field
        try:
            additional_shares_for_sim = int(entry_additional_shares.get())
        except Exception:
            additional_shares_for_sim = 0

    # If auto-target-from-lots is enabled, set target to the new average after buying lot_shares at pb
    if auto_target_from_lots:
        pt = new_average_after_buy(s0, p0, lot_shares, pb)
        entry_target_var.set(f"{pt:.4f}")
        target_price_var.set(pt)
    else:
        # read target from entry/slider
        pt = target_price_var.get()

    # If auto-lots-from-target is enabled, compute required shares to reach target and convert to lots
    if auto_lots_from_target:
        x_req, reason = compute_required_shares(s0, p0, pb, pt)
        if x_req is None or math.isinf(x_req):
            label_lots_needed.config(text="Unreachable or invalid")
        else:
            # convert to lots
            lots_needed = math.ceil(x_req / max(1, lot_size)) if lot_size > 0 else math.inf
            shares_covered = lots_needed * lot_size
            label_lots_needed.config(text=f"{x_req:.6f} exact → {lots_needed} lots ({shares_covered} shares)")
    else:
        label_lots_needed.config(text="—")

    # Compute required shares to reach target average (main calculation)
    result, reason = compute_required_shares(s0, p0, pb, pt)
    if result is None:
        label_result_value.config(text="Input error")
        label_details.config(text=reason)
        return

    if math.isinf(result):
        label_result_value.config(text="Target unreachable with this buy price")
        label_details.config(text=reason)
    else:
        x_float = result
        if rounding == "up":
            x_int = math.ceil(x_float)
        elif rounding == "down":
            x_int = math.floor(x_float)
        else:
            x_int = int(round(x_float))

        cash_required = x_int * pb
        new_total_shares = s0 + x_int
        new_total_cost = s0 * p0 + cash_required
        new_avg = new_total_cost / new_total_shares if new_total_shares > 0 else float('nan')

        label_result_value.config(text=f"{x_float:.6f} exact → {x_int} shares (rounded {rounding})")
        label_details.config(text=f"Cash required {format_money(cash_required)}  •  New average {format_money(new_avg)}")

    # Show current breakeven and breakeven after buying the simulated additional shares
    current_breakeven = p0 if s0 > 0 else float('nan')
    label_breakeven_current.config(text=f"{format_money(current_breakeven)}")

    # New average if we buy the additional_shares_for_sim at pb
    new_avg_sim = new_average_after_buy(s0, p0, additional_shares_for_sim, pb)
    label_breakeven_newavg.config(text=f"{format_money(new_avg_sim)}")

    # Shares needed to reach reference price
    try:
        ref_price = float(entry_ref_price_var.get())
    except Exception:
        label_breakeven_needed.config(text="Invalid reference")
        return

    x_ref, reason_ref = compute_required_shares(s0, p0, pb, ref_price)
    if x_ref is None:
        label_breakeven_needed.config(text="Error")
    elif math.isinf(x_ref):
        label_breakeven_needed.config(text="Unreachable (infinite or invalid)")
    else:
        x_ref_int = int(math.ceil(x_ref))
        cash_ref = x_ref_int * pb
        # convert to lots if lot_size > 0
        if lot_size > 0:
            lots_ref = x_ref_int // lot_size
            leftover = x_ref_int % lot_size
            label_breakeven_needed.config(
                text=f"{x_ref:.6f} exact → {x_ref_int} shares; {lots_ref} lots + {leftover} shares; cash {format_money(cash_ref)}"
            )
        else:
            label_breakeven_needed.config(text=f"{x_ref:.6f} exact → {x_ref_int} shares; cash {format_money(cash_ref)}")

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
    # Initialize defaults
    entry_shares.delete(0, tk.END); entry_shares.insert(0, "100")
    entry_current_price.delete(0, tk.END); entry_current_price.insert(0, "320.16")
    buy_price_var.set(280.0); entry_buy_price_var.set("280.00")
    target_price_var.set(281.75); entry_target_var.set("281.75")
    entry_additional_shares.delete(0, tk.END); entry_additional_shares.insert(0, "0")
    entry_lot_count.delete(0, tk.END); entry_lot_count.insert(0, "0")
    entry_lot_size.delete(0, tk.END); entry_lot_size.insert(0, "50")
    entry_lot_shares_var.set("0")
    entry_ref_price_var.set("280.00")
    rounding_var.set("nearest")
    auto_apply_lots_var.set(True)
    auto_target_from_lots_var.set(True)
    auto_lots_from_target_var.set(False)
    update_from_inputs()

# ---------- Build GUI ----------
root = tk.Tk()
root.title("Average Price Calculator with Lots and Auto Breakeven")

frm = ttk.Frame(root, padding=12)
frm.grid(row=0, column=0, sticky="NSEW")

# Current holdings
ttk.Label(frm, text="Current shares").grid(row=0, column=0, sticky="W")
entry_shares = ttk.Entry(frm, width=14)
entry_shares.grid(row=0, column=1, sticky="W")
entry_shares.bind("<KeyRelease>", on_entry_change)

ttk.Label(frm, text="Current average price ₹").grid(row=1, column=0, sticky="W")
entry_current_price = ttk.Entry(frm, width=14)
entry_current_price.grid(row=1, column=1, sticky="W")
entry_current_price.bind("<KeyRelease>", on_entry_change)

# Buy price with slider
ttk.Label(frm, text="Buy price per share ₹").grid(row=2, column=0, sticky="W")
buy_price_var = tk.DoubleVar(value=280.0)
slider_buy = ttk.Scale(frm, from_=0.0, to=5000.0, orient="horizontal",
                       variable=buy_price_var, command=on_slider_change_buy)
slider_buy.grid(row=2, column=1, sticky="EW", padx=(0,8))
entry_buy_price_var = tk.StringVar(value="280.00")
entry_buy_price = ttk.Entry(frm, width=12, textvariable=entry_buy_price_var)
entry_buy_price.grid(row=2, column=2, sticky="W")
entry_buy_price.bind("<KeyRelease>", on_entry_change)

# Target price with slider
ttk.Label(frm, text="Target average price ₹").grid(row=3, column=0, sticky="W")
target_price_var = tk.DoubleVar(value=281.75)
slider_target = ttk.Scale(frm, from_=0.0, to=5000.0, orient="horizontal",
                          variable=target_price_var, command=on_slider_change_target)
slider_target.grid(row=3, column=1, sticky="EW", padx=(0,8))
entry_target_var = tk.StringVar(value="281.75")
entry_target = ttk.Entry(frm, width=12, textvariable=entry_target_var)
entry_target.grid(row=3, column=2, sticky="W")
entry_target.bind("<KeyRelease>", on_entry_change)

# Additional shares manual field
ttk.Label(frm, text="Additional shares to simulate").grid(row=4, column=0, sticky="W")
entry_additional_shares = ttk.Entry(frm, width=14)
entry_additional_shares.grid(row=4, column=1, sticky="W")
entry_additional_shares.insert(0, "0")
entry_additional_shares.bind("<KeyRelease>", on_entry_change)

# Lot controls
ttk.Separator(frm, orient="horizontal").grid(row=5, column=0, columnspan=3, sticky="EW", pady=6)
ttk.Label(frm, text="Lot Count").grid(row=6, column=0, sticky="W")
entry_lot_count = ttk.Entry(frm, width=10)
entry_lot_count.grid(row=6, column=1, sticky="W")
entry_lot_count.insert(0, "0")
entry_lot_count.bind("<KeyRelease>", on_entry_change)

ttk.Label(frm, text="Lot Size").grid(row=6, column=2, sticky="W")
entry_lot_size = ttk.Entry(frm, width=10)
entry_lot_size.grid(row=6, column=3, sticky="W")
entry_lot_size.insert(0, "50")
entry_lot_size.bind("<KeyRelease>", on_entry_change)

ttk.Label(frm, text="Lot derived shares").grid(row=7, column=0, sticky="W")
entry_lot_shares_var = tk.StringVar(value="0")
entry_lot_shares = ttk.Entry(frm, width=14, textvariable=entry_lot_shares_var, state="readonly")
entry_lot_shares.grid(row=7, column=1, sticky="W")

# Auto options
auto_apply_lots_var = tk.BooleanVar(value=True)
auto_target_from_lots_var = tk.BooleanVar(value=True)
auto_lots_from_target_var = tk.BooleanVar(value=False)
auto_frame = ttk.Frame(frm)
auto_frame.grid(row=8, column=0, columnspan=4, sticky="W", pady=(6,0))
ttk.Checkbutton(auto_frame, text="Auto apply lots as additional shares", variable=auto_apply_lots_var,
                command=update_from_inputs).pack(side="left", padx=(0,8))
ttk.Checkbutton(auto_frame, text="Auto set target to new avg after lots", variable=auto_target_from_lots_var,
                command=update_from_inputs).pack(side="left", padx=(0,8))
ttk.Checkbutton(auto_frame, text="Auto compute lots needed from target", variable=auto_lots_from_target_var,
                command=update_from_inputs).pack(side="left")

# Rounding options
rounding_var = tk.StringVar(value="nearest")
ttk.Label(frm, text="Rounding").grid(row=9, column=0, sticky="W", pady=(8,0))
round_frame = ttk.Frame(frm)
round_frame.grid(row=9, column=1, sticky="W", pady=(8,0))
ttk.Radiobutton(round_frame, text="Nearest", variable=rounding_var, value="nearest",
                command=update_from_inputs).pack(side="left")
ttk.Radiobutton(round_frame, text="Up", variable=rounding_var, value="up",
                command=update_from_inputs).pack(side="left")
ttk.Radiobutton(round_frame, text="Down", variable=rounding_var, value="down",
                command=update_from_inputs).pack(side="left")

# Reference price for breakeven
ttk.Label(frm, text="Reference price for breakeven ₹").grid(row=10, column=0, sticky="W", pady=(8,0))
entry_ref_price_var = tk.StringVar(value="280.00")
entry_ref_price = ttk.Entry(frm, width=14, textvariable=entry_ref_price_var)
entry_ref_price.grid(row=10, column=1, sticky="W")
entry_ref_price.bind("<KeyRelease>", on_entry_change)

auto_breakeven_var = tk.BooleanVar(value=False)
ttk.Checkbutton(frm, text="Auto-calc Breakeven by Averaging", variable=auto_breakeven_var,
                command=update_from_inputs).grid(row=10, column=2, sticky="W")

# Buttons
btn_frame = ttk.Frame(frm, padding=(0,8,0,0))
btn_frame.grid(row=11, column=0, columnspan=4, sticky="EW")
ttk.Button(btn_frame, text="Recalculate", command=update_from_inputs).pack(side="left", padx=(0,8))
ttk.Button(btn_frame, text="Reset to defaults", command=on_clear).pack(side="left")

# Results
ttk.Separator(frm, orient="horizontal").grid(row=12, column=0, columnspan=4, sticky="EW", pady=8)
label_result_title = ttk.Label(frm, text="Result", font=("Segoe UI", 10, "bold"))
label_result_title.grid(row=13, column=0, sticky="W")
label_result_value = ttk.Label(frm, text="", foreground="blue")
label_result_value.grid(row=13, column=1, columnspan=3, sticky="W")
label_details = ttk.Label(frm, text="", foreground="gray")
label_details.grid(row=14, column=0, columnspan=4, sticky="W")

# Breakeven panel
ttk.Separator(frm, orient="horizontal").grid(row=15, column=0, columnspan=4, sticky="EW", pady=8)
ttk.Label(frm, text="Breakeven", font=("Segoe UI", 10, "bold")).grid(row=16, column=0, sticky="W")
ttk.Label(frm, text="Current breakeven (your avg cost)").grid(row=17, column=0, sticky="W")
label_breakeven_current = ttk.Label(frm, text="", foreground="black")
label_breakeven_current.grid(row=17, column=1, sticky="W")
ttk.Label(frm, text="Breakeven after simulated purchase").grid(row=18, column=0, sticky="W")
label_breakeven_newavg = ttk.Label(frm, text="", foreground="black")
label_breakeven_newavg.grid(row=18, column=1, sticky="W")
ttk.Label(frm, text="Shares/Lots needed to reach reference").grid(row=19, column=0, sticky="W")
label_breakeven_needed = ttk.Label(frm, text="", foreground="black")
label_breakeven_needed.grid(row=19, column=1, columnspan=3, sticky="W")
ttk.Label(frm, text="Lots needed when auto-lots-from-target enabled").grid(row=20, column=0, sticky="W")
label_lots_needed = ttk.Label(frm, text="—", foreground="black")
label_lots_needed.grid(row=20, column=1, columnspan=3, sticky="W")

# Make window responsive
for i in range(4):
    frm.columnconfigure(i, weight=1)

root.resizable(False, False)

# Initialize defaults and start
on_clear()
root.mainloop()
