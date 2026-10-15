-- Daily data-quality checks to run after `dbt build` (BigQuery SQL).
-- Replace YOUR_PROJECT and dataset names (dbt prefixes custom schemas: <dataset>_marts).

-- 1. Orders without line items
select count(*) as orders_without_items
from `YOUR_PROJECT.dbt_dev_marts.fct_orders` where gross_amount is null;

-- 2. Freshness
select max(order_date) as latest_order_date,
       date_diff(current_date(), max(order_date), day) as days_stale
from `YOUR_PROJECT.dbt_dev_marts.fct_orders`;

-- 3. Revenue by status (sanity)
select order_status, count(*) as orders, round(sum(gross_amount), 2) as gross
from `YOUR_PROJECT.dbt_dev_marts.fct_orders` group by 1;
