with agg as (
    select
        customer_id,
        min(order_date)                       as first_order_date,
        max(order_date)                       as last_order_date,
        countif(order_status = 'completed')   as completed_orders,
        sum(net_revenue)                      as lifetime_revenue
    from {{ ref('fct_orders') }}
    group by 1
)
select
    c.customer_id,
    c.full_name,
    c.email,
    c.country,
    c.signup_date,
    a.first_order_date,
    a.last_order_date,
    coalesce(a.completed_orders, 0) as completed_orders,
    coalesce(a.lifetime_revenue, 0) as lifetime_revenue,
    case
        when coalesce(a.completed_orders, 0) = 0 then 'no_purchase'
        when a.lifetime_revenue >= 6000 then 'vip'
        when a.completed_orders >= 6 then 'loyal'
        else 'regular'
    end as customer_segment
from {{ ref('stg_customers') }} c
left join agg a using (customer_id)
