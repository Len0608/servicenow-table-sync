"""Actions module - Business logic implementations."""

from actions.output import ActionOutput
from manager import ExtensionManager
extension_manager = ExtensionManager()

# Import your action classes here
# from actions.action_name import ActionName

# Map action names to lambdas that instantiate the class and call execute()
ACTION_MAPPER = {
    # "action_name": lambda input_data: ActionName(input_data).execute(),
}
