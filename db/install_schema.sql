-- db/install_schema.sql
SET DEFINE OFF
SET SERVEROUTPUT ON
WHENEVER SQLERROR EXIT SQL.SQLCODE

PROMPT ==================================================
PROMPT Installing FDR Investment schema...
PROMPT ==================================================

-- db/install_schema.sql
@@schema/bank_master.sql
@@schema/indicator_setup.sql
@@schema/bank_source_urls.sql
@@schema/bank_eligibility_criteria.sql
@@schema/bank_manual_entry_log.sql
@@schema/bank_performance_fact.sql

PROMPT ==================================================
PROMPT Schema install completed successfully.
PROMPT ==================================================
EXIT