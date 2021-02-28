"""Contains map of resource decorators for configuring state machines and tasks"""
import ast
from typing import Any

from .exceptions import assert_supported_operation
from .util import CallableOption, GET_VALUE_MAP


def get_subscribe_status(node: Any) -> None:
    """Get the subscribe status option value.

    Args:
        node: AST node of the keyword value

    Raises:
        :py:exc:`UnsupportedOperation` if the value isn't valid

    """
    value = GET_VALUE_MAP[str](node)
    assert_supported_operation(
        value in {"success", "failure"},
        f"Status must be one of success|failure. Provided: {value}",
        node,
    )
    return value


# Map of resource decorator configurations. Each decorator configuration contains keys:
#   * **<resource decorator name>** -- dict with keys:
#     * **max_count** -- Optional. The maximum number of decorators that can be applied
#       to the function. Default is no limit.
#     * **options** -- dict of option name to CallableOption
# option name to option schema
RESOURCE_DECORATOR_MAP = {
    # export decorator is used to indicate that the state machine should get its own
    # CloudFormation template and supporting infrastructure.
    # e.g. @export()
    "export": {
        "max_count": 1,
        "options": {
            "enabled": CallableOption(
                value_type=ast.Name,
                value_type_label="boolean",
                get_value=GET_VALUE_MAP[bool],
                default_value=True,
            )
        },
    },
    # schedule decorator is used to create a CloudWatch event rule. This can be used to
    # decorate a state machine function (``main``)
    # e.g. @schedule(expression="cron(0 12 * * ? *)")
    "schedule": {
        "max_count": 1,
        "options": {
            "expression": CallableOption(
                value_type=ast.Str,
                value_type_label="string",
                get_value=GET_VALUE_MAP[str],
                default_value=None,
            ),
            "input_data": CallableOption(
                value_type=ast.Dict,
                value_type_label="dict",
                get_value=GET_VALUE_MAP[dict],
                default_value=None,
            ),
        },
    },
    # subscribe decorator is used to trigger a state machine execution when a message
    # is published to a certain SNS topic. This can be used to decorate a state machine
    # function.
    # e.g. @subscribe(project="other-project")
    # e.g. @subscribe(topic_arn_import_value="${Environment}-topic")
    "subscribe": {
        "options": {
            # The topic ARN import value can be a string with or without CloudFormation
            # variable substitutions since it will be fed to ``!Sub`` before
            # ``!ImportValue``
            "topic_arn_import_value": CallableOption(
                value_type=ast.Str,
                value_type_label="string",
                get_value=GET_VALUE_MAP[str],
            ),
            # This project needs to already have been deployed since we'll use
            # ImportValue to reference the SNS topics.
            "project": CallableOption(
                value_type=ast.Str,
                value_type_label="string",
                get_value=GET_VALUE_MAP[str],
            ),
            "state_machine": CallableOption(
                value_type=ast.Str,
                value_type_label="string",
                get_value=GET_VALUE_MAP[str],
                default_value="main",
            ),
            "status": CallableOption(
                value_type=ast.Str,
                value_type_label="string",
                get_value=get_subscribe_status,
                default_value="success",
            ),
        }
    },
}
