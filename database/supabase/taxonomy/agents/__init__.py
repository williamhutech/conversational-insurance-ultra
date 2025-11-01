"""
Agents Package
Processing agents for the taxonomy extraction pipeline.
"""

# Stage 1
from .stage1_key_extractor import KeyExtractor

# Stage 2 (Extractors)
from .stage2_condition_extractor import (
    ConditionExtractor,
    ConditionExtractorPrompt,
    BatchConditionExtractor
)
from .stage2_benefit_extractor import (
    BenefitExtractor,
    BenefitExtractorPrompt,
    BatchBenefitExtractor
)
from .stage2_benefit_condition_extractor import (
    BenefitConditionExtractor,
    BenefitConditionExtractorPrompt,
    BatchBenefitConditionExtractor
)

# Stage 2 (Judgers)
from .stage2_condition_judger import (
    ConditionJudger,
    ConditionJudgerPrompt,
    BatchConditionJudger
)
from .stage2_benefit_judger import (
    BenefitJudger,
    BenefitJudgerPrompt,
    BatchBenefitJudger
)
from .stage2_benefit_condition_judger import (
    BenefitConditionJudger,
    BenefitConditionJudgerPrompt,
    BatchBenefitConditionJudger
)

# Stage 2 (Validators)
from .stage2_json_validators import (
    ConditionValidator,
    BenefitValidator,
    BenefitConditionValidator,
    JSONValidatorFactory
)

# Stage 3
from .stage3_aggregator import ProductAggregator

# Stage 4 (Standardizers)
from .stage4_condition_standardizer import (
    ConditionStandardizer,
    ConditionStandardizerPrompt,
    BatchConditionStandardizer
)
from .stage4_benefit_standardizer import (
    BenefitStandardizer,
    BenefitStandardizerPrompt,
    BatchBenefitStandardizer
)
from .stage4_benefit_condition_standardizer import (
    BenefitConditionStandardizer,
    BenefitConditionStandardizerPrompt,
    BatchBenefitConditionStandardizer
)

# Stage 5
from .stage5_final_assembler import FinalAssembler

__all__ = [
    # Stage 1
    "KeyExtractor",

    # Stage 2 - Extractors
    "ConditionExtractor",
    "ConditionExtractorPrompt",
    "BatchConditionExtractor",
    "BenefitExtractor",
    "BenefitExtractorPrompt",
    "BatchBenefitExtractor",
    "BenefitConditionExtractor",
    "BenefitConditionExtractorPrompt",
    "BatchBenefitConditionExtractor",

    # Stage 2 - Judgers
    "ConditionJudger",
    "ConditionJudgerPrompt",
    "BatchConditionJudger",
    "BenefitJudger",
    "BenefitJudgerPrompt",
    "BatchBenefitJudger",
    "BenefitConditionJudger",
    "BenefitConditionJudgerPrompt",
    "BatchBenefitConditionJudger",

    # Stage 2 - Validators
    "ConditionValidator",
    "BenefitValidator",
    "BenefitConditionValidator",
    "JSONValidatorFactory",

    # Stage 3
    "ProductAggregator",

    # Stage 4 - Standardizers
    "ConditionStandardizer",
    "ConditionStandardizerPrompt",
    "BatchConditionStandardizer",
    "BenefitStandardizer",
    "BenefitStandardizerPrompt",
    "BatchBenefitStandardizer",
    "BenefitConditionStandardizer",
    "BenefitConditionStandardizerPrompt",
    "BatchBenefitConditionStandardizer",

    # Stage 5
    "FinalAssembler",
]
