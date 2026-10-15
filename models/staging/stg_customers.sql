select
    cast(customer_id as int64)   as customer_id,
    trim(full_name)              as full_name,
    lower(trim(email))           as email,
    upper(country)               as country,
    cast(signup_date as date)    as signup_date
from {{ ref('raw_customers') }}
