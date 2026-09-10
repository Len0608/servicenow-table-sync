"""
Extension module template for UAC Universal Extensions.

This module provides the Extension class with extension_start() method that is called
by UAC when the extension task executes. It orchestrates all components:
- Input validation (InputFields)
- Action dispatch (ACTION_MAPPER)
- Output formatting (ActionOutput)
- Extension state management (ExtensionManager)
"""

import json
import platform
import sys

from universal_extension import UniversalExtension, ExtensionResult, logger
from universal_extension.deco.choice import dynamic_choice_command
from fields.input import InputFields
from actions.output import ActionOutput
from actions import ACTION_MAPPER
from exceptions import ExecutionError, UnexpectedSystemError
from manager import ExtensionManager
from utility import UACConnectionHandler, ServiceNowConnectionHandler

# Extension metadata - UPDATE THESE FROM YOUR ANALYSIS
EXTENSION_NAME = "extension-code"
EXTENSION_VERSION = "1.0.0"

extension_manager = ExtensionManager()


def _log_debug_info():
    system, release, _, _, machine, _ = platform.uname()
    logger.info(
        "Python sys.executable=%s, version=%s, system=%s, release=%s, machine=%s",
        sys.executable, sys.version, system, release, machine,
    )


# ============================================================================
# Extension Class
# ============================================================================

