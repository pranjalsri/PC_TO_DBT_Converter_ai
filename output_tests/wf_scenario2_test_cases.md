# Test cases: mapping_scenario2

### Test Case 1: Verify Data Flow from Source to Target
**Test Case ID:** TC_ETL_MAP_001  
**Description:** Ensure that data flows correctly from the source to all three target tables (PRODUCTS10_TGT, PRODUCTS10_TGT2, PRODUCTS10_TGT3) based on the router logic.

**Steps:**
1. Load test data into the source table (PRODUCTS10) with various combinations of PID, PNAME, and PQUAN.
2. Execute the mapping.
3. Verify that the data is correctly routed to the appropriate target tables based on the router logic.

**Logic:**
- Router logic: 
  - If NEXTVAL = 1 or NEXTVAL = 6, route to PRODUCTS10_TGT2.
  - If NEXTVAL = 2 or NEXTVAL = 5, route to PRODUCTS10_TGT3.
  - If NEXTVAL = 3 or NEXTVAL = 4, route to PRODUCTS10_TGT.

**Acceptance Criteria:**
- Each target table should contain the correct subset of data based on the router logic.
- The total number of rows in all target tables should equal the number of rows in the source table.

### Test Case 2: Verify Data Integrity in Target Tables
**Test Case ID:** TC_ETL_MAP_002  
**Description:** Ensure that the data integrity is maintained in the target tables after the mapping execution.

**Steps:**
1. Load test data into the source table (PRODUCTS10) with various combinations of PID, PNAME, and PQUAN.
2. Execute the mapping.
3. Verify that the data in each target table is consistent and does not contain any duplicates or errors.

**Logic:**
- Check for the presence of duplicate rows in each target table.
- Verify that the data types and constraints are maintained in each target table.

**Acceptance Criteria:**
- Each target table should not contain any duplicate rows.
- The data types and constraints in each target table should match the source table.

### Test Case 3: Verify Null Values Handling
**Test Case ID:** TC_ETL_MAP_003  
**Description:** Ensure that the mapping handles null values correctly in the source and target tables.

**Steps:**
1. Load test data into the source table (PRODUCTS10) with various combinations of null and non-null values for PID, PNAME, and PQUAN.
2. Execute the mapping.
3. Verify that the null values are handled correctly in the target tables.

**Logic:**
- Check if null values are preserved or replaced with default values in the target tables.
- Verify that the router logic correctly routes rows with null values.

**Acceptance Criteria:**
- Null values should be preserved or replaced with default values as specified in the mapping.
- The router logic should correctly route rows with null values.

### Test Case 4: Verify Performance under Load
**Test Case ID:** TC_ETL_MAP_004  
**Description:** Ensure that the mapping performs well under load with a large number of rows.

**Steps:**
1. Load a large number of test data into the source table (PRODUCTS10).
2. Execute the mapping.
3. Monitor the performance metrics (e.g., execution time, resource usage) during the mapping execution.

**Logic:**
- Measure the execution time and resource usage during the mapping execution.
- Compare the performance metrics with the expected values.

**Acceptance Criteria:**
- The mapping should complete within an acceptable time frame.
- The resource usage should be within the expected limits.

### Test Case 5: Verify Error Handling
**Test Case ID:** TC_ETL_MAP_005  
**Description:** Ensure that the mapping handles errors gracefully and logs appropriate error messages.

**Steps:**
1. Introduce errors in the source data (e.g., invalid data types, missing required fields).
2. Execute the mapping.
3. Verify that the mapping logs appropriate error messages and handles the errors gracefully.

**Logic:**
- Check the error logs for any error messages related to the source data.
- Verify that the mapping handles the errors gracefully and does not fail.

**Acceptance Criteria:**
- The mapping should log appropriate error messages for any errors in the source data.
- The mapping should handle errors gracefully and not fail.

### Test Case 6: Verify Data Consistency Across Targets
**Test Case ID:** TC_ETL_MAP_006  
**Description:** Ensure that the data is consistent across all target tables after the mapping execution.

**Steps:**
1. Load test data into the source table (PRODUCTS10) with various combinations of PID, PNAME, and PQUAN.
2. Execute the mapping.
3. Verify that the data is consistent across all target tables.

**Logic:**
- Check if the data is consistent across all target tables.
- Verify that the total number of rows in all target tables equals the number of rows in the source table.

**Acceptance Criteria:**
- The data should be consistent across all target tables.
- The total number of rows in all target tables should equal the number of rows in the source table.
