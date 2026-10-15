"""
Build a self-contained HTML dashboard (no extra installs, no internet needed) from the dbt marts.

  python dashboard/build_dashboard.py            # reads BigQuery marts, writes dashboard/dashboard.html, opens it
  python dashboard/build_dashboard.py --demo     # preview from the local seed CSVs (no BigQuery needed)

Uses only the standard library + google-cloud-bigquery (already installed with dbt-bigquery).
"""
import argparse, csv, html, os, sys, webbrowser
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = Path(__file__).resolve().parent / "dashboard.html"
COLORS = ["#4f8ff7", "#f59e0b", "#10b981", "#a78bfa", "#ef4444"]


# ----------------------------------------------------------------------------- data access
def profile_defaults():
    """Read project / dataset from ~/.dbt/profiles.yml if present."""
    try:
        import yaml
        p = Path.home() / ".dbt" / "profiles.yml"
        cfg = yaml.safe_load(p.read_text())["ecommerce_analytics"]
        o = cfg["outputs"][cfg.get("target", "dev")]
        return o.get("project"), o.get("dataset", "dbt_dev"), o.get("location")
    except Exception:
        return None, "dbt_dev", None


def fetch_bigquery(project, dataset, location):
    from google.cloud import bigquery
    client = bigquery.Client(project=project, location=location)
    m = f"`{project}.{dataset}_marts`"

    def q(sql):
        return [dict(r) for r in client.query(sql).result()]

    return {
        "daily": q(f"select order_date, channel, orders, completed_orders, returned_orders, revenue, "
                   f"revenue_7d_moving_avg from {m}.fct_daily_revenue order by order_date"),
        "country": q(f"select country, sum(lifetime_revenue) as revenue from {m}.dim_customers group by 1 order by 2 desc"),
        "segments": q(f"select customer_segment, count(*) as customers from {m}.dim_customers group by 1 order by 2 desc"),
        "cohorts": q(f"select cohort_month, months_since_signup, active_customers from {m}.mart_monthly_cohorts"),
    }


def fetch_demo():
    """Same shapes as the marts, computed from the seed CSVs (preview only)."""
    rd = lambda n: list(csv.DictReader(open(ROOT / "seeds" / n)))
    cust, orders, items = rd("raw_customers.csv"), rd("raw_orders.csv"), rd("raw_order_items.csv")
    amt = defaultdict(float)
    for r in items:
        amt[r["order_id"]] += int(r["quantity"]) * float(r["unit_price"])
    d = defaultdict(lambda: dict(orders=0, completed_orders=0, returned_orders=0, revenue=0.0))
    comp = defaultdict(lambda: [0, 0.0])
    for o in orders:
        day = datetime.fromisoformat(o["order_ts"]).date()
        x = d[(day, o["channel"])]
        x["orders"] += 1
        if o["status"] == "completed":
            x["completed_orders"] += 1; x["revenue"] += amt[o["order_id"]]
            comp[o["customer_id"]][0] += 1; comp[o["customer_id"]][1] += amt[o["order_id"]]
        if o["status"] == "returned":
            x["returned_orders"] += 1
    daily, hist = [], defaultdict(list)
    for (day, ch) in sorted(d):
        hist[ch].append(d[(day, ch)]["revenue"])
        last7 = hist[ch][-7:]
        daily.append(dict(order_date=day, channel=ch, **d[(day, ch)], revenue_7d_moving_avg=sum(last7) / len(last7)))
    country, seg = defaultdict(float), defaultdict(int)
    for c in cust:
        n, rev = comp.get(c["customer_id"], [0, 0.0])
        country[c["country"].upper()] += rev
        seg["no_purchase" if n == 0 else "vip" if rev >= 6000 else "loyal" if n >= 6 else "regular"] += 1
    signup = {c["customer_id"]: date.fromisoformat(c["signup_date"]).replace(day=1) for c in cust}
    active = defaultdict(set)
    for o in orders:
        if o["status"] != "completed":
            continue
        om = datetime.fromisoformat(o["order_ts"]).date().replace(day=1)
        sm = signup[o["customer_id"]]
        if om >= sm:
            active[(sm, (om.year - sm.year) * 12 + om.month - sm.month)].add(o["customer_id"])
    return {
        "daily": daily,
        "country": [dict(country=k, revenue=v) for k, v in sorted(country.items(), key=lambda kv: -kv[1])],
        "segments": [dict(customer_segment=k, customers=v) for k, v in sorted(seg.items(), key=lambda kv: -kv[1])],
        "cohorts": [dict(cohort_month=k[0], months_since_signup=k[1], active_customers=len(v)) for k, v in active.items()],
    }


