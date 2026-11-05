"""Vistra (VST) — DCF (FCFF), SOTP, through-cycle, ladder, PIE.
Inputs: 10-K FY2025, 10-Q Q2-2026, Q2-26 release (Aug 7 2026), Cogentrix 8-K (Nov 5 2026), yfinance 4 Nov 2026 close.
$ millions unless stated."""
import json

PRICE = 120.29                      # 4 Nov 2026 close
SH = 335.6 + 5.0                    # yfinance basic shares + 5.0M issued to Cogentrix seller (30 Oct 2026)
MCAP = PRICE * SH
# Net debt pro forma for Cogentrix: Q2-26 net debt 19,460 - est. Q3 retained FCF ~500 + 2,300 cash + 1,700 assumed debt
NET_DEBT = 19460 - 500 + 2300 + 1700
PREF = 2476                         # preferred stock at liquidation value (10-K)
ARO_NONNUC = 842 * (1 - 0.21)       # land reclamation / coal ash ARO, after tax
PENSION = (101 + 88) * (1 - 0.21)   # pension + OPEB deficit, after tax
DEBT_LIKE = ARO_NONNUC + PENSION    # nuclear AROs covered by NDTs (Comanche regulatory; PJM NDTs > ARO) -> not deducted
CLAIMS = NET_DEBT + PREF + DEBT_LIKE

RF, ERP, BETA = 4.98, 5.0, 1.375     # FRED DGS10 29 Oct 2026; yfinance beta (inside 0.7-1.4 clip)
KE = (RF + BETA * ERP) / 100
KD_PRE, TAX, KP = 0.060, 0.21, 0.075
D, P, E = NET_DEBT, PREF, MCAP
V = D + P + E
WACC = E / V * KE + D / V * KD_PRE * (1 - TAX) + P / V * KP

YEARS = [2027, 2028, 2029, 2030, 2031]
# Ongoing-ops Adj. EBITDA incl. Cogentrix (~$550M run-rate, our estimate) and Meta/AWS ramp
SCEN = {
 "Bear":      ([7600, 7000, 6800, 6800, 6900], 0.010),
 "Base":      ([8100, 8400, 8650, 8850, 9000], 0.020),
 "Consensus": ([8600, 8900, 9150, 9350, 9500], 0.020),
 "Bull":      ([8500, 9200, 9800, 10300, 10600], 0.025),
}
MAINT = [1700, 1720, 1750, 1780, 1800]      # maintenance capex + nuclear fuel (2025: 2,104; 2026 plan 1,562 + Cogentrix)
GROWTH = [1300, 1300, 1100, 900, 700]       # Permian units, uprates (DOE loan), repowerings, solar, Helix
TAX_DA = 2600                               # tax-deductible D&A incl. nuclear fuel amortisation (approx.)
CASH_TAX = [0.10, 0.14, 0.17, 0.19, 0.21]   # NOLs / PTC transfers / CAMT -> statutory by 2031
RONIC = 0.12


def run(name, wacc=None, g=None, ebitda=None):
    wacc = WACC if wacc is None else wacc
    eb, g0 = SCEN[name] if ebitda is None else (ebitda, SCEN[name][1])
    g = g0 if g is None else g
    pv, rows = 0.0, []
    for i, (e, m, gc, t) in enumerate(zip(eb, MAINT, GROWTH, CASH_TAX), 1):
        tax = max(e - TAX_DA, 0) * t
        f = e - m - gc - tax
        pv += f / (1 + wacc) ** i
        rows.append(dict(year=YEARS[i - 1], ebitda=e, maint=m, growth=gc, tax=tax, fcff=f))
    e5 = eb[-1] * (1 + g)
    nopat = (e5 - TAX_DA * (1 + g)) * (1 - TAX)
    reinv = g / RONIC * nopat
    f_t = e5 - MAINT[-1] * (1 + g) - (e5 - TAX_DA * (1 + g)) * TAX - reinv
    tv = f_t / (wacc - g)
    pv_tv = tv / (1 + wacc) ** 5
    ev = pv + pv_tv
    eq = ev - CLAIMS
    return dict(rows=rows, ev=ev, tv_share=pv_tv / ev, equity=eq, per_sh=eq / SH,
                exit_mult=tv / eb[-1], ev_ebitda27=ev / eb[0])


out = {"inputs": dict(PRICE=PRICE, SH=SH, MCAP=MCAP, NET_DEBT=NET_DEBT, PREF=PREF, DEBT_LIKE=DEBT_LIKE,
                      CLAIMS=CLAIMS, KE=KE, WACC=WACC, DV=D / V, PV=P / V, EV=MCAP + CLAIMS)}
print(f"Mcap {MCAP:,.0f} | net debt {NET_DEBT:,.0f} | pref {PREF:,} | debt-like {DEBT_LIKE:,.0f} | EV {MCAP+CLAIMS:,.0f}")
print(f"Ke {KE:.2%} | WACC {WACC:.2%} (E {E/V:.0%} D {D/V:.0%} P {P/V:.0%})")
for s in SCEN:
    r = run(s); out[s] = r
    print(f"\n== {s}: EV {r['ev']:,.0f} (TV {r['tv_share']:.0%}, exit {r['exit_mult']:.1f}x) -> ${r['per_sh']:.1f} ({r['per_sh']/PRICE-1:+.0%}) | EV/EBITDA27 {r['ev_ebitda27']:.1f}x")
    for x in r["rows"]:
        print(f"   {x['year']} EBITDA {x['ebitda']:,} maint {x['maint']:,} growth {x['growth']:,} tax {x['tax']:,.0f} FCFF {x['fcff']:,.0f}")

