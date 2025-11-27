"""Condition evaluator for routing rules."""
from typing import Any


class ConditionEvaluator:
    """Evaluates conditions for routing rules.

    Supports various operators for flexible rule matching:
    - Comparison: <, >, <=, >=, =, !=
    - Containment: contains, not_contains
    - Membership: in, not_in
    - Pattern: matches (regex)
    """

    def evaluate(self, conditions: dict[str, Any], review_data: dict[str, Any]) -> bool:
        """Evaluate conditions against review data.

        Args:
            conditions: Dictionary of conditions to evaluate
            review_data: Review data to evaluate against

        Returns:
            True if all conditions match, False otherwise

        Examples:
            >>> evaluator = ConditionEvaluator()
            >>> conditions = {
            ...     "task_type": {"operator": "=", "value": "payment"},
            ...     "confidence_score": {"operator": "<", "value": 0.8}
            ... }
            >>> review = {"task_type": "payment", "confidence_score": 0.7}
            >>> evaluator.evaluate(conditions, review)
            True
        """
        # Handle empty conditions (match all)
        if not conditions:
            return True

        # Special handling for logical operators
        if "and" in conditions:
            return all(
                self.evaluate(cond, review_data) for cond in conditions["and"]
            )

        if "or" in conditions:
            return any(
                self.evaluate(cond, review_data) for cond in conditions["or"]
            )

        # Evaluate each condition
        for field, condition_spec in conditions.items():
            if field in ("and", "or"):
                continue

            if not self._evaluate_single_condition(field, condition_spec, review_data):
                return False

        return True

    def _evaluate_single_condition(
        self, field: str, condition_spec: dict[str, Any], review_data: dict[str, Any]
    ) -> bool:
        """Evaluate a single condition.

        Args:
            field: Field name to check
            condition_spec: Condition specification with operator and value
            review_data: Review data

        Returns:
            True if condition matches, False otherwise
        """
        # Get the actual value from review data
        actual_value = review_data.get(field)

        # Handle nested fields (e.g., "metadata.priority")
        if "." in field:
            actual_value = self._get_nested_value(field, review_data)

        # If it's a simple value (not a dict), treat as equality
        if not isinstance(condition_spec, dict):
            return actual_value == condition_spec

        operator = condition_spec.get("operator", "=")
        expected_value = condition_spec.get("value")

        return self._apply_operator(operator, actual_value, expected_value)

    def _get_nested_value(self, field_path: str, data: dict[str, Any]) -> Any:
        """Get value from nested dictionary using dot notation.

        Args:
            field_path: Dot-separated field path (e.g., "metadata.priority")
            data: Data dictionary

        Returns:
            Value at the path, or None if not found
        """
        parts = field_path.split(".")
        value = data

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None

        return value

    def _apply_operator(self, operator: str, actual: Any, expected: Any) -> bool:
        """Apply an operator to compare values.

        Args:
            operator: Operator name
            actual: Actual value from review
            expected: Expected value from condition

        Returns:
            True if comparison passes, False otherwise
        """
        if actual is None:
            return False

        # Comparison operators
        if operator == "=":
            return actual == expected
        elif operator == "!=":
            return actual != expected
        elif operator == "<":
            return actual < expected
        elif operator == ">":
            return actual > expected
        elif operator == "<=":
            return actual <= expected
        elif operator == ">=":
            return actual >= expected

        # String operators
        elif operator == "contains":
            return expected in str(actual)
        elif operator == "not_contains":
            return expected not in str(actual)

        # List operators
        elif operator == "in":
            return actual in expected
        elif operator == "not_in":
            return actual not in expected

        # Pattern matching
        elif operator == "matches":
            import re
            return bool(re.match(expected, str(actual)))

        else:
            raise ValueError(f"Unknown operator: {operator}")
