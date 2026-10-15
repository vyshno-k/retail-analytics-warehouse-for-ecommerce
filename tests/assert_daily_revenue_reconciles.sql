-- Fails (returns a row) if the aggregated mart does not reconcile to the fact table.
with a as (select sum(net_revenue) as r from {{ ref('fct_orders') }}),
     b as (select sum(revenue)     as r from {{ ref('fct_daily_revenue') }})
select * from a, b where abs(a.r - b.r) > 0.01
