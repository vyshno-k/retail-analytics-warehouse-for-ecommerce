select
    cast(order_id as int64)            as order_id,
    cast(customer_id as int64)         as customer_id,
    cast(order_ts as timestamp)        as order_ts,
    date(cast(order_ts as timestamp))  as order_date,
    lower(status)                      as order_status,
    channel
from {{ ref('raw_orders') }}
