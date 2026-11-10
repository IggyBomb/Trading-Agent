"""Cummins (CMI) — DCF (FCFF), SOTP, through-cycle, ladder, PIE, 5-yr ratios.
Inputs: 10-K FY2025 (filed 10 Feb 2026), 10-Q Q3-2026 (filed 5 Nov 2026), Q3-26 / Q4-25 releases (8-K ex99),
XBRL companyfacts, yfinance 10 Nov 2026 (intraday 454.12). $ millions unless stated."""
import json

PRICE = 454.12                       # 10 Nov 2026, yfinance intraday (prev close 466.47)
SH = 138.1                           # Q3-26 diluted weighted shares
MCAP = PRICE * SH
DEBT = 7519                          # 10-Q: carrying value of total debt (loans payable + CP + current + LTD)
CASH = 4185                          # cash + marketable securities, 30 Sep 2026
NCI = 1015                           # noncontrolling interests, book
NET_DEBT = DEBT - CASH
# Debt-like items: US/UK pensions in net surplus (10-K: +489 US, +70 UK net recognised) -> not deducted.
# Warranty (2,778 incl. deferred) is operating working capital -> already in FCFF, not deducted.
# Electrolyzer stop-use (Sep 2026), Brazil tax litigation, derivative suit -> unquantified tail risk, not deducted.
CLAIMS = NET_DEBT + NCI

RF, ERP, BETA = 4.89, 5.0, 1.235     # ^TNX 5 Nov 2026 (pipeline macro_regime.json); yfinance beta (inside 0.7-1.4)
KE = (RF + BETA * ERP) / 100
KD, TAX = 0.053, 0.23                # KD: fair value 6,836 vs carrying 7,519 -> ~5.3% yield; 23% guided ETR
V = MCAP + DEBT + NCI
WACC = MCAP / V * KE + DEBT / V * KD * (1 - TAX) + NCI / V * KE

REV26, EBITDA26 = 37040, 37040 * 0.182          # guide: ~+10% on 33,670, ~18.2% EBITDA (ex Q1 charge)
YEARS = [2027, 2028, 2029, 2030, 2031]
# (revenue path, EBITDA margin path, terminal EBITDA margin, g)
SCEN = {
 # Bear = named risks: (1) data-centre genset cycle rolls over 2028 (Power Systems 25% -> ~18% EBITDA, volume -20%)
 #                     (2) NA truck air pocket after EPA-2027 + pickup (Stellantis Ram) weakness persists
 "Bear":      ([37500, 35300, 35600, 36700, 37800], [0.170, 0.155, 0.150, 0.152, 0.152], 0.150, 0.020),
 "Base":      ([40000, 41800, 42600, 44300, 46100], [0.188, 0.185, 0.178, 0.180, 0.180], 0.170, 0.025),
 "Consensus": ([40740, 42800, 44100, 45900, 47700], [0.190, 0.188, 0.183, 0.183, 0.183], 0.172, 0.025),
 "Bull":      ([40740, 44400, 47500, 50400, 53400], [0.195, 0.200, 0.200, 0.205, 0.205], 0.190, 0.030),
}
DA_PCT, CAPEX_PCT, NWC_PCT = 0.031, 0.034, 0.12  # D&A 2025 1,105 (3.3%); capex 1,235 (3.7%) incl. capacity build; NWC/ΔRev
RETAINED_EQ = 150                                # equity income not received as dividends (non-cash part of EBITDA)
RONIC = 0.15


def run(name, wacc=None, g=None, rev=None, mgn=None, tmgn=None):
    wacc = WACC if wacc is None else wacc
    r0, m0, tm0, g0 = SCEN[name]
    rev = r0 if rev is None else rev
    mgn = m0 if mgn is None else mgn
    tm = tm0 if tmgn is None else tmgn
    g = g0 if g is None else g
    pv, rows, prev = 0.0, [], REV26
    for i, (r, m) in enumerate(zip(rev, mgn), 1):
        e = r * m
        da = r * DA_PCT
        tax = (e - da) * TAX
        f = e - RETAINED_EQ - tax - r * CAPEX_PCT - (r - prev) * NWC_PCT
        pv += f / (1 + wacc) ** i
        rows.append(dict(year=YEARS[i - 1], rev=r, ebitda=e, margin=m, fcff=f))
        prev = r
    r_t = rev[-1] * (1 + g)
    e_t = r_t * tm
    nopat = (e_t - r_t * DA_PCT) * (1 - TAX)
    f_t = nopat - g / RONIC * nopat
    tv = f_t / (wacc - g)
    pv_tv = tv / (1 + wacc) ** 5
    ev = pv + pv_tv
    eq = ev - CLAIMS
    return dict(rows=rows, ev=ev, tv_share=pv_tv / ev, per_sh=eq / SH,
                exit_mult=tv / (rev[-1] * mgn[-1]), ev_ebitda27=ev / (rev[0] * mgn[0]),
                pe27=(eq / SH) / eps_from(rev[0], mgn[0]))


