*** Settings ***
Documentation       Suite initialization — verifies the extension is deployed and manages
...                 UAC entities required across all test suites in this directory.
Library             %{UE_CLAUDE_CODE_UAC_LIBRARY_PATH}/robot/UACLibrary.py
Library             OperatingSystem
Suite Setup         Suite Initialize
Suite Teardown      Suite Cleanup


*** Keywords ***
Suite Initialize
    [Documentation]    Load environment, verify extension is deployed, create UAC entities.
    Load Environment
    Extension Should Be Deployed
    # Example — credential wired from .env (user optional, defaults to "Empty User"):
    # ${pass}=    Get Environment Variable    MY_CRED_PASS
    # Create Credential    ue-test-my-cred    ${pass}
    # Example — with explicit user:
    # ${user}=    Get Environment Variable    MY_CRED_USER
    # ${pass}=    Get Environment Variable    MY_CRED_PASS
    # Create Credential    ue-test-my-cred    ${pass}    user=${user}
    # Example — script from atest/data/:
    # Create Script From File    ue-test-my-script    atest/data/my_script.sql

Suite Cleanup
    [Documentation]    Remove UAC entities created during suite initialization.
    # Run Keyword And Ignore Error    Delete Credential    ue-test-my-cred
    # Run Keyword And Ignore Error    Delete Script    ue-test-my-script
    No Operation
