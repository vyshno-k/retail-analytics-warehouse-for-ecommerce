# SETUP GUIDE: dbt + BigQuery project (free, no credit card)

Azure is NOT needed for this project. BigQuery is Google Cloud, and its free **sandbox** needs only a Google account.

## 1. Requirements
| Item | Version / note |
|---|---|
| Google account | any Gmail account |
| BigQuery sandbox | free: 10 GB storage, 1 TB queries/month, tables expire after 60 days |
| Python | 3.10, 3.11 or 3.12 (3.11 recommended; avoid 3.13 until dbt-bigquery supports it for you) |
| Google Cloud CLI (`gcloud`) | latest |
| dbt | `dbt-bigquery` (installs dbt-core too) |
| Optional | VS Code, Git |

## 2. Create the BigQuery sandbox project
1. Open https://console.cloud.google.com/bigquery and sign in.
2. Top bar -> project picker -> **New Project** -> name `dbt-portfolio` -> Create.
3. Copy the **Project ID** (looks like `dbt-portfolio-123456`; it is not the project name).
4. Open BigQuery in that project. A banner says you are in the **sandbox**. That is fine.

## 3. Install tools
**Python:** https://www.python.org/downloads/ (tick "Add Python to PATH" on Windows). Check: `python --version`.

**gcloud CLI:** https://cloud.google.com/sdk/docs/install. After install, open a NEW terminal and run:
```bash
gcloud --version
gcloud auth login                              # browser sign-in
gcloud auth application-default login          # IMPORTANT: this is what dbt uses
gcloud config set project YOUR_PROJECT_ID
```

## 4. Create a virtual environment and install dbt
Unzip the project, open a terminal in the folder `dbt-bigquery-ecommerce`:
```bash
python -m venv .venv
# Mac/Linux:
source .venv/bin/activate
# Windows PowerShell:
.venv\Scripts\Activate.ps1      # if blocked: Set-ExecutionPolicy -Scope Process RemoteSigned

pip install --upgrade pip
pip install dbt-bigquery
dbt --version
```
**Expected:** `dbt --version` lists `installed:` for dbt-core and `bigquery:` under Plugins.

## 5. Configure the dbt profile
Copy `profiles.yml.example` to:
- Mac/Linux: `~/.dbt/profiles.yml`
- Windows: `C:\Users\<you>\.dbt\profiles.yml`

Edit `project:` to your Project ID. Keep `location: US`, `dataset: dbt_dev`.

## 6. Run the project (in this order)
```bash
dbt debug      # connection test
dbt deps       # installs dbt_utils
dbt seed       # loads 4 CSVs to BigQuery
dbt build      # runs models + all tests
```

### Expected output
**`dbt debug`** ends with: `All checks passed!` (look for `Connection test: [OK connection ok]`).

**`dbt seed`** ends like:
```
Completed successfully
Done. PASS=4 WARN=0 ERROR=0 SKIP=0 TOTAL=4
```
**`dbt build`** ends like (about 35 nodes: 4 seeds + 8 models + 23 tests):
```
Done. PASS=35 WARN=0 ERROR=0 SKIP=0 TOTAL=35
```
Timings vary. What matters: **ERROR=0**. If your TOTAL differs slightly, that is OK as long as nothing fails.

## 6b. ONE COMMAND: run everything and open the dashboard
```bash
python run_all.py
```
This runs `dbt deps`, `dbt seed`, `dbt build`, then builds `dashboard/dashboard.html` from your BigQuery marts and **opens it in your browser automatically**. If you only want to rebuild the dashboard later: `python dashboard/build_dashboard.py`.

Want a preview before setting up BigQuery? `python dashboard/build_dashboard.py --demo` builds the same dashboard from the local CSV seeds. See `dashboard/preview.png` for what it looks like.

### What the dashboard shows
- 4 KPI cards: Net revenue **$1.94M**, Orders **3,000**, Avg order value **~$782**, Return rate **~7.6%**
- Line chart: 7-day moving average of revenue for 3 channels (web, mobile, marketplace), April to September
- Bar chart: lifetime revenue by country (6 bars: SG, IN, AE, DE, UK, US)
- Donut: customer segments (regular 309, loyal 121, vip 65, no_purchase 5)
- Cohort heatmap: active customers by signup month and months since signup

