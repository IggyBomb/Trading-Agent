"""Danieli (DAN.MI / DANR.MI) — DCF, SOTP, through-cycle, ladder. Inputs: FY2025/26 annual report + guidance."""
import json

P_ORD, P_SAV = 51.90, 36.30            # 4 Nov 2026 close (yfinance)
N_ORD, N_SAV = 36.368, 35.205           # M shares outstanding ex-treasury (AR: 4.512M ord + 5.220M sav treasury)
N_TOT = N_ORD + N_SAV
RATIO = P_SAV / P_ORD                   # savings / ordinary price ratio
N_ORD_EQ = N_ORD + RATIO * N_SAV        # ordinary-equivalent shares at today's discount
MCAP = P_ORD * N_ORD + P_SAV * N_SAV

NFP_ADJ = 1019.7       # adjusted net cash (net of operating customer advances)
NFP_REP = 2667.8       # reported net cash
PENSION, MINORITY = 25.0, 1.3
TAX = 0.28
RF, ERP, BETA = 4.61, 5.0, 1.18
KE = (RF + BETA * ERP) / 100
WACC, G = KE, 0.02     # net-cash balance sheet -> WACC = Ke

SCEN = {
 "Bear": ([3900, 3500, 3250, 3350, 3450], [0.100, 0.085, 0.080, 0.085, 0.090]),
 "Base": ([4050, 4250, 4380, 4510, 4600], [0.109, 0.112, 0.113, 0.113, 0.113]),
 "Consensus": ([4125, 4379, 4510, 4645, 4740], [0.115, 0.117, 0.117, 0.117, 0.117]),
 "Bull": ([4200, 4550, 4900, 5200, 5400], [0.112, 0.120, 0.125, 0.128, 0.130]),
}
CAPEX = [200, 200, 180, 160, 150]
DA_PCT, NWC_PCT, REV0 = 0.037, 0.08, 3833.5


def run(name, wacc=WACC, g=G, cash=NFP_ADJ):
    revs, ms = SCEN[name]
    pv, prev, rows = 0.0, REV0, []
    for i, (r, m, cx) in enumerate(zip(revs, ms, CAPEX), 1):
        ebitda = r * m; da = r * DA_PCT; ebit = ebitda - da
        fcff = ebit * (1 - TAX) + da - cx - (r - prev) * NWC_PCT
        pv += fcff / (1 + wacc) ** i; prev = r
        rows.append(dict(year=f"FY{26+i}", rev=r, ebitda=ebitda, margin=m, ebit=ebit, fcff=fcff))
    r = revs[-1]; m = ms[-1]; da = r * DA_PCT
    fcf_t = (r * m - da) * (1 - TAX) + da - da * 1.05 - r * g * NWC_PCT
    tv = fcf_t * (1 + g) / (wacc - g); pv_tv = tv / (1 + wacc) ** 5
    ev = pv + pv_tv
    eq = ev + cash - PENSION - MINORITY
    return dict(rows=rows, ev=ev, pv_tv_share=pv_tv / ev, equity=eq,
                per_econ=eq / N_TOT, per_ord=eq / N_ORD_EQ, per_sav=eq / N_ORD_EQ * RATIO)


out = {"inputs": dict(MCAP=MCAP, RATIO=RATIO, N_ORD_EQ=N_ORD_EQ, KE=KE, WACC=WACC, G=G,
                      EV_ADJ=MCAP - NFP_ADJ + PENSION + MINORITY, EV_REP=MCAP - NFP_REP + PENSION + MINORITY)}
print(f"Mcap €{MCAP:,.0f}M | sav/ord {RATIO:.3f} | ord-eq shares {N_ORD_EQ:.2f}M | Ke=WACC {KE:.2%} | EV(adj) {out['inputs']['EV_ADJ']:,.0f} | EV(rep) {out['inputs']['EV_REP']:,.0f}")
for s in SCEN:
    r = run(s); out[s] = r
    print(f"\n== {s}: EV {r['ev']:,.0f} (TV {r['pv_tv_share']:.0%}) equity {r['equity']:,.0f} | ord €{r['per_ord']:.1f} ({r['per_ord']/P_ORD-1:+.0%}) sav €{r['per_sav']:.1f}")
    for x in r["rows"]:
        print(f"   {x['year']} rev {x['rev']:,.0f} EBITDA {x['ebitda']:,.0f} ({x['margin']:.1%}) EBIT {x['ebit']:,.0f} FCFF {x['fcff']:,.0f}")

# stress, gross-cash variant
out["stress"] = {s: run(s, wacc=WACC + 0.03)["per_ord"] for s in ["Bear", "Base", "Bull"]}
out["gross_cash"] = {s: run(s, cash=NFP_REP)["per_ord"] for s in ["Bear", "Base", "Bull"]}
print("\nBear/Base/Bull at WACC+3:", {k: round(v, 1) for k, v in out["stress"].items()})
print("Crediting full reported net cash:", {k: round(v, 1) for k, v in out["gross_cash"].items()})

