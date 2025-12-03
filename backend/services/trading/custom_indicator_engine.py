"""
Custom Indicator Engine

This module provides a secure JSON-based custom indicator engine that allows users
to define custom indicators without uploading Python code. Uses recursive formula
evaluation with strict validation and safety checks.
"""

from typing import Dict, List, Optional, Set, Any
import pandas as pd


class CustomIndicatorError(Exception):
    """Base exception for custom indicator errors"""
    def __init__(self, error_code: str, message: str, rule_name: Optional[str] = None):
        self.error_code = error_code
        self.message = message
        self.rule_name = rule_name
        super().__init__(self.format_error())
    
    def format_error(self) -> str:
        """Format error message with code and rule name"""
        if self.rule_name:
            return f"[{self.error_code}] {self.message} (rule: {self.rule_name})"
        return f"[{self.error_code}] {self.message}"


class CustomIndicatorEngine:
    """
    Engine for calculating custom indicators from JSON-based rule definitions.
    
    Provides secure, code-free custom indicator calculation using:
    - JSON rule parsing and validation
    - Recursive formula evaluation
    - Circular dependency detection
    - Type-safe numeric operations
    
    Example:
        >>> engine = CustomIndicatorEngine(df, available_indicators)
        >>> rule = {
        ...     "name": "price_momentum",
        ...     "type": "composite",
        ...     "formula": {
        ...         "operator": "*",
        ...         "left": {"indicator": "rsi"},
        ...         "right": {"value": 0.01}
        ...     }
        ... }
        >>> engine.add_rule(rule)
        >>> result = engine.calculate("price_momentum")
    """
    
    # Whitelist of allowed operators
    ALLOWED_OPERATORS = ['+', '-', '*', '/']
    
    # Valid indicator types
    VALID_TYPES = ['composite', 'derived']
    
    def __init__(self, df: pd.DataFrame, available_indicators: Dict[str, pd.Series]):
        """
        Initialize the custom indicator engine.
        
        Args:
            df: DataFrame with OHLCV data (used for index alignment)
            available_indicators: Dictionary mapping indicator names to pandas Series
                                 (includes OHLCV data and calculated indicators)
        """
        self.df = df
        self.available_indicators = available_indicators.copy()
        self.custom_indicators: Dict[str, Dict] = {}
        self.calculation_cache: Dict[str, pd.Series] = {}
    
    def add_rule(self, rule: Dict[str, Any]) -> None:
        """
        Add a custom indicator rule after validation.
        
        Args:
            rule: JSON rule definition with name, type, and formula
            
        Raises:
            CustomIndicatorError: If rule validation fails
        """
        # Validate rule structure
        self._validate_rule_structure(rule)
        
        # Extract rule name
        name = rule['name']
        
        # Check for duplicate names
        if name in self.custom_indicators:
            raise CustomIndicatorError(
                'DUPLICATE_INDICATOR_NAME',
                f"Custom indicator '{name}' already exists",
                name
            )
        
        # Check if name conflicts with existing indicators
        if name in self.available_indicators:
            raise CustomIndicatorError(
                'INDICATOR_NAME_CONFLICT',
                f"Name '{name}' conflicts with existing indicator",
                name
            )
        
        # Validate formula structure
        self._validate_formula(rule['formula'], name)
        
        # Store the rule
        self.custom_indicators[name] = rule
    
    def calculate(self, name: str) -> pd.Series:
        """
        Calculate a custom indicator by name.
        
        Args:
            name: Name of the custom indicator to calculate
            
        Returns:
            pandas Series with calculated values
            
        Raises:
            CustomIndicatorError: If indicator doesn't exist or calculation fails
        """
        # Check if indicator exists
        if name not in self.custom_indicators:
            raise CustomIndicatorError(
                'INDICATOR_NOT_FOUND',
                f"Custom indicator '{name}' not found",
                name
            )
        
        # Check cache first
        if name in self.calculation_cache:
            return self.calculation_cache[name]
        
        # Check for circular dependencies before calculation
        self._check_circular_dependencies(name, set())
        
        # Get the rule
        rule = self.custom_indicators[name]
        
        # Evaluate the formula
        try:
            result = self._evaluate_formula(rule['formula'], name)
        except Exception as e:
            if isinstance(e, CustomIndicatorError):
                raise
            raise CustomIndicatorError(
                'CALCULATION_ERROR',
                f"Error calculating indicator: {str(e)}",
                name
            )
        
        # Validate result is a pandas Series
        if not isinstance(result, pd.Series):
            raise CustomIndicatorError(
                'INVALID_RESULT_TYPE',
                f"Calculation must return pandas Series, got {type(result)}",
                name
            )
        
        # Cache the result
        self.calculation_cache[name] = result
        
        return result
    
    def _validate_rule_structure(self, rule: Dict[str, Any]) -> None:
        """
        Validate that rule has required fields with correct types.
        
        Args:
            rule: Rule dictionary to validate
            
        Raises:
            CustomIndicatorError: If validation fails
        """
        # Check if rule is a dictionary
        if not isinstance(rule, dict):
            raise CustomIndicatorError(
                'INVALID_RULE_STRUCTURE',
                f"Rule must be a dictionary, got {type(rule)}"
            )
        
        # Check required fields
        required_fields = ['name', 'type', 'formula']
        for field in required_fields:
            if field not in rule:
                raise CustomIndicatorError(
                    'INVALID_RULE_STRUCTURE',
                    f"Missing required field: {field}",
                    rule.get('name')
                )
        
        # Validate name
        name = rule['name']
        if not isinstance(name, str) or not name.strip():
            raise CustomIndicatorError(
                'INVALID_RULE_STRUCTURE',
                "Field 'name' must be a non-empty string",
                name
            )
        
        # Validate type
        indicator_type = rule['type']
        if indicator_type not in self.VALID_TYPES:
            raise CustomIndicatorError(
                'INVALID_INDICATOR_TYPE',
                f"Type must be one of {self.VALID_TYPES}, got '{indicator_type}'",
                name
            )
        
        # Validate formula is a dictionary
        if not isinstance(rule['formula'], dict):
            raise CustomIndicatorError(
                'INVALID_RULE_STRUCTURE',
                f"Field 'formula' must be a dictionary, got {type(rule['formula'])}",
                name
            )
    
    def _validate_formula(self, formula: Dict[str, Any], rule_name: str) -> None:
        """
        Recursively validate formula structure.
        
        Args:
            formula: Formula dictionary to validate
            rule_name: Name of the rule (for error messages)
            
        Raises:
            CustomIndicatorError: If validation fails
        """
        # Check if formula is a dictionary
        if not isinstance(formula, dict):
            raise CustomIndicatorError(
                'INVALID_FORMULA_STRUCTURE',
                f"Formula must be a dictionary, got {type(formula)}",
                rule_name
            )
        
        # Base case: indicator reference
        if 'indicator' in formula:
            indicator_name = formula['indicator']
            
            # Validate indicator name is a string
            if not isinstance(indicator_name, str):
                raise CustomIndicatorError(
                    'INVALID_OPERAND_TYPE',
                    f"Indicator name must be a string, got {type(indicator_name)}",
                    rule_name
                )
            
            # Note: We don't validate existence here because custom indicators
            # might reference other custom indicators defined later
            # Existence will be checked during calculation
            
            return
        
        # Base case: constant value
        if 'value' in formula:
            value = formula['value']
            
            # Validate value is numeric
            if not isinstance(value, (int, float)):
                raise CustomIndicatorError(
                    'INVALID_OPERAND_TYPE',
                    f"Value must be numeric, got {type(value)}",
                    rule_name
                )
            
            # Validate value is finite
            if not pd.isna(value) and not (-float('inf') < value < float('inf')):
                raise CustomIndicatorError(
                    'INVALID_OPERAND_VALUE',
                    f"Value must be finite, got {value}",
                    rule_name
                )
            
            return
        
        # Recursive case: operator with left and right operands
        if 'operator' not in formula:
            raise CustomIndicatorError(
                'INVALID_FORMULA_STRUCTURE',
                "Formula must have 'operator', 'indicator', or 'value' field",
                rule_name
            )
        
        operator = formula['operator']
        
        # Validate operator
        if operator not in self.ALLOWED_OPERATORS:
            raise CustomIndicatorError(
                'INVALID_OPERATOR',
                f"Operator '{operator}' is not allowed. Use one of: {', '.join(self.ALLOWED_OPERATORS)}",
                rule_name
            )
        
        # Validate left and right operands exist
        if 'left' not in formula:
            raise CustomIndicatorError(
                'INVALID_FORMULA_STRUCTURE',
                "Operator formula must have 'left' operand",
                rule_name
            )
        
        if 'right' not in formula:
            raise CustomIndicatorError(
                'INVALID_FORMULA_STRUCTURE',
                "Operator formula must have 'right' operand",
                rule_name
            )
        
        # Recursively validate operands
        self._validate_formula(formula['left'], rule_name)
        self._validate_formula(formula['right'], rule_name)
    
    def _check_circular_dependencies(
        self, 
        name: str, 
        visited: Set[str],
        path: Optional[List[str]] = None
    ) -> None:
        """
        Check for circular dependencies in custom indicator references.
        
        Args:
            name: Name of the indicator to check
            visited: Set of indicators already visited in this path
            path: List of indicator names in the current dependency path
            
        Raises:
            CustomIndicatorError: If circular dependency is detected
        """
        if path is None:
            path = []
        
        # Check if we've seen this indicator in the current path
        if name in visited:
            # Build circular path string
            cycle_start = path.index(name)
            cycle = ' → '.join(path[cycle_start:] + [name])
            raise CustomIndicatorError(
                'CIRCULAR_DEPENDENCY',
                f"Circular dependency detected: {cycle}",
                name
            )
        
        # If this is a custom indicator, check its dependencies
        if name in self.custom_indicators:
            rule = self.custom_indicators[name]
            visited.add(name)
            path.append(name)
            
            # Get all indicator references in the formula
            referenced_indicators = self._get_referenced_indicators(rule['formula'])
            
            # Recursively check each referenced indicator
            for ref_name in referenced_indicators:
                self._check_circular_dependencies(ref_name, visited.copy(), path.copy())
    
    def _get_referenced_indicators(self, formula: Dict[str, Any]) -> List[str]:
        """
        Extract all indicator references from a formula.
        
        Args:
            formula: Formula dictionary
            
        Returns:
            List of indicator names referenced in the formula
        """
        references = []
        
        # Base case: indicator reference
        if 'indicator' in formula:
            references.append(formula['indicator'])
            return references
        
        # Base case: constant value
        if 'value' in formula:
            return references
        
        # Recursive case: operator with left and right
        if 'operator' in formula:
            references.extend(self._get_referenced_indicators(formula['left']))
            references.extend(self._get_referenced_indicators(formula['right']))
        
        return references
    
    def _evaluate_formula(self, formula: Dict[str, Any], rule_name: str) -> pd.Series:
        """
        Recursively evaluate a formula to produce a pandas Series.
        
        Args:
            formula: Formula dictionary to evaluate
            rule_name: Name of the rule (for error messages)
            
        Returns:
            pandas Series with calculated values
            
        Raises:
            CustomIndicatorError: If evaluation fails
        """
        # Base case: indicator reference
        if 'indicator' in formula:
            indicator_name = formula['indicator']
            
            # Check if indicator exists in available indicators
            if indicator_name in self.available_indicators:
                return self.available_indicators[indicator_name]
            
            # Check if it's a custom indicator
            if indicator_name in self.custom_indicators:
                # Recursively calculate custom indicator
                return self.calculate(indicator_name)
            
            # Indicator not found
            raise CustomIndicatorError(
                'INDICATOR_NOT_FOUND',
                f"Referenced indicator '{indicator_name}' does not exist",
                rule_name
            )
        
        # Base case: constant value
        if 'value' in formula:
            value = formula['value']
            # Create Series with constant value, aligned with DataFrame index
            return pd.Series([value] * len(self.df), index=self.df.index, dtype=float)
        
        # Recursive case: operator with left and right operands
        operator = formula['operator']
        
        # Evaluate left and right operands
        left = self._evaluate_formula(formula['left'], rule_name)
        right = self._evaluate_formula(formula['right'], rule_name)
        
        # Ensure both are pandas Series
        if not isinstance(left, pd.Series) or not isinstance(right, pd.Series):
            raise CustomIndicatorError(
                'INVALID_OPERAND_TYPE',
                "Operands must evaluate to pandas Series",
                rule_name
            )
        
        # Apply operator
        try:
            if operator == '+':
                result = left + right
            elif operator == '-':
                result = left - right
            elif operator == '*':
                result = left * right
            elif operator == '/':
                # Division by zero will produce NaN (handled gracefully)
                result = left / right
            else:
                # Should never reach here due to validation
                raise CustomIndicatorError(
                    'INVALID_OPERATOR',
                    f"Unsupported operator: {operator}",
                    rule_name
                )
        except Exception as e:
            raise CustomIndicatorError(
                'CALCULATION_ERROR',
                f"Error applying operator '{operator}': {str(e)}",
                rule_name
            )
        
        return result
    
    def get_custom_indicator_names(self) -> List[str]:
        """
        Get list of all custom indicator names.
        
        Returns:
            List of custom indicator names
        """
        return list(self.custom_indicators.keys())
    
    def clear_cache(self) -> None:
        """Clear the calculation cache."""
        self.calculation_cache.clear()