# ----------------------------------------------------------------------------- tiny SVG chart helpers
def money(v):
    v = float(v)
    return f"${v/1e6:.2f}M" if abs(v) >= 1e6 else f"${v/1e3:.1f}K" if abs(v) >= 1e3 else f"${v:,.0f}"


def line_chart(dates, series, w=640, h=280):
    L, R, T, B = 56, 12, 14, 34
    top = max(max(v) for v in series.values()) * 1.1 or 1
    X = lambda i: L + (w - L - R) * i / max(len(dates) - 1, 1)
    Y = lambda v: T + (h - T - B) * (1 - v / top)
    g = []
    for k in range(5):
        v = top * k / 4
        g.append(f'<line x1="{L}" x2="{w-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="grid"/>'
                 f'<text x="{L-6}" y="{Y(v)+4:.1f}" text-anchor="end" class="ax">{money(v)}</text>')
    last_m = None
    for i, dt in enumerate(dates):
        if dt.month != last_m:
            g.append(f'<text x="{X(i):.1f}" y="{h-12}" class="ax">{dt.strftime("%b")}</text>'); last_m = dt.month
    paths = []
    for n, (name, vals) in enumerate(series.items()):
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(vals))
        paths.append(f'<polyline points="{pts}" fill="none" stroke="{COLORS[n % 5]}" stroke-width="2"/>')
    return f'<svg viewBox="0 0 {w} {h}" class="chart">{"".join(g)}{"".join(paths)}</svg>'


def bar_chart(rows, w=640, h=280):
    L, R, T = 56, 70, 10
    top = max(v for _, v in rows) or 1
    bh = (h - T - 10) / len(rows)
    out = []
    for i, (name, v) in enumerate(rows):
        y = T + i * bh
        bw = (w - L - R) * v / top
        out.append(f'<text x="{L-8}" y="{y+bh*0.62:.1f}" text-anchor="end" class="ax">{html.escape(str(name))}</text>'
                   f'<rect x="{L}" y="{y+4:.1f}" width="{bw:.1f}" height="{bh-10:.1f}" rx="4" fill="{COLORS[0]}"/>'
                   f'<text x="{L+bw+6:.1f}" y="{y+bh*0.62:.1f}" class="ax">{money(v)}</text>')
    return f'<svg viewBox="0 0 {w} {h}" class="chart">{"".join(out)}</svg>'


def donut(rows, size=220):
    total = sum(v for _, v in rows) or 1
    r, c, off, out, leg = 70, 2 * 3.14159265 * 70, 0, [], []
    for i, (name, v) in enumerate(rows):
        frac = v / total
        out.append(f'<circle cx="110" cy="110" r="{r}" fill="none" stroke="{COLORS[i % 5]}" stroke-width="34" '
                   f'stroke-dasharray="{frac*c:.2f} {c:.2f}" stroke-dashoffset="{-off*c:.2f}" transform="rotate(-90 110 110)"/>')
        off += frac
        leg.append(f'<div class="lg"><span style="background:{COLORS[i % 5]}"></span>{html.escape(name)} '
                   f'<b>{v:,}</b> ({frac:.0%})</div>')
    svg = f'<svg viewBox="0 0 {size} {size}" class="donut">{"".join(out)}</svg>'
    return f'<div class="donutwrap">{svg}<div>{"".join(leg)}</div></div>'


def heatmap(cohorts):
    if not cohorts:
        return "<p>No cohort data.</p>"
    months = sorted({c["cohort_month"] for c in cohorts})
    cols = sorted({c["months_since_signup"] for c in cohorts})
    val = {(c["cohort_month"], c["months_since_signup"]): c["active_customers"] for c in cohorts}
    mx = max(val.values())
    head = "<tr><th>Cohort</th>" + "".join(f"<th>M{c}</th>" for c in cols) + "</tr>"
    body = ""
    for m in months:
        cells = ""
        for c in cols:
            v = val.get((m, c))
            cells += (f'<td style="background:rgba(79,143,247,{0.1 + 0.9 * v / mx:.2f})">{v}</td>' if v is not None else "<td></td>")
        body += f"<tr><th>{m.strftime('%b %Y') if hasattr(m, 'strftime') else m}</th>{cells}</tr>"
    return f'<table class="heat">{head}{body}</table>'