If the numbers above match, your pipeline is correct.

## 7. Verify the data in BigQuery
In the BigQuery console you should see three new datasets: `dbt_dev_raw`, `dbt_dev_staging`, `dbt_dev_marts`.
Run these in the query editor (replace `YOUR_PROJECT`). Values are exact for the provided seed data:

```sql
-- 1) Row counts
select 'fct_orders' t, count(*) n from `YOUR_PROJECT.dbt_dev_marts.fct_orders`          -- 3000
union all select 'dim_customers', count(*) from `YOUR_PROJECT.dbt_dev_marts.dim_customers`   -- 500
union all select 'fct_daily_revenue', count(*) from `YOUR_PROJECT.dbt_dev_marts.fct_daily_revenue`; -- 548

-- 2) Orders by status
select order_status, count(*) orders from `YOUR_PROJECT.dbt_dev_marts.fct_orders` group by 1 order by 2 desc;
-- completed 2480 | cancelled 292 | returned 228

-- 3) Revenue totals
select round(sum(gross_amount),2) gross, round(sum(net_revenue),2) net
from `YOUR_PROJECT.dbt_dev_marts.fct_orders`;
-- gross 2350785.42 | net 1938172.58

-- 4) Customer segments
select customer_segment, count(*) customers from `YOUR_PROJECT.dbt_dev_marts.dim_customers` group by 1 order by 2 desc;
-- regular 309 | loyal 121 | vip 65 | no_purchase 5

-- 5) Date range
select min(order_date), max(order_date) from `YOUR_PROJECT.dbt_dev_marts.fct_orders`;
-- 2026-04-01 | 2026-09-30
```
Also check: open `fct_orders` -> **Details** tab -> it should show *Partitioned by DAY on order_date* and *Clustered by customer_id, channel*.

**Incremental test:** run `dbt run -s fct_orders` again. It succeeds and the count stays 3000. The lookback window only reprocesses the last 3 days, and the sample data ends in September.

**Docs / lineage:** `dbt docs generate` then `dbt docs serve` opens a browser with the lineage graph. Take a screenshot for your portfolio.

## 8. Optional: also build a Looker Studio dashboard
1. https://lookerstudio.google.com -> Create -> Report -> BigQuery connector -> pick your project -> `dbt_dev_marts` -> `fct_daily_revenue` -> Add.
2. Add scorecards: Sum of `revenue` (about 1.94M), Sum of `orders` (3000), Average `avg_order_value`.
3. Add a time series: dimension `order_date`, metric `revenue`, breakdown `channel`.
4. Add data sources `dim_customers` (pie chart of `customer_segment`, bar chart of revenue by `country`) and `mart_monthly_cohorts` (pivot table: rows `cohort_month`, columns `months_since_signup`, metric `active_customers`, heatmap colouring).
5. Screenshot every page.

## 9. Troubleshooting
| Error | Fix |
|---|---|
| `Could not automatically determine credentials` | Re-run `gcloud auth application-default login` |
| `Profile ecommerce_analytics not found` | profiles.yml is in the wrong folder or the top key is renamed |
| `403 ... bigquery.jobs.create` or `Not found: Project` | Wrong Project ID (use the ID, not the name); run `gcloud config set project ID` |
| `Dataset ... was not found in location X` | `location` in profiles.yml must match; use `US` and delete any datasets created in another region |
| `dbt_utils ... not found` / `macro ... undefined` | Run `dbt deps` |
| Billing / DML errors on the sandbox | Sandbox rules change over time. Fix: enable the free trial or free tier in Google Cloud Billing (a card is required but you are not charged unless you upgrade), then re-run `dbt build` |
| `pip install dbt-bigquery` fails | Use Python 3.11 in a fresh venv |
| `dbt` not found | Activate the venv again in the new terminal |
| Dashboard script: `Project not found` | Run `python dashboard/build_dashboard.py --project YOUR_PROJECT_ID --dataset dbt_dev` |
| Dashboard script: `Not found: Table ... mart` | Run `dbt build` first; check the dataset name ends with `_marts` |
| Browser did not open | Open `dashboard/dashboard.html` by double-clicking it |
