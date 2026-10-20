{ config(materialized='table') }

WITH source AS (
    SELECT
        PID,
        PNAME,
        PQUAN
    FROM
        { source('legacy', 'PRODUCTS10') }
),

sequence AS (
    SELECT
        NEXTVAL,
        CURRVAL
    FROM
        seq6
),

router AS (
    SELECT
        PID,
        PNAME,
        PQUAN,
        NEXTVAL,
        CASE
            WHEN NEXTVAL >= 1 AND NEXTVAL <= 3 THEN 'firsttarget'
            WHEN NEXTVAL >= 4 AND NEXTVAL <= 6 THEN 'secondtarget'
            ELSE 'DEFAULT1'
        END AS target_group
    FROM
        source
    CROSS JOIN
        sequence
)

SELECT
    PID,
    PNAME,
    PQUAN
FROM
    router
WHERE
    target_group = 'firsttarget'
UNION ALL
SELECT
    PID,
    PNAME,
    PQUAN
FROM
    router
WHERE
    target_group = 'secondtarget'
UNION ALL
SELECT
    PID,
    PNAME,
    PQUAN
FROM
    router
WHERE
    target_group = 'DEFAULT1'
