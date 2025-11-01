"""
Personality Generator Agent (Stage 5)
Generates diverse customer personas for QA generation.
"""

import json
import math
from pathlib import Path
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..utils.api_client import APIClient
from ..entities.data_models import PersonalityGenerationResult


class PersonalityPromptTemplate:
    """Prompt template for personality generation."""

    @staticmethod
    def get_system_prompt() -> str:
        """Get system prompt for personality generation."""
        return """You are an expert persona designer specializing in creating detailed, realistic insurance customer profiles.

Your task is to generate diverse, specific personalities for insurance customers.

Generation principles:
- Create complete, realistic personas with specific details
- Include concrete demographics, occupation details, and income levels
- Provide specific lifestyle habits and activities
- Detail clear insurance motivations and concerns
- Avoid vague descriptions (e.g., "likes insurance", "good person")
- Each personality should be distinct and representative of real customer segments
- Use specific numbers, companies, locations when applicable

Please ensure the output format strictly follows JSON format requirements."""

    @staticmethod
    def get_generation_prompt(batch_size: int) -> str:
        """
        Get generation prompt for creating personalities.

        Args:
            batch_size: Number of personalities to generate

        Returns:
            Formatted generation prompt
        """
        return f"""**Task: Generate {batch_size} diverse insurance customer personalities**

Generate {batch_size} detailed, specific customer personalities that represent different insurance customer segments, be as diverse as possible in demographics, occupations, lifestyles, and insurance needs.

Each personality description MUST include ALL of these details in a single comprehensive string:
- Name (with title)
- Sex
- Age (specific number)
- Nationality
- Marital Status (with family details if applicable)
- Occupation (specific role and company type)
- Education Level
- Income Level (specific amount with currency)
- Lifestyle (specific hobbies and activities with frequency)
- Personality Traits (specific traits relevant to insurance decisions)
- Insurance Motivation (specific reasons and scenarios)
- Concerns (specific risks and coverage needs)
- Decision-Making Style (specific research and comparison behaviors)
- Preferred Communication Style (specific channels and preferences)
- Previous Insurance Experience (specific products and future considerations)

The output should be ALWAYS a json list of STRINGS, each string representing one complete personality description with all required details.

**Output format (strictly follow JSON format):**
```json
{{
  "personalities": [
    "personality1",
    "personality2",
    ...
  ]
}}
```"""


class PersonalityGenerator:
    """
    Generate diverse customer personas for insurance scenarios.

    Creates detailed personality profiles with demographics, lifestyle,
    insurance motivations, and concerns for use in QA generation.
    """

    def __init__(self, api_client: APIClient):
        """
        Initialize personality generator.

        Args:
            api_client: Configured API client
        """
        self.api_client = api_client
        self.prompt = PersonalityPromptTemplate()

    def generate_batch(self, batch_size: int = 5) -> List[str]:
        """
        Generate a batch of personalities in a single API call.

        Args:
            batch_size: Number of personalities to generate per call

        Returns:
            List of personality strings
        """
        # Create messages
        system_prompt = self.prompt.get_system_prompt()
        user_prompt = self.prompt.get_generation_prompt(batch_size)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        # Call API
        api_result = self.api_client.call_api(messages, timeout=120)

        if api_result["status"] == "success":
            try:
                # Parse JSON response
                response_content = api_result["content"]

                # Remove markdown code blocks if present
                if "```json" in response_content:
                    response_content = response_content.split("```json")[1].split("```")[0]
                elif "```" in response_content:
                    response_content = response_content.replace("```", "")

                response_json = json.loads(response_content.strip())
                personalities = response_json.get("personalities", [])
                return personalities

            except Exception as e:
                print(f"Failed to parse batch: {str(e)}")
                return []

        return []

    def generate_personalities(
        self,
        personality_number: int,
        batch_size: int = 5,
        max_workers: int = 10
    ) -> List[str]:
        """
        Generate multiple personalities using concurrent batch generation.

        Args:
            personality_number: Total number of personalities to generate
            batch_size: Number of personalities per API call
            max_workers: Number of concurrent API calls

        Returns:
            List of all generated personality strings
        """
        # Calculate number of batches needed
        num_batches = math.ceil(personality_number / batch_size)

        print(f"Generating {personality_number} personalities in {num_batches} batches...")

        all_personalities = []

        # Process batches concurrently
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit batch generation tasks
            futures = []
            for i in range(num_batches):
                # Calculate batch size for the last batch
                if i == num_batches - 1:
                    current_batch_size = personality_number - (i * batch_size)
                else:
                    current_batch_size = batch_size

                future = executor.submit(self.generate_batch, current_batch_size)
                futures.append(future)

            # Collect results as they complete
            for i, future in enumerate(as_completed(futures)):
                personalities = future.result()
                all_personalities.extend(personalities)
                print(f"Completed batch {i+1}/{num_batches}: Generated {len(personalities)} personalities")

        print(f"Total: Generated {len(all_personalities)} personalities")
        return all_personalities

    def save_personalities(
        self,
        personalities: List[str],
        output_file: Path
    ) -> Path:
        """
        Save generated personalities to a JSON file.

        Args:
            personalities: List of personality strings
            output_file: Path to output file

        Returns:
            Path to saved file
        """
        output_file = Path(output_file)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # Save to file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(personalities, f, indent=2, ensure_ascii=False)

        print(f"Saved {len(personalities)} personalities to {output_file}")
        return output_file

    def generate_and_save(
        self,
        personality_number: int,
        output_file: Path,
        batch_size: int = 5,
        max_workers: int = 10
    ) -> PersonalityGenerationResult:
        """
        Generate personalities and save to file.

        Convenience method that combines generation and saving.

        Args:
            personality_number: Total number of personalities to generate
            output_file: Path to output file
            batch_size: Number of personalities per API call
            max_workers: Number of concurrent API calls

        Returns:
            PersonalityGenerationResult with status and file path
        """
        try:
            # Generate personalities
            personalities = self.generate_personalities(
                personality_number=personality_number,
                batch_size=batch_size,
                max_workers=max_workers
            )

            # Save to file
            saved_path = self.save_personalities(personalities, output_file)

            return PersonalityGenerationResult(
                status="success",
                batch_index=0,
                personalities=personalities
            )

        except Exception as e:
            return PersonalityGenerationResult(
                status="error",
                batch_index=0,
                error=str(e)
            )
