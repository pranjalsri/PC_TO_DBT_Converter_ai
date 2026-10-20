# Test cases: mapping_scenario1

### Test Case 1: Verify Data Flow from Source to Target
**Test Case ID:** TC_ETL_MAP_001  
**Description:** Ensure that data flows correctly from the source to the target tables without any transformation errors.

**Steps:**
1. Load sample data into the source table `PRODUCTS10` with the following values:
   - PID: 1, PNAME: 'Product A', PQUAN: 10
   - PID: 2, PNAME: 'Product B', PQUAN: 20
   - PID: 3, PNAME: 'Product C', PQUAN: 30
   - PID: 4, PNAME: 'Product D', PQUAN: 40
   - PID: 5, PNAME: 'Product E', PQUAN: 50
   - PID: 6, PNAME: 'Product F', PQUAN: 60

2. Run the ETL process.

3. Verify that the data is correctly distributed across the three target tables:
   - `PRODUCTS10_TGT` should contain rows with PID: 1, 2, 3
   - `PRODUCTS10_TGT2` should contain rows with PID: 4, 5
   - `PRODUCTS10_TGT3` should contain rows with PID: 6

**Acceptance Criteria:**
- All rows from the source table should be present in the respective target tables.
- The data in each target table should match the source data.

### Test Case 2: Verify Data Integrity in Target Tables
**Test Case ID:** TC_ETL_MAP_002  
**Description:** Ensure that the data integrity is maintained in the target tables.

**Steps:**
1. Load sample data into the source table `PRODUCTS10` with the following values:
   - PID: 1, PNAME: 'Product A', PQUAN: 10
   - PID: 2, PNAME: 'Product B', PQUAN: 20
   - PID: 3, PNAME: 'Product C', PQUAN: 30

2. Run the ETL process.

3. Verify that the data in each target table is consistent and there are no duplicate or missing rows.

**Acceptance Criteria:**
- Each target table should contain unique rows based on the PID.
- There should be no duplicate or missing rows in any of the target tables.

### Test Case 3: Verify Data Handling for Null Values
**Test Case ID:** TC_ETL_MAP_003  
**Description:** Ensure that the ETL process handles null values correctly.

**Steps:**
1. Load sample data into the source table `PRODUCTS10` with the following values:
   - PID: 1, PNAME: 'Product A', PQUAN: 10
   - PID: 2, PNAME: 'Product B', PQUAN: NULL
   - PID: 3, PNAME: NULL, PQUAN: 30

2. Run the ETL process.

3. Verify that the null values are handled correctly in the target tables:
   - `PRODUCTS10_TGT` should contain rows with PID: 1, 2, 3
   - `PRODUCTS10_TGT2` should contain rows with PID: 2, 3
   - `PRODUCTS10_TGT3` should contain rows with PID: 3

**Acceptance Criteria:**
- Null values in the source table should be handled correctly in the target tables.
- The target tables should not contain any rows with null values in the PNAME or PQUAN columns.

### Test Case 4: Verify Data Handling for Out-of-Range Values
**Test Case ID:** TC_ETL_MAP_004  
**Description:** Ensure that the ETL process handles out-of-range values correctly.

**Steps:**
1. Load sample data into the source table `PRODUCTS10` with the following values:
   - PID: 1, PNAME: 'Product A', PQUAN: 10
   - PID: 2, PNAME: 'Product B', PQUAN: 1000
   - PID: 3, PNAME: 'Product C', PQUAN: -10

2. Run the ETL process.

3. Verify that the out-of-range values are handled correctly in the target tables:
   - `PRODUCTS10_TGT` should contain rows with PID: 1, 2, 3
   - `PRODUCTS10_TGT2` should contain rows with PID: 2, 3
   - `PRODUCTS10_TGT3` should contain rows with PID: 3

**Acceptance Criteria:**
- Out-of-range values in the source table should be handled correctly in the target tables.
- The target tables should not contain any rows with out-of-range values in the PQUAN column.

### Test Case 5: Verify Data Handling for Duplicate Rows
**Test Case ID:** TC_ETL_MAP_005  
**Description:** Ensure that the ETL process handles duplicate rows correctly.

**Steps:**
1. Load sample data into the source table `PRODUCTS10` with the following values:
   - PID: 1, PNAME: 'Product A', PQUAN: 10
   - PID: 1, PNAME: 'Product A', PQUAN: 10
   - PID: 2, PNAME: 'Product B', PQUAN: 20

