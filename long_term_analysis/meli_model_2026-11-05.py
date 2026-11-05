"""MercadoLibre (MELI) — equity DCF (FCFE, bank-style: fintech credit book needs equity), PIE, ladder, SOTP.
Inputs: 10-K FY2025 (filed 25 Feb 2026), 10-Q Q3-2026 (filed 5 Nov 2026), Q3-26 release (4 Nov 2026),
yfinance 5 Nov 2026 intraday (~10:20 ET). $ millions unless stated."""
import json

PRICE = 1505.62
SH = 50.697                          # diluted weighted shares Q3-26 (M)
MCAP = PRICE * SH
NET_DEBT_CO = 8028                   # company-defined net debt 30 Sep 2026 (incl. fintech funding + leases)
CONTING_RP = 768                     # reasonably-possible contingencies (not accrued) — tail risk, not deducted

RF, ERP, BETA = 4.95, 5.0, 1.39      # FRED DGS10 (5 Nov 2026 macro run); yfinance beta inside 0.7–1.4
KE = (RF + BETA * ERP) / 100
CRP = 0.025                          # LatAm country-risk override shown alongside (not the house rule)

REV26, NI26 = 41857.5, 38.17403 * SH  # FY26 consensus
YEARS = list(range(2027, 2037))
SCEN = {
    #            revenue growth path (FY27..FY36)                     net margin path                                   k=ΔEq/ΔRev  g_term
    "Bear": ([0.205, 0.165, 0.14, 0.12, 0.105, 0.09, 0.08, 0.07, 0.06, 0.05],
             [0.040, 0.045, 0.050, 0.055, 0.060, 0.062, 0.064, 0.065, 0.065, 0.065], 0.24, 0.030),
    "Base": ([0.292, 0.24, 0.20, 0.17, 0.15, 0.13, 0.11, 0.095, 0.08, 0.07],
             [0.0517, 0.063, 0.073, 0.082, 0.090, 0.095, 0.100, 0.100, 0.100, 0.100], 0.20, 0.035),
    "Bull": ([0.33, 0.28, 0.24, 0.20, 0.17, 0.15, 0.13, 0.11, 0.095, 0.08],
             [0.056, 0.070, 0.083, 0.095, 0.105, 0.112, 0.118, 0.122, 0.125, 0.125], 0.17, 0.040),
}


def run(name, ke=None, growth=None, margin=None, k=None, g=None, ni_override=None):
    ke = KE if ke is None else ke
    gr, mg, k0, g0 = SCEN[name]
    gr = growth or gr; mg = margin or mg; k = k0 if k is None else k; g = g0 if g is None else g
    rev, pv, rows = REV26, 0.0, []
    for i, (y, gi, mi) in enumerate(zip(YEARS, gr, mg), 1):
        new = rev * (1 + gi); ni = new * mi
        if ni_override and y in ni_override: ni = ni_override[y]
        fcfe = ni - k * (new - rev)
        pv += fcfe / (1 + ke) ** i
        rows.append(dict(year=y, rev=new, margin=ni / new, ni=ni, eps=ni / SH, fcfe=fcfe)); rev = new
    ni_t = rev * (1 + g) * mg[-1]
    tv = (ni_t - k * g * rev) / (ke - g)
    pv_tv = tv / (1 + ke) ** len(YEARS)
    eq = pv + pv_tv
    return dict(rows=rows, equity=eq, per_sh=eq / SH, tv_share=pv_tv / eq, tv_pe=tv / rows[-1]["ni"],
                pe27=eq / SH / rows[0]["eps"], roe_term=mg[-1] / k * (g / g) if k else None)


out = {"inputs": dict(PRICE=PRICE, SH=SH, MCAP=MCAP, NET_DEBT_CO=NET_DEBT_CO, KE=KE, KE_CRP=KE + CRP, RF=RF, BETA=BETA)}
print(f"Mcap {MCAP:,.0f} | Ke {KE:.2%} (with CRP {KE+CRP:.2%})")
for s in SCEN:
    r = run(s); out[s] = r
    print(f"\n== {s}: equity {r['equity']:,.0f} -> ${r['per_sh']:,.0f} ({r['per_sh']/PRICE-1:+.0%}) TV {r['tv_share']:.0%} TV P/E {r['tv_pe']:.1f}x, implied P/E27 {r['pe27']:.1f}x")
    for x in r["rows"][:3] + r["rows"][-1:]:
        print(f"   {x['year']} rev {x['rev']:,.0f} m {x['margin']:.1%} NI {x['ni']:,.0f} EPS {x['eps']:.1f} FCFE {x['fcfe']:,.0f}")

out["crp"] = {s: run(s, ke=KE + CRP)["per_sh"] for s in SCEN}
out["stress"] = {s: run(s, ke=KE + 0.03)["per_sh"] for s in SCEN}
print("Ke+CRP:", {k: round(v) for k, v in out["crp"].items()}, "| Ke+3:", {k: round(v) for k, v in out["stress"].items()})


