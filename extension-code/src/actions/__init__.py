"""Actions module - Business logic implementations."""

from actions.output import ActionOutput
from actions.validate_configuration import ValidateConfiguration
from actions.preview import Preview
from actions.synchronize import Synchronize
from manager import ExtensionManager

extension_manager = ExtensionManager()

ACTION_MAPPER = {
    "Validate Configuration": lambda input_data: ValidateConfiguration(input_data).execute(),
    "Preview": lambda input_data: Preview(input_data).execute(),
    "Synchronize": lambda input_data: Synchronize(input_data).execute(),
}
