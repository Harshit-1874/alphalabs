# Custom Indicator JSON Schema

## Overview

Custom indicators are defined using JSON-based rules instead of formula strings. This approach provides:
- **Security**: No code execution, pure data parsing
- **Validation**: Structured format with clear validation rules
- **Type Safety**: Explicit operand types (indicator references vs values)
- **Clarity**: Easy to understand and debug

## JSON Rule Structure

### Basic Schema

```json
{
  "name": "string",           // Unique identifier for the custom indicator
  "type": "composite|derived", // Type of custom indicator
  "formula": {                // Nested formula tree
    "operator": "+|-|*|/",    // Mathematical operator
    "left": <operand>,        // Left operand
    "right": <operand>        // Right operand
  }
}
```

### Operand Types

An operand can be one of:

1. **Indicator Reference**
```json
{"indicator": "rsi"}
```

2. **Numeric Value**
```json
{"value": 50}
```

3. **Nested Formula** (for complex expressions)
```json
{
  "operator": "+",
  "left": {"indicator": "close"},
  "right": {"value": 100}
}
```

## Complete Examples

### Example 1: Price Momentum
**Formula**: `(rsi + 50) * 0.01`

```json
{
  "name": "price_momentum",
  "type": "composite",
  "formula": {
    "operator": "*",
    "left": {
      "operator": "+",
      "left": {"indicator": "rsi"},
      "right": {"value": 50}
    },
    "right": {"value": 0.01}
  }
}
```

**Evaluation Tree**:
```
        *
       / \
      +   0.01
     / \
   rsi  50
```

### Example 2: Mean Reversion Signal
**Formula**: `(close - sma_50) / atr`

```json
{
  "name": "mean_reversion",
  "type": "composite",
  "formula": {
    "operator": "/",
    "left": {
      "operator": "-",
      "left": {"indicator": "close"},
      "right": {"indicator": "sma_50"}
    },
    "right": {"indicator": "atr"}
  }
}
```

**Evaluation Tree**:
```
          /
         / \
        -   atr
       / \
   close  sma_50
```

### Example 3: Volatility Ratio
**Formula**: `(high - low) / close`

```json
{
  "name": "volatility_ratio",
  "type": "composite",
  "formula": {
    "operator": "/",
    "left": {
      "operator": "-",
      "left": {"indicator": "high"},
      "right": {"indicator": "low"}
    },
    "right": {"indicator": "close"}
  }
}
```

### Example 4: Weighted RSI
**Formula**: `rsi * 0.7`

```json
{
  "name": "weighted_rsi",
  "type": "derived",
  "formula": {
    "operator": "*",
    "left": {"indicator": "rsi"},
    "right": {"value": 0.7}
  }
}
```

### Example 5: Complex Composite
**Formula**: `((rsi + macd) / 2) * (close / sma_200)`

```json
{
  "name": "complex_signal",
  "type": "composite",
  "formula": {
    "operator": "*",
    "left": {
      "operator": "/",
      "left": {
        "operator": "+",
        "left": {"indicator": "rsi"},
        "right": {"indicator": "macd"}
      },
      "right": {"value": 2}
    },
    "right": {
      "operator": "/",
      "left": {"indicator": "close"},
      "right": {"indicator": "sma_200"}
    }
  }
}
```

**Evaluation Tree**:
```
              *
            /   \
           /     \
          /       /
         / \     / \
        +   2  close sma_200
       / \
     rsi macd
```

## Validation Rules

### Required Fields
- `name`: Must be a non-empty string, unique across all indicators
- `type`: Must be either "composite" or "derived"
- `formula`: Must be a valid formula object

### Formula Validation
- `operator`: Must be one of: `+`, `-`, `*`, `/`
- `left` and `right`: Must be valid operands
- Operands must be either:
  - `{"indicator": "name"}` where name exists
  - `{"value": number}` where number is finite
  - A nested formula object

### Indicator References
- All referenced indicators must exist in the available indicators
- Can reference:
  - Built-in indicators (rsi, macd, ema_20, etc.)
  - OHLCV data (open, high, low, close, volume)
  - Other custom indicators (if defined first)

### Circular Dependencies
- Custom indicators cannot reference themselves
- Cannot create circular chains (A → B → A)
- Must be evaluated in dependency order

### Type Safety
- All operations must result in numeric pandas Series
- Division by zero returns NaN (handled gracefully)
- Invalid operations are caught during validation

## Error Messages

### Invalid Structure
```json
{
  "error": "INVALID_RULE_STRUCTURE",
  "message": "Missing required field: formula",
  "rule_name": "my_indicator"
}
```

### Invalid Operator
```json
{
  "error": "INVALID_OPERATOR",
  "message": "Operator '%' is not allowed. Use one of: +, -, *, /",
  "rule_name": "my_indicator"
}
```