def solve(fn, lo, hi, up=True):
    for _ in range(80):
        mid = (lo + hi) / 2
        (lo, hi) = (mid, hi) if (fn(mid) > PRICE) == up else (lo, mid)
    return mid


out["ke_bear_eq_price"] = solve(lambda w: run("Bear", ke=w)["per_sh"], 0.05, 0.30)
out["ke_base_eq_price"] = solve(lambda w: run("Base", ke=w)["per_sh"], 0.05, 0.30)
print(f"Ke where Bear=price {out['ke_bear_eq_price']:.2%}; Base=price {out['ke_base_eq_price']:.2%}")

# consensus 80% haircut on FY27 (and FY28 Base) net income
b = run("Base")["rows"]
out["cons80"] = run("Base", ni_override={2027: b[0]["ni"] * .8, 2028: b[1]["ni"] * .8})["per_sh"]
print(f"Base with FY27-28 NI at 80%: ${out['cons80']:,.0f}")

# PIE: steady-state net margin (reached FY31, Base growth & k) that justifies the price
base_g = SCEN["Base"][0]
pie = {}
for lab, ke in [("house", KE), ("house-1", KE - 0.01), ("CRP", KE + CRP)]:
    def f(m):
        path = [0.0517, 0.0517 + (m - 0.0517) * .25, 0.0517 + (m - 0.0517) * .5, 0.0517 + (m - 0.0517) * .75] + [m] * 6
        return run("Base", ke=ke, margin=path)["per_sh"]
    pie[lab] = solve(f, 0.02, 0.40, up=False) if False else None
    lo, hi = 0.02, 0.40
    for _ in range(80):
        mid = (lo + hi) / 2
        (lo, hi) = (lo, mid) if f(mid) > PRICE else (mid, hi)
    pie[lab] = (ke, mid)
out["pie"] = pie
print("PIE steady net margin:", {k: (f"{v[0]:.2%}", f"{v[1]:.2%}") for k, v in pie.items()})
# PIE growth: margin path Base, scale growth path
def fg(mult):
    return run("Base", growth=[x * mult for x in base_g])["per_sh"]
lo, hi = 0.1, 3.0
for _ in range(80):
    mid = (lo + hi) / 2
    (lo, hi) = (lo, mid) if fg(mid) > PRICE else (mid, hi)
out["pie_growth_mult"] = mid; print(f"PIE growth multiplier on Base path: {mid:.2f}x")

sens = {}
for ke in [0.10, 0.11, 0.119, 0.13, 0.144]:
    sens[f"{ke:.1%}"] = [round(run("Base", ke=ke, margin=[0.0517, 0.063, 0.073, 0.082] + [tm] * 6)["per_sh"]) for tm in [0.07, 0.085, 0.10, 0.115, 0.13]]
out["sens"] = sens
print("Sens Ke x terminal margin 7/8.5/10/11.5/13%"); [print(k, v) for k, v in sens.items()]

EPS27 = 55.17; EPS_TTM = 36.77
REV27 = 54066; EBITDA27 = REV27 * 0.075 + 1300   # our estimate: 7.5% op margin + D&A ~1.3bn
lad = {
    "PDD fwd P/E 6.7×": 6.7 * EPS27, "NU fwd P/E 10.3×": 10.3 * EPS27, "Peer median fwd P/E 14.9× (SE)": 14.9 * EPS27,
    "AMZN fwd P/E 23.9×": 23.9 * EPS27, "Own fwd P/E today 27.0×": 27.0 * EPS27,
    "Own avg trailing P/E FY23–25 58.9× on TTM EPS": 58.9 * EPS_TTM,
    "SE EV/Sales 1.67× on FY27E": (1.67 * REV27 - NET_DEBT_CO) / SH,
    "EV/EBITDA 17× (SE/AMZN) on FY27E": (17 * EBITDA27 - NET_DEBT_CO) / SH,
}
out["ladder"] = lad
for k_, v in lad.items(): print(f"   {k_}: ${v:,.0f}")

# SOTP on FY27E revenue (55% commerce / 45% fintech, FY25 split 56/44)
SEG = {"Commerce": (REV27 * .55, 0.83, 1.67, 2.50), "Fintech": (REV27 * .45, 0.78, 2.10, 4.00)}
sotp = {}
for j, lab in enumerate(["Low", "Mid", "High"]):
    ev = sum(r * m[j] for r, *m in SEG.values())
    sotp[lab] = dict(ev=ev, per_sh=(ev - NET_DEBT_CO) / SH)
out["sotp"] = sotp; out["seg"] = SEG
print("SOTP:", {k_: round(v["per_sh"]) for k_, v in sotp.items()})
out["ebitda27"] = EBITDA27
json.dump(out, open(__file__.replace(".py", ".json"), "w"), default=float, indent=1)