def eps_from(rev, m, interest=320, sh=137.5, nci=120):
    pre = rev * m - rev * DA_PCT - interest
    return (pre * (1 - TAX) - nci) / sh


def solve(fn, lo, hi, target=PRICE, increasing=True):
    for _ in range(80):
        mid = (lo + hi) / 2
        v = fn(mid)
        if (v > target) == increasing:
            hi = mid
        else:
            lo = mid
    return mid


out = {"inputs": dict(PRICE=PRICE, SH=SH, MCAP=MCAP, DEBT=DEBT, CASH=CASH, NCI=NCI, NET_DEBT=NET_DEBT,
                      CLAIMS=CLAIMS, KE=KE, WACC=WACC, EV_MKT=MCAP + CLAIMS,
                      EV_W=MCAP / V, D_W=DEBT / V, NCI_W=NCI / V)}
print(f"Mcap {MCAP:,.0f} | net debt {NET_DEBT:,.0f} | NCI {NCI:,} | EV {MCAP+CLAIMS:,.0f}")
print(f"Ke {KE:.2%} | WACC {WACC:.2%} (E {MCAP/V:.1%} D {DEBT/V:.1%} NCI {NCI/V:.1%})")
for s in SCEN:
    r = run(s); out[s] = r
    print(f"\n== {s}: EV {r['ev']:,.0f} (TV {r['tv_share']:.0%}, exit {r['exit_mult']:.1f}x) -> ${r['per_sh']:.0f} "
          f"({r['per_sh']/PRICE-1:+.0%}) | EV/EBITDA27 {r['ev_ebitda27']:.1f}x | P/E27 {r['pe27']:.1f}x")
    for x in r["rows"]:
        print(f"   {x['year']} rev {x['rev']:,} EBITDA {x['ebitda']:,.0f} ({x['margin']:.1%}) FCFF {x['fcff']:,.0f}")

out["stress"] = {s: run(s, wacc=WACC + 0.03)["per_sh"] for s in ["Bear", "Base", "Bull"]}
print("\nWACC+3:", {k: round(v) for k, v in out["stress"].items()})
for s in ["Bear", "Base", "Bull"]:
    out[f"wacc_{s}_eq_price"] = solve(lambda w: -run(s, wacc=w)["per_sh"], 0.05, 0.25, target=-PRICE)
    print(f"WACC where {s} = price: {out[f'wacc_{s}_eq_price']:.2%}")

sens = {}
for w in [0.085, 0.09, 0.095, 0.10, 0.105, 0.11, 0.115]:
    sens[f"{w:.1%}"] = [round(run("Base", wacc=w, g=g)["per_sh"]) for g in [0.015, 0.02, 0.025, 0.03, 0.035]]
out["sens"] = sens
print("Sens WACC x g (1.5/2/2.5/3/3.5%)"); [print(k, v) for k, v in sens.items()]
# Revenue growth x margin grid (Base): scale revenue path, shift margins
grid = {}
for rs in [0.90, 0.95, 1.00, 1.05]:
    grid[f"rev x{rs:.2f}"] = [round(run("Base", rev=[x * rs for x in SCEN['Base'][0]],
                                        mgn=[m + d for m in SCEN['Base'][1]], tmgn=SCEN['Base'][2] + d)["per_sh"])
                              for d in [-0.02, -0.01, 0, 0.01]]
out["grid"] = grid
print("Grid rev scale x margin shift (-2/-1/0/+1 pt)"); [print(k, v) for k, v in grid.items()]

# 80% consensus haircut: EBITDA 2027-28 at 80% of consensus case
c = SCEN["Consensus"]
out["cons80"] = run("Consensus", mgn=[c[1][0] * .8, c[1][1] * .8] + c[1][2:])["per_sh"]
print(f"Consensus @80% EBITDA yrs1-2: ${out['cons80']:.0f}")

# PIE 1: terminal EBITDA margin implied by price, holding Base revenue + explicit margins
for w in [WACC - 0.01, WACC, WACC + 0.015]:
    k = f"pie_tm_{w:.3f}"
    out[k] = solve(lambda tm: run("Base", wacc=w, tmgn=tm)["per_sh"], 0.05, 0.30)
    print(f"PIE @ WACC {w:.2%}: terminal EBITDA margin = {out[k]:.1%}")
# PIE 2: flat revenue growth 2028-31 implied (margins Base)
def flat_growth(gr, w=WACC):
    rv = [40000 * (1 + gr) ** i for i in range(5)]
    return run("Base", wacc=w, rev=rv)["per_sh"]
out["pie_growth"] = solve(flat_growth, -0.10, 0.20)
print(f"PIE: revenue CAGR 2027-31 implied at Base margins = {out['pie_growth']:.1%}")

# Through-cycle (Lynch Cyclical): consensus 2026-27, Base 2028-29 EPS, discount, residual -> required mid-cycle EPS
EPS_PATH = {2026: 27.81, 2027: 33.51, 2028: eps_from(41800, 0.185), 2029: eps_from(42600, 0.178)}
FCF_CONV = 0.85                       # FCF / NI: 2021-25 cum FCF 7,986 vs NI 11,806 = 68%; ex-2024 settlement ~85%
pv_eps = sum(e / (1 + WACC) ** (i + 0.5) for i, e in enumerate(EPS_PATH.values()))  # 2026 Q4 only ~ partial: use full yrs from 2027
pv_eps = sum(e / (1 + WACC) ** i for i, (y, e) in enumerate(EPS_PATH.items()) if y >= 2027 for _ in [0]) if False else \
         sum(EPS_PATH[y] / (1 + WACC) ** (y - 2026) for y in [2027, 2028, 2029])
pv_fcf = pv_eps * FCF_CONV
netcash_sh = -(CLAIMS) / SH
res_eps = PRICE - pv_eps - netcash_sh
res_fcf = PRICE - pv_fcf - netcash_sh
fv_eps = res_eps * (1 + WACC) ** 3
fv_fcf = res_fcf * (1 + WACC) ** 3
out["tc"] = dict(eps_path=EPS_PATH, pv_eps=pv_eps, pv_fcf=pv_fcf, netcash_sh=netcash_sh, res_eps=res_eps,
                 res_fcf=res_fcf, req_eps=fv_eps / 12, req_eps_fcf=fv_fcf / 12 / FCF_CONV)
print("Through-cycle:", {k: (round(v, 2) if isinstance(v, float) else v) for k, v in out["tc"].items()})

# SOTP on TTM segment EBITDA (Q4-25 + 9M-26), named peer EV/EBITDA (yfinance 10 Nov 2026, TTM)
SEG = {  # TTM EBITDA, low / mid / high multiple
 "Power Systems (gensets, data-centre, mining/rail/marine)": (2129, 12, 15, 18),   # CAT 18.4x, GNRC 19.6x, RR.L 21.1x; haircut for cycle
 "Distribution (dealer network, ~1/3 power-gen)":           (1851, 10, 12, 13.5), # FTT.TO 12.8x, TIH.TO 13.7x, RUSHA 10.2x
 "Engine (on/off-highway)":                                  (1350, 7, 9, 10.5),   # PCAR 17.0x(captive fin.), ALSN 10.4x, DTG 11.8x, BWA 6.0x
 "Components (aftertreatment, axles/brakes, turbo, fuel)":   (1453, 6, 8, 10),     # BWA 6.0x, ALSN 10.4x
 "Accelera (ex Q1 charge & Q4-25 electrolyzer charges)":     (-776 + 199 + 218, 8, 8, 8),  # losses capitalised as a cost
 "Eliminations / corporate":                                 (-127, 9, 9, 9),
}
sotp = {}
for k, lab in enumerate(["Low", "Mid", "High"]):
    ev = sum(e * m[k] for e, *m in SEG.values())
    sotp[lab] = dict(ev=ev, per_sh=(ev - CLAIMS) / SH)
out["sotp"] = sotp; out["seg"] = SEG
print("SOTP:", {k: round(v["per_sh"]) for k, v in sotp.items()})

