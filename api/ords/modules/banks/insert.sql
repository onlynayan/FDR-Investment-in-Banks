DECLARE
    v_bank_id NUMBER;
BEGIN
    SELECT bank_id
    INTO v_bank_id
    FROM bank_master
    WHERE UPPER(bank_name) = UPPER(:bank_name);

    INSERT INTO BANK_ELIGIBILITY_CRITERIA (
        BANK_ID,
        FISCAL_YEAR,
        FIN_PERIOD,
        NPL_RATIO,
        PROVISION_COVERAGE_RATIO,
        CREDIT_RATING
    ) VALUES (
        v_bank_id,
        :fiscal_year,
        :fin_period,
        :npl,
        :pcr,
        :credit_rating
    );

    :status := 201;

    HTP.P(
        '{"message": "Data for ' || :bank_name || ' inserted successfully."}'
    );

EXCEPTION
    WHEN NO_DATA_FOUND THEN
        :status := 404;
        HTP.P('{"error": "Bank name not found in master table."}');

    WHEN OTHERS THEN
        :status := 400;
        HTP.P('{"error": "' || REPLACE(SQLERRM, '"', '') || '"}');
END;
