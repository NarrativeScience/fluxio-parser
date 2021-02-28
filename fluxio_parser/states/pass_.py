"""Contains the class that represents the AWS Step Functions Pass State"""
import ast
import json
import re
from typing import Any, Dict

import astor

from ..constants import INVALID_RESULT_PATH_PATTERN, RESERVED_INPUT_DATA_KEYS
from ..exceptions import assert_supported_operation, UnsupportedOperation
from ..util import convert_input_data_ref
from .base import State


class PassState(State):
    """Pass state

    A Pass state updates the input data dictionary with static values. The static
    values must be JSON-serializeable. Pass states are generated by setting a key on or
    updating the ``data`` dict in an .sfn file.

    See: https://docs.aws.amazon.com/step-functions/latest/dg/amazon-states-language-pass-state.html

    For example::

        data["foo"] = {"bar": 123}

    resolves to::

        {
            "Type": "Pass",
            "Result": {"bar": 123},
            "ResultPath": "$['foo']"
        }
    """

    def shape(self) -> None:
        """Shape the graph for this Pass state.

        The main purpose here is to remove the representations of ``pass`` from the
        graph. We added those in the ScriptTransformer and will now remove them. The
        exception is when ``pass`` is used as the end state in a state machine (edge
        count is 0). This means it was probably used as a catch handler and should be
        kept.
        """
        if not isinstance(self.ast_node, ast.Pass) or len(self.edges) == 0:
            return

        # To shape a `pass` state, point the upstream state to the downstream state
        edges_to_remove = []
        for next_state in self.state_graph[self]:
            for edge in list(self.state_graph.in_edges(self)):
                attrs = self.state_graph.edges[edge]
                edges_to_remove.append(edge)
                from_state, _ = edge
                self.state_graph.add_edge(from_state, next_state, **attrs)

        for edge in edges_to_remove:
            self.state_graph.remove_edge(*edge)

        self.state_graph.remove_node(self)

    def _parse_result(self) -> Any:
        """Parse the result value from the AST node

        The result value can be anything that is JSON-serializeable.

        Returns:
            result value
        """
        if isinstance(self.ast_node, ast.Assign):
            source = astor.to_source(self.ast_node.value).strip()
        elif hasattr(self.ast_node, "value"):
            source = astor.to_source(self.ast_node.value.args[0]).strip()
        else:
            source = "{}"

        # Parse dict from source code and check that it's plain JSON
        try:
            result = ast.literal_eval(source)
            json.dumps(result)
        except Exception:
            raise UnsupportedOperation(
                "Only JSON-serializeable values can be used to update the data object",
                self.ast_node,
            )

        return result

    def _parse_result_path(self) -> str:
        """Parse the result path from the AST node.

        The result path is where the result value will be inserted into the data object.

        Returns:
            result path string
        """
        if isinstance(self.ast_node, ast.Assign):
            result_path = convert_input_data_ref(self.ast_node.targets[0])
            assert_supported_operation(
                re.search(INVALID_RESULT_PATH_PATTERN, result_path) is None,
                "Task result path is invalid. Check that it does not contain reserved"
                f" keys: {', '.join(RESERVED_INPUT_DATA_KEYS)}",
                self.ast_node,
            )
            return result_path

        return "$"

    def to_dict(self) -> Dict:
        """Return a serialized representation of the Choice state."""
        data = {"Type": "Pass"}
        if not isinstance(self.ast_node, ast.Pass):
            data["Result"] = self._parse_result()
            data["ResultPath"] = self._parse_result_path()
        self._set_end_or_next(data)
        return data
