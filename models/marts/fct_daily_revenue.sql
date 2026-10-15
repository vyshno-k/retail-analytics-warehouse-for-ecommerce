with daily as (
    select
        order_date,
        channel,
        count(*)                            as orders,
        countif(order_status = 'completed') as completed_orders,
        countif(order_status = 'returned')  as returned_orders,
        count(distinct customer_id)         as unique_customers,
        sum(net_revenue)                    as revenue
    from {{ ref('fct_orders') }}
    group by 1, 2
)
select
    *,
    {{ safe_divide('revenue', 'completed_orders') }} as avg_order_value,
    {{ safe_divide('returned_orders', 'orders') }}   as return_rate,
    avg(revenue) over (
        partition by channel order by order_date
        rows between 6 preceding and current row
    ) as revenue_7d_moving_avg
from daily
