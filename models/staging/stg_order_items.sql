select
    cast(order_id as int64)    as order_id,
    cast(product_id as int64)  as product_id,
    cast(quantity as int64)    as quantity,
    cast(unit_price as numeric) as unit_price,
    cast(quantity as int64) * cast(unit_price as numeric) as line_amount
from {{ ref('raw_order_items') }}
