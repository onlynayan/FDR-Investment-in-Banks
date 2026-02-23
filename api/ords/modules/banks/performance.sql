DECLARE
    v_bank_id      NUMBER;
    v_indicator_id NUMBER;
    v_numeric_val  NUMBER;
    v_text_val     VARCHAR2(50);
BEGIN
    -- Find Bank ID
    BEGIN
        SELECT bank_id INTO v_bank_id
        FROM bank_master
        WHERE UPPER(bank_name) = UPPER(:bank_name);
    EXCEPTION WHEN NO_DATA_FOUND THEN
        RAISE_APPLICATION_ERROR(-20001, 'Bank "' || :bank_name || '" not found.');
    END;

    -- Find Indicator ID
    BEGIN
        SELECT indicator_id INTO v_indicator_id
        FROM indicator_setup
        WHERE UPPER(indicator_code) = UPPER(:indicator_code);
    EXCEPTION WHEN NO_DATA_FOUND THEN
        RAISE_APPLICATION_ERROR(-20002, 'Indicator Code "' || :indicator_code || '" not found.');
    END;

    -- Determine if the value is numeric or text based on input
    v_numeric_val := TO_NUMBER(:actual_value DEFAULT NULL ON CONVERSION ERROR);
    
    IF v_numeric_val IS NULL THEN
        v_text_val := :actual_value;
    END IF;

    -- Insert into the Fact table
    INSERT INTO BANK_PERFORMANCE_FACT (
        BANK_ID,
        INDICATOR_ID,
        ACTUAL_VALUE_NUMERIC,
        ACTUAL_VALUE_TEXT,
        CALCULATED_SCORE,
        FINANCIAL_YEAR,
        REPORT_PERIOD,
        DATA_SOURCE_URL,
        DATA_SOURCE_TYPE,
        IS_LATEST_DATA_YN
    ) VALUES (
        v_bank_id,
        v_indicator_id,
        v_numeric_val,
        v_text_val,
        :score,
        :year,
        :period,
        :source_url,
        :source_type,
        'Y'
    );

    :status := 201;
    HTP.P('{"message": "Performance data for ' || :indicator_code || ' saved."}');

EXCEPTION
    WHEN OTHERS THEN
        :status := 400;
        HTP.P('{"error": "' || REPLACE(SQLERRM, '"', '') || '"}');
END;