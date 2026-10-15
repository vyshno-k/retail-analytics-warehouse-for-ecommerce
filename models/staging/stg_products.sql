select
    cast(product_id as int64)    as product_id,
    product_name,
    category,
    cast(unit_price as numeric)  as list_price
from {{ ref('raw_products') }}