# ----------------------------------------------------------------------------- page
def render(data, source):
    daily = data["daily"]
    tot_rev = sum(float(r["revenue"]) for r in daily)
    tot_orders = sum(int(r["orders"]) for r in daily)
    tot_comp = sum(int(r["completed_orders"]) for r in daily)
    tot_ret = sum(int(r["returned_orders"]) for r in daily)
    dates = sorted({r["order_date"] for r in daily})
    channels = sorted({r["channel"] for r in daily})
    lookup = {(r["order_date"], r["channel"]): float(r["revenue_7d_moving_avg"]) for r in daily}
    series = {}
    for ch in channels:
        last, vals = 0.0, []
        for d in dates:
            last = lookup.get((d, ch), last); vals.append(last)
        series[ch] = vals
    legend = "".join(f'<span class="lg"><span style="background:{COLORS[i%5]}"></span>{html.escape(c)}</span>' for i, c in enumerate(channels))
    kpis = [("Net revenue", money(tot_rev)), ("Orders", f"{tot_orders:,}"),
            ("Avg order value", money(tot_rev / max(tot_comp, 1))), ("Return rate", f"{tot_ret / max(tot_orders, 1):.1%}")]
    kpi_html = "".join(f'<div class="kpi"><div class="kl">{k}</div><div class="kv">{v}</div></div>' for k, v in kpis)
    css = """
    :root{--bg:#f4f6fb;--card:#fff;--tx:#1b2333;--mu:#6b7488;--gr:#e6e9f1}
    @media (prefers-color-scheme: dark){:root{--bg:#0f1420;--card:#171e2e;--tx:#e8ecf5;--mu:#93a0b8;--gr:#2a3350}}
    body{margin:0;background:var(--bg);color:var(--tx);font-family:Segoe UI,Roboto,Arial,sans-serif}
    .wrap{max-width:1200px;margin:0 auto;padding:24px}
    h1{margin:0 0 4px;font-size:26px}.sub{color:var(--mu);margin-bottom:20px;font-size:13px}
    .kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin-bottom:16px}
    .kpi,.card{background:var(--card);border-radius:12px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
    .kl{color:var(--mu);font-size:13px}.kv{font-size:30px;font-weight:700;margin-top:4px}
    .grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:16px;margin-bottom:16px}
    h2{font-size:15px;margin:0 0 10px}.chart{width:100%;height:auto}
    .grid{stroke:var(--gr);stroke-width:1}.ax{fill:var(--mu);font-size:11px}
    .lg{display:inline-flex;align-items:center;gap:6px;margin:3px 12px 3px 0;font-size:13px}
    .lg span{width:10px;height:10px;border-radius:50%;display:inline-block}
    .donutwrap{display:flex;align-items:center;gap:20px;flex-wrap:wrap}.donut{width:200px}
    .donutwrap .lg{display:flex}
    .heat{border-collapse:collapse;font-size:12px;width:100%}
    .heat th,.heat td{padding:6px 8px;text-align:center;border:1px solid var(--gr)}
    .heat td{color:#0b1220}
    @media(max-width:520px){.grid2{grid-template-columns:1fr}}"""
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>E-commerce Analytics Dashboard</title>
<meta name="viewport" content="width=device-width,initial-scale=1"><style>{css}</style></head><body><div class="wrap">
<h1>E-commerce Analytics Dashboard</h1><div class="sub">Source: {html.escape(source)} &middot; generated {datetime.now():%Y-%m-%d %H:%M} &middot; built from dbt marts</div>
<div class="kpis">{kpi_html}</div>
<div class="grid2">
 <div class="card"><h2>Revenue by channel (7-day moving average)</h2>{line_chart(dates, series)}<div>{legend}</div></div>
 <div class="card"><h2>Lifetime revenue by customer country</h2>{bar_chart([(r['country'], float(r['revenue'])) for r in data['country']])}</div>
</div>
<div class="grid2">
 <div class="card"><h2>Customer segments</h2>{donut([(r['customer_segment'], int(r['customers'])) for r in data['segments']])}</div>
 <div class="card"><h2>Cohort retention (active customers by months since signup)</h2>{heatmap(data['cohorts'])}</div>
</div></div></body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="preview from local seed CSVs, no BigQuery")
    ap.add_argument("--project"); ap.add_argument("--dataset"); ap.add_argument("--location")
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    if a.demo:
        data, source = fetch_demo(), "local seed CSVs (demo)"
    else:
        p, ds, loc = profile_defaults()
        project, dataset, location = a.project or p, a.dataset or ds, a.location or loc
        if not project:
            sys.exit("Project not found. Pass --project YOUR_PROJECT_ID or fill in ~/.dbt/profiles.yml")
        data, source = fetch_bigquery(project, dataset, location), f"BigQuery {project}.{dataset}_marts"
    OUT.write_text(render(data, source), encoding="utf-8")
    print(f"Dashboard written: {OUT}")
    if not a.no_open:
        webbrowser.open(OUT.as_uri())


if __name__ == "__main__":
    main()
