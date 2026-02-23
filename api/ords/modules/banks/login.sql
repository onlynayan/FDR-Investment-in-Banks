DECLARE
    v_workspace_id NUMBER;
    v_auth_result  BOOLEAN;
BEGIN
    apex_util.set_workspace(p_workspace => 'CPA_INVST'); 

    v_auth_result := APEX_UTIL.IS_LOGIN_PASSWORD_VALID(
                        p_username => :username,
                        p_password => :password
                     );

    IF v_auth_result THEN
        :status := 200;
        HTP.P('{"status": "success", "username": "' || :username || '"}');
    ELSE
        :status := 401;
        HTP.P('{"status": "error", "message": "Invalid username or password"}');
    END IF;

EXCEPTION
    WHEN OTHERS THEN
        :status := 555;
        HTP.P('{"status": "error", "detail": "' || REPLACE(SQLERRM, '"', '') || '"}');
END;