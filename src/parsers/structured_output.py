"""Orchestrator for extracting, parsing, and validating LLM outputs."""

from typing import Any, Dict, List, Optional, Tuple, Union
from .extractors import extract_json_block
from .json_parser import parse_json, repair_json
from .validators import validate_required_fields, validate_keys, validate_types, validate_enum


class StructuredOutputParser:
    """Orchestrates extraction, parsing, and validation of raw LLM outputs.

    Provides a clean, unified interface to parse text into validated Python
    dictionaries or lists.
    """

    def __init__(
        self,
        required_fields: Optional[List[str]] = None,
        allowed_keys: Optional[List[str]] = None,
        expected_types: Optional[Dict[str, Union[type, Tuple[type, ...]]]] = None,
        enums: Optional[Dict[str, List[Any]]] = None,
    ) -> None:
        """Initializes the parser with validation rules.

        Args:
            required_fields: Optional list of required field paths (supports
              dot-notation for nesting).
            allowed_keys: Optional list of permitted top-level keys.
            expected_types: Optional mapping of field paths to expected Python types.
            enums: Optional mapping of field paths to lists of allowed values.
        """
        self.required_fields = required_fields
        self.allowed_keys = allowed_keys
        self.expected_types = expected_types
        self.enums = enums

    def parse(self, text: str, repair: bool = True) -> Any:
        """Extracts, parses, and validates structured output from raw LLM text.

        Args:
            text: The raw, unreliable text from the model.
            repair: Whether to attempt deterministic JSON repair. Defaults to True.

        Returns:
            The parsed and validated Python object (dict or list).

        Raises:
            ExtractionError: If no JSON structure can be found.
            JSONParseError: If parsing fails.
            ValidationError: If any validation rule fails.
        """
        # 1. Extract JSON block from markdown fences or text
        raw_json = extract_json_block(text)

        # 2. Repair common formatting faults if enabled
        if repair:
            raw_json = repair_json(raw_json)

        # 3. Perform strict JSON parsing
        parsed = parse_json(raw_json)

        # 4. Perform validation checks if target is a dictionary
        if isinstance(parsed, dict):
            if self.required_fields:
                validate_required_fields(parsed, self.required_fields)
            if self.allowed_keys:
                validate_keys(parsed, self.allowed_keys)
            if self.expected_types:
                validate_types(parsed, self.expected_types)
            if self.enums:
                for field, allowed_values in self.enums.items():
                    validate_enum(parsed, field, allowed_values)

        return parsed
```
,Description:
