{{
    config(materialized='table')
}}

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
        seq3
),

router AS (
    SELECT
        NEXTVAL,
        PID,
        PNAME,
        PQUAN,
        CASE
            WHEN NEXTVAL IN (1, 6) THEN 'tgt1'
            WHEN NEXTVAL IN (2, 5) THEN 'tgt2'
            ELSE 'DEFAULT1'
        END AS target
    FROM
        source
    CROSS JOIN
        sequence
),

tgt1 AS (
    SELECT
        NEXTVAL AS NEXTVAL1,
        PID AS PID1,
        PNAME AS PNAME1,
        PQUAN AS PQUAN1
    FROM
        router
    WHERE
        target = 'tgt1'
),

tgt2 AS (
    SELECT
        NEXTVAL AS NEXTVAL3,
        PID AS PID3,
        PNAME AS PNAME3,
        PQUAN AS PQUAN3
    FROM
        router
    WHERE
        target = 'tgt2'
),

tgt_default AS (
    SELECT
        NEXTVAL AS NEXTVAL2,
        PID AS PID2,
        PNAME AS PNAME2,
        PQUAN AS PQUAN2
    FROM
        router
    WHERE
        target = 'DEFAULT1'
)

INSERT INTO PRODUCTS10_TGT2 (PID, PNAME, PQUAN)
SELECT PID1, PNAME1, PQUAN1 FROM tgt1;

INSERT INTO PRODUCTS10_TGT (PID, PNAME, PQUAN)
SELECT PID2, PNAME2, PQUAN2 FROM tgt_default;

INSERT INTO PRODUCTS10_TGT3 (PID, PNAME, PQUAN)
SELECT PID3, PNAME3, PQUAN3 FROM tgt2;