out["stress"] = {s: run(s, wacc=WACC + 0.03)["per_sh"] for s in ["Bear", "Base", "Bull"]}
print("\nWACC+3:", {k: round(v, 1) for k, v in out["stress"].items()})
lo, hi = 0.04, 0.30
for _ in range(60):
    mid = (lo + hi) / 2
    (lo, hi) = (mid, hi) if run("Bear", wacc=mid)["per_sh"] > PRICE else (lo, mid)
out["wacc_bear_eq_price"] = mid; print(f"WACC where Bear = price: {mid:.2%}")
lo, hi = 0.04, 0.30
for _ in range(60):
    mid = (lo + hi) / 2
    (lo, hi) = (mid, hi) if run("Base", wacc=mid)["per_sh"] > PRICE else (lo, mid)
out["wacc_base_eq_price"] = mid; print(f"WACC where Base = price: {mid:.2%}")

sens = {}
for w in [0.08, 0.085, 0.09, 0.095, 0.10, 0.105, 0.11]:
    sens[f"{w:.1%}"] = [round(run("Base", wacc=w, g=g)["per_sh"], 0) for g in [0.0, 0.01, 0.02, 0.025, 0.03]]
out["sens"] = sens
print("Sens (g 0/1/2/2.5/3%)"); [print(k, v) for k, v in sens.items()]

# 80% consensus haircut on years 1-2
c = SCEN["Consensus"][0]
out["cons80"] = run("Consensus", ebitda=[c[0] * .8, c[1] * .8] + c[2:])["per_sh"]
print(f"Consensus @80% yrs1-2: ${out['cons80']:.1f}")

# PIE: flat EBITDA from 2028 that justifies the price (2027 base)
for w in [WACC, WACC - 0.01, WACC + 0.015]:
    lo, hi = 3000, 15000
    for _ in range(60):
        mid = (lo + hi) / 2
        v = run("Base", wacc=w, ebitda=[8100] + [mid] * 4)["per_sh"]
        (lo, hi) = (lo, mid) if v > PRICE else (mid, hi)
    out[f"pie_{w:.3f}"] = mid; print(f"PIE @ WACC {w:.2%}: flat EBITDA 2028-31 = {mid:,.0f}")
lo, hi = 3000, 15000
for _ in range(60):
    mid = (lo + hi) / 2
    v = run("Base", g=0.0, ebitda=[8100] + [mid] * 4)["per_sh"]
    (lo, hi) = (lo, mid) if v > PRICE else (mid, hi)
out["pie_g0"] = mid; print(f"PIE @ g=0: flat EBITDA = {mid:,.0f}")

# SOTP on FY2027 base segment EBITDA
SEG = {"Retail": (1650, 6, 7, 8), "Texas generation": (2450, 8, 10, 12),
       "East generation (PJM nuclear + gas, incl. Cogentrix)": (3750, 9.5, 12, 14),
       "West": (250, 6, 7, 8), "Corporate & other": (-100, 10, 10, 10)}
sotp = {}
for k, lab in enumerate(["Low", "Mid", "High"]):
    ev = sum(e * m[k] for e, *m in SEG.values())
    sotp[lab] = dict(ev=ev, per_sh=(ev - CLAIMS) / SH)
out["sotp"] = sotp; out["seg"] = SEG
print("SOTP:", {k: round(v["per_sh"], 1) for k, v in sotp.items()})

# Through-cycle (Ongoing Ops Adj. EBITDA, company releases / 10-K)
HIST = {2022: 3119, 2023: 4140, 2024: 5643, 2025: 5912, "2026E": 7300}
ev_now = MCAP + CLAIMS
avg = sum(v for k, v in HIST.items() if k != "2026E") / 4
out["through"] = dict(hist=HIST, avg_22_25=avg, ev_avg=ev_now / avg, ev_26=ev_now / 7300, ev_27=ev_now / 8100,
                      mid_needed_at_8x=ev_now / 8, mid_needed_at_9x=ev_now / 9)
print(f"EV {ev_now:,.0f}: EV/avg22-25 {ev_now/avg:.1f}x, EV/26E {ev_now/7300:.1f}x, EV/27E {ev_now/8100:.1f}x")

# Multiples ladder ($/share)
EPS27 = 10.33
lad = {}
for lab, pe in [("NRG fwd P/E 7.9x", 7.9), ("TLN fwd P/E 11.8x", 11.8), ("Own fwd P/E today 12.6x", 12.6),
                ("CEG fwd P/E 18.3x", 18.3)]:
    lad[lab] = pe * EPS27
for lab, m in [("EV/EBITDA 7x (own 2022-23 trough 6.6-7.7x)", 7.0), ("EV/EBITDA 9.7x (own 2022-25 avg)", 9.7),
               ("EV/EBITDA 12x (2024-25 own)", 12.0), ("EV/EBITDA 14x (CEG)", 14.0)]:
    lad[lab] = (m * 8100 - CLAIMS) / SH
out["ladder"] = lad
for k, v in lad.items(): print(f"   {k}: ${v:.0f}")
for s in ["Bear", "Base", "Bull"]:
    out[s]["impl_pe27"] = out[s]["per_sh"] / EPS27
    print(f"   {s}: implied P/E27 {out[s]['impl_pe27']:.1f}x, EV/EBITDA27 {out[s]['ev_ebitda27']:.1f}x")
json.dump(out, open(__file__.replace(".py", ".json"), "w"), default=float, indent=1)