class Extension(UniversalExtension):
    """
    Universal Extension entry point.

    This class inherits from UniversalExtension as required by the UAC framework.
    """

    def extension_start(self, fields: dict) -> ExtensionResult:
        """
        Main entry point called by UAC when extension task executes.

        Flow:
        1. Preprocess fields via InputFields.preprocess_fields()
        2. Parse and validate input (InputFields)
        3. Dispatch to action (ACTION_MAPPER)
        4. Action executes, prints to STDOUT, returns ActionOutput
        5. Build ExtensionResult via build_result()
        6. Return ExtensionResult

        Args:
            fields: Dictionary containing all input field values from UAC

        Returns:
            ExtensionResult with rc, message, and optional unv_output
        """
        # Initialize extension manager at start
        extension_manager.clear()
        uip = getattr(self, "uip", None)
        if uip is not None:
            task_variables = getattr(uip, "task_variables", None)
            if task_variables is not None:
                extension_manager.set_uac_variables(task_variables)

        input_data = None
        processed_fields = {}

        try:
            logger.info("%s v%s started", EXTENSION_NAME, EXTENSION_VERSION)
            _log_debug_info()

            # Preprocess fields via InputFields static method
            processed_fields = InputFields.preprocess_fields(fields)

            # Parse and validate input (triggers validation in __post_init__)
            input_data = InputFields(**processed_fields)
            logger.info("Action requested: %s", input_data.action.value)

            # Get action function from mapper
            action_func = ACTION_MAPPER.get(input_data.action.value)

            # Execute action - action prints to STDOUT and returns ActionOutput
            logger.info("Executing action: %s", input_data.action.value)
            action_output: ActionOutput = action_func(input_data)

            # Print action output to STDOUT
            action_output.print_output()

            # Build success result
            logger.info("%s completed successfully", EXTENSION_NAME)
            return self.build_result(
                input_fields=input_data,
                result=action_output.to_dict(),
                status_description=action_output.message
            )
        except ExecutionError as e:
            # Custom extension exception (validation, auth, service errors, etc.)
            logger.error("Execution error: %s", e.message)

            # Add error to manager if not already collected
            if not e in extension_manager.errors:
                extension_manager.add_error(e)

            # Create InputFields without validation for error reporting
            if processed_fields:
                input_data = InputFields(**processed_fields, _skip_validation=True)

            return self.build_result(
                input_fields=input_data,
                result=extension_manager.result,
                errors=extension_manager.to_array(),
                exit_code=e.exit_code,
                status_description=e.message
            )
        except Exception as e:
            # Capture exception details for debugging
            error_msg = str(e) if str(e) else f"{type(e).__name__}"
            exc = UnexpectedSystemError(error_msg)
            extension_manager.add_error(exc)

            if processed_fields:
                input_data = InputFields(**processed_fields, _skip_validation=True)

            return self.build_result(
                input_fields=input_data,
                result=extension_manager.result,
                errors=extension_manager.to_array(),
                exit_code=exc.exit_code,
                status_description=exc.message
            )


    def build_result(
        self,
        input_fields: InputFields = None,
        result: dict = None,
        errors: list = None,
        exit_code: int = 0,
        status_description: str = "Successful Execution"
    ) -> ExtensionResult:
        """
        Build ExtensionResult with structured unv_output.

        Args:
            input_fields: Input fields (InputFields instance, optional)
            result: Result dictionary from action or ErrorManager
            errors: Errors array (empty list for success, error list for failures)
            exit_code: Exit code (0 for success, 1+ for errors)
            status_description: Human-readable status message

        Returns:
            ExtensionResult with structured unv_output

        Example (success):
            return self.build_result(
                input_fields=input_data,
                result=action_output.to_dict(),
                errors=[],
                exit_code=0,
                status_description=action_output.message
            )

        Example (error):
            return self.build_result(
                input_fields=input_data,
                result=extension_manager.result,
                errors=extension_manager.to_array(),
                exit_code=1,
                status_description="Execution failed"
            )
        """
        # Set defaults
        if result is None:
            result = {}
        if errors is None:
            errors = []

        # Convert input_fields to dict (if provided)
        # Uses to_dict() to exclude internal fields and empty previous_output
        input_dict = input_fields.to_dict() if input_fields else {}

        # Build unv_output structure
        unv_output = {
            "exit_code": exit_code,
            "status_description": status_description,
            "metadata": {
                "version": EXTENSION_VERSION,
                "extension": EXTENSION_NAME
            },
            "input_fields": input_dict,
            "result": result,
            "errors": errors
        }

        return ExtensionResult(
            rc=exit_code,
            message=status_description,
            unv_output=json.dumps(unv_output, indent=2, default=str)
        )

    def extension_cancel(self):
        """
        Called when extension is cancelled.

        Sets extension_manager.cancelled = True which can be checked in actions:
            if extension_manager.is_cancelled():
                raise OperationCancelledError("User cancelled")

        Override to add custom cleanup:
            def extension_cancel(self):
                super().extension_cancel()  # Set the cancelled flag
                logger.info("Cleaning up resources")
                # Close connections, cleanup files, etc.
        """
        extension_manager.set_cancelled()


    # ============================================================================
    # CUSTOMIZE: Add Dynamic Choice Commands (MUST be methods inside Extension class)
    # ============================================================================

    def _extract_credential_from_fields(self, fields: dict, credential_name: str) -> tuple:
        """Extract credential components from flattened fields dict.

        Args:
            fields: Raw fields dict with flattened credentials (dotted notation)
            credential_name: Credential field name (e.g., "uac_credential")

        Returns:
            Tuple of (url, username, password) or (None, None, None) if not found
        """
        url = fields.get(f"{credential_name}.url")
        username = fields.get(f"{credential_name}.username") or fields.get(f"{credential_name}.user")
        password = fields.get(f"{credential_name}.password")

        return url, username, password

    @dynamic_choice_command("business_service")
    def get_business_service(self, fields: dict) -> ExtensionResult:
        """Populate Business Service dropdown from UAC.

        Returns list of "[Label] | [Business Service ID]" strings.
        """
        try:
            url, username, password = self._extract_credential_from_fields(fields, "uac_credential")

            if not all([url, username, password]):
                return ExtensionResult(
                    rc=1,
                    message="Missing UAC credential fields",
                    values=[]
                )

            conn = UACConnectionHandler(url, username, password)
            try:
                response = conn.fetch_paginated("/resources/businessservice/list")

                choices = []
                for bs in response:
                    if "id" in bs and "name" in bs:
                        label = bs.get("name", "")
                        bs_id = bs.get("id", "")
                        choices.append(f"{label} | {bs_id}")

                if len(response) >= 100:
                    choices.append("... (truncated - max 100 items)")

                return ExtensionResult(
                    rc=0,
                    message="Successfully retrieved Business Services",
                    values=choices[:100]
                )
            finally:
                conn.close()
        except Exception as e:
            logger.error("Failed to fetch business services: %s", str(e))
            return ExtensionResult(
                rc=1,
                message=f"Failed to fetch Business Services: {str(e)}",
                values=[]
            )

    @dynamic_choice_command("source_object")
    def get_source_object(self, fields: dict) -> ExtensionResult:
        """Populate source object dropdown from UAC.

        Returns list of "[Label (type)] | [Stable ID]" strings.
        """
        try:
            url, username, password = self._extract_credential_from_fields(fields, "uac_credential")

            if not all([url, username, password]):
                return ExtensionResult(
                    rc=1,
                    message="Missing UAC credential fields",
                    values=[]
                )

            source_dataset_value = fields.get("source_dataset")
            if isinstance(source_dataset_value, list) and len(source_dataset_value) > 0:
                source_dataset = source_dataset_value[0]
            else:
                source_dataset = source_dataset_value

            if not source_dataset:
                return ExtensionResult(
                    rc=1,
                    message="source_dataset is required",
                    values=[]
                )

            business_service_value = fields.get("business_service")
            if isinstance(business_service_value, list) and len(business_service_value) > 0:
                business_service = business_service_value[0]
            else:
                business_service = business_service_value

            # Determine endpoint based on source_dataset
            if source_dataset == "Agents":
                endpoint = "/resources/agent/list"
                obj_type = "Agent"
                id_field = "agentid"
                name_field = "agentname"
            elif source_dataset == "Calendars":
                endpoint = "/resources/calendar/list"
                obj_type = "Calendar"
                id_field = "calendarid"
                name_field = "calendername"
            elif source_dataset == "Scripts":
                endpoint = "/resources/script/list"
                obj_type = "Script"
                id_field = "scriptid"
                name_field = "scriptname"
            elif source_dataset == "SAP/ABAP Jobs":
                endpoint = "/resources/task/list"
                obj_type = "SAP Job"
                id_field = "taskid"
                name_field = "taskname"
            else:
                return ExtensionResult(
                    rc=1,
                    message=f"Unknown source_dataset: {source_dataset}",
                    values=[]
                )

            conn = UACConnectionHandler(url, username, password)
            try:
                # For tasks, use POST with filter
                if source_dataset == "SAP/ABAP Jobs":
                    payload = {"filter": {"tasktype": "taskSap"}}
                    response = conn.post(endpoint, payload)
                    objects = response.get("data", []) if isinstance(response, dict) else response
                else:
                    objects = conn.fetch_paginated(endpoint)

                # Filter by business service if provided
                if business_service:
                    bs_id = business_service.split(" | ")[-1] if " | " in business_service else business_service
                    objects = [obj for obj in objects if obj.get("businessserviceid") == bs_id]

                choices = []
                for obj in objects:
                    label = obj.get(name_field, "")
                    obj_id = obj.get(id_field, "")
                    choices.append(f"{label} ({obj_type}) | {obj_id}")

                if len(objects) >= 100:
                    choices.append("... (truncated - max 100 items)")

                return ExtensionResult(
                    rc=0,
                    message="Successfully retrieved source objects",
                    values=choices[:100]
                )
            finally:
                conn.close()
        except Exception as e:
            logger.error("Failed to fetch source objects: %s", str(e))
            return ExtensionResult(
                rc=1,
                message=f"Failed to fetch source objects: {str(e)}",
                values=[]
            )

    @dynamic_choice_command("customer_table")
    def get_customer_table(self, fields: dict) -> ExtensionResult:
        """Populate customer table dropdown from ServiceNow.

        Returns list of "[Table Label (technical name)]" strings.
        """
        try:
            url, username, password = self._extract_credential_from_fields(fields, "servicenow_credential")

            if not all([url, username, password]):
                return ExtensionResult(
                    rc=1,
                    message="Missing ServiceNow credential fields",
                    values=[]
                )

            conn = ServiceNowConnectionHandler(url, username, password)
            try:
                response = conn.get(
                    "sys_db_object",
                    query="nameSTARTSWITHcustomer ORnameSTARTSWITHaccount",
                    limit=100
                )

                tables = response.get("result", []) if isinstance(response, dict) else response

                choices = []
                for table in tables:
                    label = table.get("label", "")
                    name = table.get("name", "")
                    choices.append(f"{label} ({name})")

                return ExtensionResult(
                    rc=0,
                    message="Successfully retrieved customer tables",
                    values=choices
                )
            finally:
                conn.close()
        except Exception as e:
            logger.error("Failed to fetch customer tables: %s", str(e))
            return ExtensionResult(
                rc=1,
                message=f"Failed to fetch customer tables: {str(e)}",
                values=[]
            )

    @dynamic_choice_command("target_fields")
    def get_target_fields(self, fields: dict) -> ExtensionResult:
        """Populate target fields dropdown from selected customer table.

        Returns list of "[Field Label (type)] | [field_name]" strings.
        """
        try:
            url, username, password = self._extract_credential_from_fields(fields, "servicenow_credential")

            if not all([url, username, password]):
                return ExtensionResult(
                    rc=1,
                    message="Missing ServiceNow credential fields",
                    values=[]
                )

            customer_table_value = fields.get("customer_table")
            if isinstance(customer_table_value, list) and len(customer_table_value) > 0:
                customer_table_str = customer_table_value[0]
            else:
                customer_table_str = customer_table_value

            if not customer_table_str:
                return ExtensionResult(
                    rc=1,
                    message="customer_table is required",
                    values=[]
                )

            # Extract technical name from "[Label (technical_name)]"
            if "(" in customer_table_str and ")" in customer_table_str:
                customer_table = customer_table_str.split("(")[1].split(")")[0]
            else:
                customer_table = customer_table_str

            conn = ServiceNowConnectionHandler(url, username, password)
            try:
                response = conn.get(
                    "sys_dictionary",
                    query=f"name={customer_table}",
                    limit=200
                )

                fields_list = response.get("result", []) if isinstance(response, dict) else response

                choices = []
                for field in fields_list:
                    fname = field.get("element", "")
                    label = field.get("column_label", "")
                    ftype = field.get("internal_type", "String")

                    # Skip system fields
                    if fname.startswith("sys_") or fname.startswith("internal_"):
                        continue

                    choices.append(f"{label} ({ftype}) | {fname}")

                return ExtensionResult(
                    rc=0,
                    message="Successfully retrieved target fields",
                    values=choices[:100]
                )
            finally:
                conn.close()
        except Exception as e:
            logger.error("Failed to fetch target fields: %s", str(e))
            return ExtensionResult(
                rc=1,
                message=f"Failed to fetch target fields: {str(e)}",
                values=[]
            )

    @dynamic_choice_command("decision_table")
    def get_decision_table(self, fields: dict) -> ExtensionResult:
        """Populate Decision Table dropdown from ServiceNow.

        Returns list of "[Table Name] | [sys_id]" strings.
        """
        try:
            url, username, password = self._extract_credential_from_fields(fields, "servicenow_credential")

            if not all([url, username, password]):
                return ExtensionResult(
                    rc=1,
                    message="Missing ServiceNow credential fields",
                    values=[]
                )

            conn = ServiceNowConnectionHandler(url, username, password)
            try:
                response = conn.get(
                    "sn_decision_table",
                    limit=100
                )

                tables = response.get("result", []) if isinstance(response, dict) else response

                choices = []
                for table in tables:
                    name = table.get("name", "")
                    sys_id = table.get("sys_id", "")
                    choices.append(f"{name} | {sys_id}")

                if len(tables) >= 100:
                    choices.append("... (truncated - max 100 items)")

                return ExtensionResult(
                    rc=0,
                    message="Successfully retrieved Decision Tables",
                    values=choices[:100]
                )
            finally:
                conn.close()
        except Exception as e:
            logger.error("Failed to fetch Decision Tables: %s", str(e))
            return ExtensionResult(
                rc=1,
                message=f"Failed to fetch Decision Tables: {str(e)}",
                values=[]
            )

    @dynamic_choice_command("decision_inputs")
    def get_decision_inputs(self, fields: dict) -> ExtensionResult:
        """Populate Decision Table input fields dropdown.

        Returns list of "[Field Name (type)] | [Field sys_id]" strings.
        """
        try:
            url, username, password = self._extract_credential_from_fields(fields, "servicenow_credential")

            if not all([url, username, password]):
                return ExtensionResult(
                    rc=1,
                    message="Missing ServiceNow credential fields",
                    values=[]
                )

            decision_table_value = fields.get("decision_table")
            if isinstance(decision_table_value, list) and len(decision_table_value) > 0:
                decision_table_str = decision_table_value[0]
            else:
                decision_table_str = decision_table_value

            if not decision_table_str:
                return ExtensionResult(
                    rc=1,
                    message="decision_table is required",
                    values=[]
                )

            # Extract sys_id from "[Name] | [sys_id]"
            if " | " in decision_table_str:
                dt_sys_id = decision_table_str.split(" | ")[-1]
            else:
                dt_sys_id = decision_table_str

            conn = ServiceNowConnectionHandler(url, username, password)
            try:
                response = conn.get(
                    "sn_decision_table_input",
                    query=f"decision_table={dt_sys_id}",
                    limit=100
                )

                fields_list = response.get("result", []) if isinstance(response, dict) else response

                choices = []
                for field in fields_list:
                    fname = field.get("name", "")
                    sys_id = field.get("sys_id", "")
                    ftype = field.get("type", "String")
                    choices.append(f"{fname} ({ftype}) | {sys_id}")

                return ExtensionResult(
                    rc=0,
                    message="Successfully retrieved Decision Table input fields",
                    values=choices[:50]
                )
            finally:
                conn.close()
        except Exception as e:
            logger.error("Failed to fetch Decision Table input fields: %s", str(e))
            return ExtensionResult(
                rc=1,
                message=f"Failed to fetch Decision Table input fields: {str(e)}",
                values=[]
            )

    @dynamic_choice_command("decision_results")
    def get_decision_results(self, fields: dict) -> ExtensionResult:
        """Populate Decision Table result fields dropdown.

        Returns list of "[Field Name (type)] | [Field sys_id]" strings.
        """
        try:
            url, username, password = self._extract_credential_from_fields(fields, "servicenow_credential")

            if not all([url, username, password]):
                return ExtensionResult(
                    rc=1,
                    message="Missing ServiceNow credential fields",
                    values=[]
                )

            decision_table_value = fields.get("decision_table")
            if isinstance(decision_table_value, list) and len(decision_table_value) > 0:
                decision_table_str = decision_table_value[0]
            else:
                decision_table_str = decision_table_value

            if not decision_table_str:
                return ExtensionResult(
                    rc=1,
                    message="decision_table is required",
                    values=[]
                )

            # Extract sys_id from "[Name] | [sys_id]"
            if " | " in decision_table_str:
                dt_sys_id = decision_table_str.split(" | ")[-1]
            else:
                dt_sys_id = decision_table_str

            conn = ServiceNowConnectionHandler(url, username, password)
            try:
                response = conn.get(
                    "sn_decision_table_result",
                    query=f"decision_table={dt_sys_id}",
                    limit=100
                )

                fields_list = response.get("result", []) if isinstance(response, dict) else response

                choices = []
                for field in fields_list:
                    fname = field.get("name", "")
                    sys_id = field.get("sys_id", "")
                    ftype = field.get("type", "String")
                    choices.append(f"{fname} ({ftype}) | {sys_id}")

                return ExtensionResult(
                    rc=0,
                    message="Successfully retrieved Decision Table result fields",
                    values=choices[:50]
                )
            finally:
                conn.close()
        except Exception as e:
            logger.error("Failed to fetch Decision Table result fields: %s", str(e))
            return ExtensionResult(
                rc=1,
                message=f"Failed to fetch Decision Table result fields: {str(e)}",
                values=[]
            )

    @dynamic_choice_command("customer_record")
    def get_customer_record(self, fields: dict) -> ExtensionResult:
        """Populate customer record dropdown from ServiceNow.

        Returns list of "[Account Name] | [sys_id]" strings.
        """
        try:
            url, username, password = self._extract_credential_from_fields(fields, "servicenow_credential")

            if not all([url, username, password]):
                return ExtensionResult(
                    rc=1,
                    message="Missing ServiceNow credential fields",
                    values=[]
                )

            customer_table_value = fields.get("customer_table")
            if isinstance(customer_table_value, list) and len(customer_table_value) > 0:
                customer_table_str = customer_table_value[0]
            else:
                customer_table_str = customer_table_value

            if not customer_table_str:
                return ExtensionResult(
                    rc=1,
                    message="customer_table is required",
                    values=[]
                )

            # Extract technical name from "[Label (technical_name)]"
            if "(" in customer_table_str and ")" in customer_table_str:
                customer_table = customer_table_str.split("(")[1].split(")")[0]
            else:
                customer_table = customer_table_str

            conn = ServiceNowConnectionHandler(url, username, password)
            try:
                response = conn.get(
                    customer_table,
                    limit=100
                )

                records = response.get("result", []) if isinstance(response, dict) else response

                choices = []
                for record in records:
                    name = record.get("name", "")
                    sys_id = record.get("sys_id", "")
                    choices.append(f"{name} | {sys_id}")

                if len(records) >= 100:
                    choices.append("... (truncated - max 100 items)")

                return ExtensionResult(
                    rc=0,
                    message="Successfully retrieved customer records",
                    values=choices[:100]
                )
            finally:
                conn.close()
        except Exception as e:
            logger.error("Failed to fetch customer records: %s", str(e))
            return ExtensionResult(
                rc=1,
                message=f"Failed to fetch customer records: {str(e)}",
                values=[]
            )

    # Example dynamic choice command:
    #
    # from universal_extension.deco.choice import dynamic_choice_command
    #
    # @dynamic_choice_command("field_name")
    # def get_resources(self, fields: dict) -> ExtensionResult:
    #     """
    #     Dynamic choice function for resource selection.
    #
    #     Called by UAC when user opens the dropdown for 'field_name'.
    #     The field_name in decorator MUST match the field's "name" property in template.json.
    #     The field in template.json MUST have "choiceDynamic": true.
    #
    #     Args:
    #         fields: Current field values (for dependencies)
    #
    #     Returns:
    #         ExtensionResult with values parameter containing list of choices.
    #         Parameters: rc (int), message (str), values (List[str])
    #     """
    #     try:
    #         logger.info("Fetching available resources")
    #
    #         # May depend on other fields (extract as list)
    #         filter_type = fields.get("filter_type", [""])[0] if fields.get("filter_type") else None
    #
    #         # Query resources
    #         resources = ["resource1", "resource2", "resource3"]
    #
    #         logger.info("Found %d resources", len(resources))
    #         return ExtensionResult(
    #             rc=0,
    #             message="Successfully retrieved resources",
    #             values=resources
    #         )
    #
    #     except Exception as e:
    #         logger.error("Failed to fetch resources: %s", str(e))
    #         return ExtensionResult(
    #             rc=1,
    #             message=f"Failed to fetch resources: {str(e)}",
    #             values=[]
    #         )


    # ============================================================================
    # CUSTOMIZE: Add Extension Commands (MUST be methods inside Extension class)
    # ============================================================================

    # Example extension command:
    #
    # from universal_extension.deco.command import dynamic_command
    #
    # @dynamic_command(command_name="validate_configuration")
    # def validate_configuration(self, fields: dict) -> ExtensionResult:
    #     """
    #     Command to validate extension configuration.
    #
    #     Can be called independently from UAC without executing the extension.
    #     The command_name in decorator is used to invoke this command.
    #
    #     Args:
    #         fields: Current field values to validate
    #
    #     Returns:
    #         ExtensionResult indicating validation success/failure
    #     """
    #     try:
    #         logger.info("Validating configuration...")
    #
    #         # Extract and validate fields
    #         timeout = fields.get("timeout", 30)
    #         if timeout < 5:
    #             return ExtensionResult(
    #                 rc=1,
    #                 message="Timeout must be at least 5 seconds",
    #                 output=False,
    #                 output_data=None,
    #                 output_name=None
    #             )
    #
    #         logger.info("Configuration validated successfully")
    #         return ExtensionResult(
    #             rc=0,
    #             message="Configuration is valid",
    #             output=False,
    #             output_data=None,
    #             output_name=None
    #         )
    #
    #     except Exception as e:
    #         logger.error("Validation failed: %s", str(e))
    #         return ExtensionResult(
    #             rc=1,
    #             message=f"Validation error: {str(e)}",
    #             output=False,
    #             output_data=None,
    #             output_name=None
    #         )
    #
    # Example extension command with output data:
    #
    # @dynamic_command(command_name="get_system_info")
    # def get_system_info(self, _fields: dict) -> ExtensionResult:
    #     """Return extension and system information."""
    #     try:
    #         info = {
    #             "extension_name": EXTENSION_NAME,
    #             "extension_version": EXTENSION_VERSION,
    #             "python_version": "3.11"
    #         }
    #         return ExtensionResult(
    #             rc=0,
    #             message="System information retrieved",
    #             output=True,
    #             output_data=json.dumps(info, indent=2),
    #             output_name="system_info"
    #         )
    #     except Exception as e:
    #         return ExtensionResult(
    #             rc=1,
    #             message=f"Error: {str(e)}",
    #             output=False,
    #             output_data=None,
    #             output_name=None
    #         )