2. Run the ETL process.

3. Verify that the duplicate rows are handled correctly in the target tables:
   - `PRODUCTS10_TGT` should contain rows with PID: 1, 2
   - `PRODUCTS10_TGT2` should contain rows with PID: 1, 2
   - `PRODUCTS10_TGT3` should contain rows with PID: 1, 2

**Acceptance Criteria:**
- Duplicate rows in the source table should be handled correctly in the target tables.
- The target tables should not contain any duplicate rows based on the PID.

### Test Case 6: Verify Data Handling for Large Data Sets
**Test Case ID:** TC_ETL_MAP_006  
**Description:** Ensure that the ETL process handles large data sets correctly.

**Steps:**
1. Load a large number of sample data into the source table `PRODUCTS10` (e.g., 10,000 rows).

2. Run the ETL process.

3. Verify that the data is correctly distributed across the three target tables:
   - `PRODUCTS10_TGT` should contain approximately 3,333 rows
   - `PRODUCTS10_TGT2` should contain approximately 3,333 rows
   - `PRODUCTS10_TGT3` should contain approximately 3,334 rows

**Acceptance Criteria:**
- The ETL process should handle large data sets efficiently.
- The data should be correctly distributed across the target tables without any errors.

### Test Case 7: Verify Data Handling for Performance
**Test Case ID:** TC_ETL_MAP_007  
**Description:** Ensure that the ETL process performs well under load.

**Steps:**
1. Load a large number of sample data into the source table `PRODUCTS10` (e.g., 100,000 rows).

2. Run the ETL process multiple times to measure performance.

3. Verify that the ETL process completes within an acceptable time frame.

**Acceptance Criteria:**
- The ETL process should complete within a reasonable time frame (e.g., less than 10 minutes).
- The performance should be consistent across multiple runs.

### Test Case 8: Verify Data Handling for Error Conditions
**Test Case ID:** TC_ETL_MAP_008  
**Description:** Ensure that the ETL process handles error conditions correctly.

**Steps:**
1. Introduce an error condition in the source data, such as a syntax error in the SQL query.

2. Run the ETL process.

3. Verify that the error is handled correctly and the process fails gracefully.

**Acceptance Criteria:**
- The ETL process should detect the error condition and fail gracefully.
- The error should be logged for further investigation.

### Test Case 9: Verify Data Handling for Data Type Mismatch
**Test Case ID:** TC_ETL_MAP_009  
**Description:** Ensure that the ETL process handles data type mismatches correctly.

**Steps:**
1. Load sample data into the source table `PRODUCTS10` with the following values:
   - PID: 1, PNAME: 'Product A', PQUAN: '10' (string instead of number)

2. Run the ETL process.

3. Verify that the data type mismatch is handled correctly in the target tables:
   - `PRODUCTS10_TGT` should contain rows with PID: 1, PNAME: 'Product A', PQUAN: 10
   - `PRODUCTS10_TGT2` should contain rows with PID: 1, PNAME: 'Product A', PQUAN: 10
   - `PRODUCTS10_TGT3` should contain rows with PID: 1, PNAME: 'Product A', PQUAN: 10

**Acceptance Criteria:**
- Data type mismatches in the source table should be handled correctly in the target tables.
- The target tables should contain the correct data types for each column.

### Test Case 10: Verify Data Handling for Data Masking
**Test Case ID:** TC_ETL_MAP_010  
**Description:** Ensure that the ETL process handles data masking correctly.

**Steps:**
1. Load sample data into the source table `PRODUCTS10` with the following values:
   - PID: 1, PNAME: 'Product A', PQUAN: 10
   - PID: 2, PNAME: 'Product B', PQUAN: 20
   - PID: 3, PNAME: 'Product C', PQUAN: 30

2. Configure the ETL process to mask the PNAME column.

3. Run the ETL process.

4. Verify that the PNAME column is masked in the target tables:
   - `PRODUCTS10_TGT` should contain rows with PID: 1, PNAME: '****', PQUAN: 10
   - `PRODUCTS10_TGT2` should contain rows with PID: 1, PNAME: '****', PQUAN: 10
   - `PRODUCTS10_TGT3` should contain rows with PID: 1, PNAME: '****', PQUAN: 10

**Acceptance Criteria:**
- The PNAME column should be masked in the target tables.
- The target tables should not contain the actual PNAME values.
