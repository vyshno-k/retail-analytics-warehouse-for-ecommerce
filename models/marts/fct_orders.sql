{{
  config(
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    partition_by={'field': 'order_date', 'data_type': 'date'},
    cluster_by=['customer_id', 'channel']
  )
}}

with items as (
    select order_id,
           sum(line_amount) as gross_amount,
           sum(quantity)    as units,
           count(*)         as line_count
    from {{ ref('stg_order_items') }}
    group by 1
),
orders as (
    select * from {{ ref('stg_orders') }}
    {% if is_incremental() %}
    where order_date >= date_sub(current_date(), interval {{ var('incremental_lookback_days') }} day)
    {% endif %}
)
select
    o.order_id,
    o.customer_id,
    o.order_ts,
    o.order_date,
    o.order_status,
    o.channel,
    i.units,
    i.line_count,
    i.gross_amount,
    -- only completed orders count as recognised revenue
    if(o.order_status = 'completed', i.gross_amount, 0) as net_revenue
from orders o
left join items i using (order_id)