# WACC at which Bear = price
lo, hi = 0.04, 0.30
for _ in range(60):
    mid = (lo + hi) / 2
    (lo, hi) = (mid, hi) if run("Bear", wacc=mid)["per_ord"] > P_ORD else (lo, mid)
out["wacc_bear_eq_price"] = mid
print(f"WACC where Bear = price: {mid:.1%}")

# sensitivity base
sens = {}
for w in [0.085, 0.095, 0.105, 0.115, 0.125]:
    sens[w] = [round(run("Base", wacc=w, g=g)["per_ord"], 1) for g in [0.01, 0.015, 0.02, 0.025, 0.03]]
out["sens"] = {f"{k:.1%}": v for k, v in sens.items()}
print("Sensitivity (ord €): g 1/1.5/2/2.5/3%"); [print(k, v) for k, v in out["sens"].items()]

# 80% consensus haircut row: scale consensus EBITDA by 0.8 on years 1-2
SCEN["Cons80"] = (SCEN["Consensus"][0], [SCEN["Consensus"][1][0] * .8, SCEN["Consensus"][1][1] * .8] + SCEN["Consensus"][1][2:])
out["cons80"] = run("Cons80")["per_ord"]; print(f"Consensus@80% (yrs1-2): €{out['cons80']:.1f}")

# PIE: flat terminal margin needed (base growth) to justify price
lo, hi = 0.03, 0.25
for _ in range(60):
    mid = (lo + hi) / 2
    SCEN["PIE"] = (SCEN["Base"][0], [mid] * 5)
    (lo, hi) = (lo, mid) if run("PIE")["per_ord"] > P_ORD else (mid, hi)
out["pie_margin"] = mid; print(f"PIE: price implies flat EBITDA margin {mid:.1%} (base growth, WACC {WACC:.1%})")
for w in [0.085, 0.125]:
    lo, hi = 0.0, 0.25
    for _ in range(60):
        mid = (lo + hi) / 2; SCEN["PIE"] = (SCEN["Base"][0], [mid] * 5)
        (lo, hi) = (lo, mid) if run("PIE", wacc=w)["per_ord"] > P_ORD else (mid, hi)
    out[f"pie_{w}"] = mid; print(f"   at WACC {w:.1%}: {mid:.1%}")

# SOTP (FY27 guidance midpoints)
pm_ebitda, sm_ebitda = 350, 95
pm_cash, sm_debt = 1325, 275
sotp = {}
for lab, mpm, msm in [("Low", 6, 4.5), ("Mid", 7, 5), ("High", 9, 6)]:
    eq = pm_ebitda * mpm + pm_cash + sm_ebitda * msm - sm_debt - PENSION - MINORITY
    sotp[lab] = dict(mult_pm=mpm, mult_sm=msm, equity=eq, per_ord=eq / N_ORD_EQ)
out["sotp"] = sotp; print("SOTP:", {k: round(v['per_ord'], 1) for k, v in sotp.items()})

# Through-cycle
mid_ni = (218.7 + 243.6 + 240.8 + 220.1 + 230.4) / 5
mid_ebitda = (319 + 383.2 + 391.2 + 437.8 + 438.9) / 5
cash_income_at = NFP_ADJ * 0.03 * (1 - TAX)
pe_mid = MCAP / mid_ni; pe_mid_ex = (MCAP - NFP_ADJ) / (mid_ni - cash_income_at)
out["through"] = dict(mid_ni=mid_ni, mid_ebitda=mid_ebitda, pe_mid=pe_mid, pe_mid_ex=pe_mid_ex,
                      ev_mid_ebitda=out["inputs"]["EV_ADJ"] / mid_ebitda)
print(f"Through-cycle: mid NI {mid_ni:.1f} -> P/E {pe_mid:.1f}x, ex-cash {pe_mid_ex:.1f}x; EV/mid EBITDA {out['through']['ev_mid_ebitda']:.1f}x")

# Multiples ladder (value per ordinary share)
lad = {}
eps27 = 3.98 * N_TOT  # consensus NI FY27 (€M)
for lab, pe in [("Own 5y avg P/E (9.1x)", 9.1), ("Andritz fwd P/E 13.8x", 13.8), ("Sector median fwd P/E ~12x", 12.0)]:
    lad[lab] = pe * eps27 / N_ORD_EQ
for lab, m in [("EV/EBITDA 5x (own history, adj. cash)", 5.0), ("EV/EBITDA 7x", 7.0), ("Andritz EV/EBITDA 9.1x", 9.1)]:
    lad[lab] = (m * 440 + NFP_ADJ - PENSION - MINORITY) / N_ORD_EQ
out["ladder"] = lad
for k, v in lad.items(): print(f"   {k}: €{v:.1f}")
# implied multiples of DCF scenarios
for s in ["Bear", "Base", "Bull"]:
    eq = out[s]["equity"]; ev = out[s]["ev"]
    out[s]["impl_pe27"] = eq / eps27; out[s]["impl_ev_ebitda27"] = ev / 440
    print(f"   {s}: implied P/E FY27 {eq/eps27:.1f}x, EV/EBITDA FY27 {ev/440:.1f}x")
json.dump(out, open(__file__.replace(".py", ".json"), "w"), default=float, indent=1)
