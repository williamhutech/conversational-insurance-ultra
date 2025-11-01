"""
Stage 2: JSON Validators
Programmatic validation of JSON structure and types for all three layers.
"""

import sys
from pathlib import Path
from typing import Dict, List, Any, Tuple

sys.path.append(str(Path(__file__).resolve().parent.parent))

from entities.data_models import ValidationResult


class ConditionValidator:
    """Validates general condition JSON structure."""

    REQUIRED_KEYS = {"condition", "condition_type", "products"}
    PRODUCT_REQUIRED_KEYS = {"condition_exist", "original_text", "parameters"}
    VALID_CONDITION_TYPES = {"eligibility", "exclusion"}

    @classmethod
    def validate(cls, data: Dict[str, Any]) -> ValidationResult:
        """Validate general condition JSON."""
        errors = []
        warnings = []

        # Check top-level keys
        missing_keys = cls.REQUIRED_KEYS - set(data.keys())
        if missing_keys:
            errors.append(f"Missing required keys: {missing_keys}")

        # Validate condition field
        if "condition" not in data or not isinstance(data["condition"], str):
            errors.append("'condition' must be a string")

        # Validate condition_type
        if "condition_type" in data:
            if data["condition_type"] not in cls.VALID_CONDITION_TYPES:
                errors.append(f"'condition_type' must be one of {cls.VALID_CONDITION_TYPES}")

        # Validate products structure
        if "products" in data:
            if not isinstance(data["products"], dict):
                errors.append("'products' must be a dictionary")
            else:
                for product_name, product_data in data["products"].items():
                    missing_product_keys = cls.PRODUCT_REQUIRED_KEYS - set(product_data.keys())
                    if missing_product_keys:
                        errors.append(f"Product '{product_name}' missing keys: {missing_product_keys}")

                    # Validate condition_exist is boolean
                    if "condition_exist" in product_data:
                        if not isinstance(product_data["condition_exist"], bool):
                            errors.append(f"Product '{product_name}': 'condition_exist' must be boolean")

                    # Validate parameters is dict
                    if "parameters" in product_data:
                        if not isinstance(product_data["parameters"], dict):
                            errors.append(f"Product '{product_name}': 'parameters' must be a dictionary")

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            layer_name="general_conditions",
            data=data,
            errors=errors,
            warnings=warnings
        )

    @classmethod
    def validate_list(cls, data_list: List[Dict[str, Any]]) -> ValidationResult:
        """Validate a list of general condition JSON objects."""
        errors = []
        warnings = []

        # Check data_list is a list
        if not isinstance(data_list, list):
            return ValidationResult(
                is_valid=False,
                layer_name="general_conditions",
                data=data_list,
                errors=["Data must be a list"],
                warnings=[]
            )

        # Validate each item in the list
        for idx, item in enumerate(data_list):
            if not isinstance(item, dict):
                errors.append(f"List item {idx} is not a dictionary")
                continue

            # Validate individual item
            item_result = cls.validate(item)
            if not item_result.is_valid:
                for error in item_result.errors:
                    errors.append(f"Item {idx}: {error}")
            warnings.extend([f"Item {idx}: {w}" for w in item_result.warnings])

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            layer_name="general_conditions",
            data=data_list,
            errors=errors,
            warnings=warnings
        )


class BenefitValidator:
    """Validates benefit JSON structure."""

    REQUIRED_KEYS = {"benefit_name", "products"}
    PRODUCT_REQUIRED_KEYS = {"condition_exist", "parameters"}
    PARAMETER_KEYS = {"coverage_limit", "sub_limits"}

    @classmethod
    def validate(cls, data: Dict[str, Any]) -> ValidationResult:
        """Validate benefit JSON."""
        errors = []
        warnings = []

        # Check top-level keys
        missing_keys = cls.REQUIRED_KEYS - set(data.keys())
        if missing_keys:
            errors.append(f"Missing required keys: {missing_keys}")

        # Validate benefit_name
        if "benefit_name" not in data or not isinstance(data["benefit_name"], str):
            errors.append("'benefit_name' must be a string")

        # Validate products structure
        if "products" in data:
            if not isinstance(data["products"], dict):
                errors.append("'products' must be a dictionary")
            else:
                for product_name, product_data in data["products"].items():
                    missing_product_keys = cls.PRODUCT_REQUIRED_KEYS - set(product_data.keys())
                    if missing_product_keys:
                        errors.append(f"Product '{product_name}' missing keys: {missing_product_keys}")

                    # Validate condition_exist is boolean
                    if "condition_exist" in product_data:
                        if not isinstance(product_data["condition_exist"], bool):
                            errors.append(f"Product '{product_name}': 'condition_exist' must be boolean")

                    # Validate parameters
                    if "parameters" in product_data:
                        if not isinstance(product_data["parameters"], dict):
                            errors.append(f"Product '{product_name}': 'parameters' must be a dictionary")
                        else:
                            params = product_data["parameters"]
                            # Check for coverage_limit
                            if "coverage_limit" not in params:
                                warnings.append(f"Product '{product_name}': missing 'coverage_limit'")

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            layer_name="benefits",
            data=data,
            errors=errors,
            warnings=warnings
        )

    @classmethod
    def validate_list(cls, data_list: List[Dict[str, Any]]) -> ValidationResult:
        """Validate a list of benefit JSON objects."""
        errors = []
        warnings = []

        # Check data_list is a list
        if not isinstance(data_list, list):
            return ValidationResult(
                is_valid=False,
                layer_name="benefits",
                data=data_list,
                errors=["Data must be a list"],
                warnings=[]
            )

        # Validate each item in the list
        for idx, item in enumerate(data_list):
            if not isinstance(item, dict):
                errors.append(f"List item {idx} is not a dictionary")
                continue

            # Validate individual item
            item_result = cls.validate(item)
            if not item_result.is_valid:
                for error in item_result.errors:
                    errors.append(f"Item {idx}: {error}")
            warnings.extend([f"Item {idx}: {w}" for w in item_result.warnings])

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            layer_name="benefits",
            data=data_list,
            errors=errors,
            warnings=warnings
        )