### Missing Indicator
```json
{
  "error": "INDICATOR_NOT_FOUND",
  "message": "Referenced indicator 'custom_rsi' does not exist",
  "rule_name": "my_indicator"
}
```

### Circular Dependency
```json
{
  "error": "CIRCULAR_DEPENDENCY",
  "message": "Circular dependency detected: indicator_a → indicator_b → indicator_a",
  "rule_name": "indicator_a"
}
```

## Implementation Notes

### Recursive Evaluation

The formula is evaluated recursively:

```python
def _evaluate_formula(self, formula: Dict) -> pd.Series:
    """Recursively evaluate JSON formula tree"""
    
    # Base case: indicator reference
    if "indicator" in formula:
        indicator_name = formula["indicator"]
        return self.available_indicators[indicator_name]
    
    # Base case: constant value
    if "value" in formula:
        value = formula["value"]
        # Create Series with constant value
        return pd.Series([value] * len(self.df), index=self.df.index)
    
    # Recursive case: operator with left/right
    operator = formula["operator"]
    left = self._evaluate_formula(formula["left"])
    right = self._evaluate_formula(formula["right"])
    
    # Apply operator
    if operator == "+":
        return left + right
    elif operator == "-":
        return left - right
    elif operator == "*":
        return left * right
    elif operator == "/":
        return left / right  # Division by zero → NaN
```

### Available Indicators

The CustomIndicatorEngine receives a dictionary of available indicators:

```python
available_indicators = {
    # OHLCV data
    "open": df["open"],
    "high": df["high"],
    "low": df["low"],
    "close": df["close"],
    "volume": df["volume"],
    
    # Calculated indicators
    "rsi": rsi_series,
    "macd": macd_series,
    "ema_20": ema_20_series,
    # ... etc
}
```

### Integration with IndicatorCalculator

```python
# In IndicatorCalculator.__init__
self.custom_engine = CustomIndicatorEngine(
    df=self.df,
    available_indicators={
        "open": self.df["open"],
        "high": self.df["high"],
        "low": self.df["low"],
        "close": self.df["close"],
        "volume": self.df["volume"],
        **self.cache  # All calculated indicators
    }
)

# Add custom indicator rules
for rule in custom_indicator_rules:
    self.custom_engine.add_rule(rule)

# Calculate custom indicators
for name in self.custom_engine.custom_indicators.keys():
    self.cache[name] = self.custom_engine.calculate(name)
```

## Usage Example

```python
from services.trading.indicator_calculator import IndicatorCalculator
from services.trading.custom_indicator_engine import CustomIndicatorEngine

# Define custom indicator rules
custom_rules = [
    {
        "name": "price_momentum",
        "type": "composite",
        "formula": {
            "operator": "*",
            "left": {
                "operator": "+",
                "left": {"indicator": "rsi"},
                "right": {"value": 50}
            },
            "right": {"value": 0.01}
        }
    },
    {
        "name": "mean_reversion",
        "type": "composite",
        "formula": {
            "operator": "/",
            "left": {
                "operator": "-",
                "left": {"indicator": "close"},
                "right": {"indicator": "sma_50"}
            },
            "right": {"indicator": "atr"}
        }
    }
]

# Initialize calculator with custom indicators
calc = IndicatorCalculator(
    candles=candles,
    enabled_indicators=['rsi', 'macd', 'sma_50', 'atr'],
    custom_indicators=custom_rules,
    mode='omni'
)

# Get all indicators including custom ones
result = calc.calculate_all(100)
print(result)
# {
#   'rsi': 45.2,
#   'macd': 123.4,
#   'sma_50': 42300.0,
#   'atr': 500.0,
#   'price_momentum': 0.952,  # Custom indicator
#   'mean_reversion': -0.4    # Custom indicator
# }
```

## Benefits of JSON-Based Approach

1. **Security**: No code execution, impossible to inject malicious code
2. **Validation**: Structure can be validated before execution
3. **Serialization**: Easy to store in database as JSONB
4. **Debugging**: Clear tree structure, easy to trace evaluation
5. **Type Safety**: Explicit operand types prevent errors
6. **Portability**: JSON is language-agnostic
7. **UI-Friendly**: Can build visual formula builders in frontend
8. **Versioning**: Easy to version and migrate rule formats

## Future Enhancements

Potential additions to the schema:

1. **Functions**: Add support for functions like `abs`, `max`, `min`
```json
{
  "function": "abs",
  "argument": {"indicator": "macd"}
}
```

2. **Conditionals**: Add if-then-else logic
```json
{
  "condition": {
    "operator": ">",
    "left": {"indicator": "rsi"},
    "right": {"value": 70}
  },
  "then": {"value": 1},
  "else": {"value": 0}
}
```

3. **Aggregations**: Add rolling window operations
```json
{
  "aggregation": "rolling_mean",
  "window": 20,
  "indicator": "close"
}
```