# Multiples ladder anchors (per share)
EBITDA_TTM = 5880 + 199          # reported TTM EBITDA + Q1-26 fuel-cell charge
EBITDA_26 = EBITDA26
EPS27 = 33.51
lad = {}
# peers (yfinance 10 Nov 2026): fwd P/E PCAR 15.5, ALSN 10.8, BWA 8.6, DTG 8.9, VOLV 12.9, CAT 18.0 -> median 11.9
# TTM EV/EBITDA PCAR 17.0, ALSN 10.4, BWA 6.0, DTG 11.8, VOLV 14.8, CAT 18.4 -> median 13.3
lad["Peer median fwd P/E 11.9x x FY27 EPS"] = 11.86 * EPS27
lad["Peer median TTM EV/EBITDA 13.3x x TTM adj. EBITDA"] = (13.29 * EBITDA_TTM - CLAIMS) / SH
lad["Own 5-yr median trailing P/E 16.0x x FY26E EPS"] = 16.0 * 27.81
lad["Own 5-yr avg EV/EBITDA 11.1x x TTM adj. EBITDA"] = (11.1 * EBITDA_TTM - CLAIMS) / SH
lad["Own 5-yr avg EV/EBITDA 11.1x x 2026E EBITDA"] = (11.1 * EBITDA_26 - CLAIMS) / SH
out["ladder"] = lad

# Koller Method 2 cross-check: exit EV/EBITDA on 2031 EBITDA instead of value-driver TV
def exit_val(name, mult, wacc=None):
    wacc = WACC if wacc is None else wacc
    r = run(name, wacc=wacc)
    pv = sum(x["fcff"] / (1 + wacc) ** i for i, x in enumerate(r["rows"], 1))
    tv = r["rows"][-1]["ebitda"] * mult / (1 + wacc) ** 5
    return (pv + tv - CLAIMS) / SH
out["exit_cc"] = {s: {m: exit_val(s, m) for m in [8, 10, 12]} for s in ["Bear", "Base", "Bull"]}
print("Exit-multiple cross-check:", {s: {m: round(v) for m, v in d.items()} for s, d in out["exit_cc"].items()})
out["ycp"] = {y: PRICE / e for y, e in EPS_PATH.items()}
print("Years of consensus P/E:", {y: round(v, 1) for y, v in out["ycp"].items()})
out["tc"]["req_eps_15x"] = out["tc"]["req_eps"] * 12 / 15
print("Ladder:", {k: round(v) for k, v in lad.items()})

# 5-year ratio table
FY = {  # rev, gp, ebitda(approx pre-tax+int+D&A), NI attrib, equity(parent), debt(ex loans payable pre-2025), cash+ms, ocf, capex, price, shares, opinc
 2021: (24021, 5695, 2751 + 111 + 662, 2131, 8146, 3579 + 59 + 313, 2592 + 595, 2256, 734, 218.14, 145.9, 2706),
 2022: (28074, 6719, 2819 + 199 + 784, 2151, 8975, 4498 + 573 + 2574, 2020 + 472, 1962, 916, 242.29, 142.3, 2929),
 2023: (34065, 8249, 1626 + 375 + 1024, 735, 8850, 4802 + 118 + 1496, 2179 + 562, 3966, 1213, 239.57, 142.7, 1761),
 2024: (34102, 8439, 4903 + 370 + 1065, 3946, 10271, 4784 + 660 + 1259, 1671 + 593, 1487, 1208, 348.60, 139.1, 3750),
 2025: (33670, 8516, 3963 + 329 + 1105, 2843, 12349, 7552, 3609, 3621, 1235, 510.45, 138.7, 4025),
 "TTM": (35829, 1951 + 7323, 5880, 593 + 2726, 13331, 7519, 4185, 1534 + 3213, 544 + 741, PRICE, 138.1, 813 + 3672),
}
ratios, prev_rev = {}, 19811
for y, (rev, gp, eb, ni, eq, debt, cash, ocf, capex, px, sh, oi) in FY.items():
    mc = px * sh
    ev = mc + debt - cash + 1000
    ratios[y] = dict(rev=rev, growth=rev / prev_rev - 1, gm=gp / rev, ebitda_m=eb / rev, net_m=ni / rev, roe=ni / eq,
                     pe=mc / ni, ps=mc / rev, pb=mc / eq, ev_rev=ev / rev, ev_ebitda=ev / eb, de=debt / eq,
                     net_cash=cash - debt, fcf_m=(ocf - capex) / rev, op_m=oi / rev,
                     roic=oi * (1 - TAX) / (eq + 1000 + debt - cash), fcf_ni=(ocf - capex) / ni, capex_rev=capex / rev)
    prev_rev = rev if y != 2025 else 33670
ratios["TTM"]["growth"] = 35829 / 33317 - 1   # TTM vs prior-year TTM (Q4-24 + 9M-25 = 8,447 + 25,134 - ... approx)
out["ratios"] = ratios
for y, r in ratios.items():
    print(y, {k: round(v, 3) for k, v in r.items()})

json.dump(out, open("/private/tmp/claude-501/-Users-andreaguida/51e5d6c2-6463-40d8-8707-09be2a0c02e3/scratchpad/cmi/model_out.json", "w"),
          default=float, indent=1)
