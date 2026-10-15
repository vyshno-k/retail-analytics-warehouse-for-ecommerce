-- Retention by signup-month cohort (feeds a heatmap in the dashboard)
with c as (
    select customer_id, date_trunc(signup_date, month) as cohort_month
    from {{ ref('stg_customers') }}
),
o as (
    select customer_id, date_trunc(order_date, month) as order_month
    from {{ ref('fct_orders') }}
    where order_status = 'completed'
    group by 1, 2
)
select
    c.cohort_month,
    date_diff(o.order_month, c.cohort_month, month) as months_since_signup,
    count(distinct o.customer_id)                   as active_customers
from c
join o using (customer_id)
where o.order_month >= c.cohort_month
group by 1, 2