class BenefitConditionValidator:
    """Validates benefit-specific condition JSON structure."""

    REQUIRED_KEYS = {"benefit_name", "condition", "condition_type", "products"}
    PRODUCT_REQUIRED_KEYS = {"condition_exist", "original_text", "parameters"}
    VALID_CONDITION_TYPES = {"benefit_eligibility", "benefit_exclusion"}

    @classmethod
    def validate(cls, data: Dict[str, Any]) -> ValidationResult:
        """Validate benefit-specific condition JSON."""
        errors = []
        warnings = []

        # Check top-level keys
        missing_keys = cls.REQUIRED_KEYS - set(data.keys())
        if missing_keys:
            errors.append(f"Missing required keys: {missing_keys}")

        # Validate benefit_name
        if "benefit_name" not in data or not isinstance(data["benefit_name"], str):
            errors.append("'benefit_name' must be a string")

        # Validate condition
        if "condition" not in data or not isinstance(data["condition"], str):
            errors.append("'condition' must be a string")

        # Validate condition_type
        if "condition_type" in data:
            if data["condition_type"] not in cls.VALID_CONDITION_TYPES:
                errors.append(f"'condition_type' must be one of {cls.VALID_CONDITION_TYPES}")

        # Validate products structure
        if "products" in data:
            if not isinstance(data["products"], dict):
                errors.append("'products' must be a dictionary")
            else:
                for product_name, product_data in data["products"].items():
                    missing_product_keys = cls.PRODUCT_REQUIRED_KEYS - set(product_data.keys())
                    if missing_product_keys:
                        errors.append(f"Product '{product_name}' missing keys: {missing_product_keys}")

                    # Validate condition_exist is boolean
                    if "condition_exist" in product_data:
                        if not isinstance(product_data["condition_exist"], bool):
                            errors.append(f"Product '{product_name}': 'condition_exist' must be boolean")

                    # Validate parameters is dict
                    if "parameters" in product_data:
                        if not isinstance(product_data["parameters"], dict):
                            errors.append(f"Product '{product_name}': 'parameters' must be a dictionary")

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            layer_name="benefit_specific_conditions",
            data=data,
            errors=errors,
            warnings=warnings
        )

    @classmethod
    def validate_list(cls, data_list: List[Dict[str, Any]]) -> ValidationResult:
        """Validate a list of benefit-specific condition JSON objects."""
        errors = []
        warnings = []

        # Check data_list is a list
        if not isinstance(data_list, list):
            return ValidationResult(
                is_valid=False,
                layer_name="benefit_specific_conditions",
                data=data_list,
                errors=["Data must be a list"],
                warnings=[]
            )

        # Validate each item in the list
        for idx, item in enumerate(data_list):
            if not isinstance(item, dict):
                errors.append(f"List item {idx} is not a dictionary")
                continue

            # Validate individual item
            item_result = cls.validate(item)
            if not item_result.is_valid:
                for error in item_result.errors:
                    errors.append(f"Item {idx}: {error}")
            warnings.extend([f"Item {idx}: {w}" for w in item_result.warnings])

        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            layer_name="benefit_specific_conditions",
            data=data_list,
            errors=errors,
            warnings=warnings
        )


class JSONValidatorFactory:
    """Factory for getting the appropriate validator."""

    @staticmethod
    def get_validator(layer_name: str):
        """Get validator for a specific layer."""
        validators = {
            "general_conditions": ConditionValidator,
            "benefits": BenefitValidator,
            "benefit_specific_conditions": BenefitConditionValidator
        }
        return validators.get(layer_name)

    @staticmethod
    def validate_batch(
        data_list: List[Dict[str, Any]],
        layer_name: str
    ) -> Tuple[List[ValidationResult], int, int]:
        """
        Validate a batch of JSON objects.

        Returns:
            Tuple of (validation_results, valid_count, invalid_count)
        """
        validator = JSONValidatorFactory.get_validator(layer_name)
        if not validator:
            raise ValueError(f"Unknown layer: {layer_name}")

        results = []
        valid_count = 0
        invalid_count = 0

        for data in data_list:
            result = validator.validate(data)
            results.append(result)

            if result.is_valid:
                valid_count += 1
            else:
                invalid_count += 1

        return results, valid_count, invalid_count
