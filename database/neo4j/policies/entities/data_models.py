"""
Data Models
Dataclasses for representing entities throughout the pipeline.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from datetime import datetime


# ============================================================================
# Stage 1: Product Extraction Models
# ============================================================================

@dataclass
class ProductExtractionResult:
    """Result from product name extraction."""
    status: str  # "success" or "error"
    file_name: str
    product_names: Optional[List[str]] = None
    error: Optional[str] = None


# ============================================================================
# Stage 2: Concept Extraction Models
# ============================================================================

@dataclass
class ConceptExtractionResult:
    """Result from concept extraction."""
    status: str  # "success" or "error"
    text_id: str
    extracted_concepts: Optional[List[str]] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None


# ============================================================================
# Stage 3: Fact Extraction Models
# ============================================================================

@dataclass
class FactExtractionResult:
    """Result from fact extraction."""
    status: str  # "success" or "error"
    product_name: str
    text_index: int
    extracted_facts: Optional[List[str]] = None
    error: Optional[str] = None
    processing_time: Optional[float] = None


# ============================================================================
# Stage 4: Concept Expansion Models
# ============================================================================

@dataclass
class ConceptExpansionResult:
    """Result from concept expansion for a single concept."""
    status: str  # "success", "api_error", or "json_error"
    concept_id: str
    center_concept: str
    existing_neighbors: List[str]
    new_concepts: Optional[List[str]] = None
    error_details: Optional[str] = None
    processing_time: Optional[float] = None


# ============================================================================
# Stage 5: Personality Models
# ============================================================================

@dataclass
class PersonalityProfile:
    """Customer personality profile for QA generation."""
    name: str
    sex: str
    age: int
    nationality: str
    marital_status: str
    occupation: str
    education: str
    income_level: str
    lifestyle: str
    personality_traits: str
    insurance_motivation: str
    insurance_concerns: str
    decision_making_style: str
    communication_preference: str
    insurance_experience: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "sex": self.sex,
            "age": self.age,
            "nationality": self.nationality,
            "marital_status": self.marital_status,
            "occupation": self.occupation,
            "education": self.education,
            "income_level": self.income_level,
            "lifestyle": self.lifestyle,
            "personality_traits": self.personality_traits,
            "insurance_motivation": self.insurance_motivation,
            "insurance_concerns": self.insurance_concerns,
            "decision_making_style": self.decision_making_style,
            "communication_preference": self.communication_preference,
            "insurance_experience": self.insurance_experience
        }

    def to_string(self) -> str:
        """Convert to formatted string."""
        return f"""
Name: {self.name}
Sex: {self.sex}
Age: {self.age}
Nationality: {self.nationality}
Marital Status: {self.marital_status}
Occupation: {self.occupation}
Education: {self.education}
Income Level: {self.income_level}
Lifestyle: {self.lifestyle}
Personality Traits: {self.personality_traits}
Insurance Motivation: {self.insurance_motivation}
Insurance Concerns: {self.insurance_concerns}
Decision Making Style: {self.decision_making_style}
Communication Preference: {self.communication_preference}
Insurance Experience: {self.insurance_experience}
""".strip()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PersonalityProfile':
        """Create from dictionary."""
        return cls(
            name=data["name"],
            sex=data["sex"],
            age=data["age"],
            nationality=data["nationality"],
            marital_status=data["marital_status"],
            occupation=data["occupation"],
            education=data["education"],
            income_level=data["income_level"],
            lifestyle=data["lifestyle"],
            personality_traits=data["personality_traits"],
            insurance_motivation=data["insurance_motivation"],
            insurance_concerns=data["insurance_concerns"],
            decision_making_style=data["decision_making_style"],
            communication_preference=data["communication_preference"],
            insurance_experience=data["insurance_experience"]
        )


@dataclass
class PersonalityGenerationResult:
    """Result from personality generation."""
    status: str  # "success" or "error"
    batch_index: int
    personalities: Optional[List[PersonalityProfile]] = None
    error: Optional[str] = None


# ============================================================================
# Stage 7: QA Distillation Models
# ============================================================================

@dataclass
class QAPair:
    """Question-answer pair with metadata."""
    question_id: int
    question: str
    reasoning_guidance: str
    knowledge_facts: List[str]
    final_answer: str
    best_to_know: str
    concept: Optional[str] = None  # Single concept
    concept_pair: Optional[tuple] = None  # Concept pair (concept1, concept2)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "question_id": self.question_id,
            "question": self.question,
            "reasoning_guidance": self.reasoning_guidance,
            "knowledge_facts": self.knowledge_facts,
            "final_answer": self.final_answer,
            "best_to_know": self.best_to_know
        }
        if self.concept:
            result["concept"] = self.concept
        if self.concept_pair:
            result["concept_pair"] = list(self.concept_pair)
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QAPair':
        """Create from dictionary."""
        return cls(
            question_id=data["question_id"],
            question=data["question"],
            reasoning_guidance=data["reasoning_guidance"],
            knowledge_facts=data["knowledge_facts"],
            final_answer=data["final_answer"],
            best_to_know=data["best_to_know"],
            concept=data.get("concept"),
            concept_pair=tuple(data["concept_pair"]) if "concept_pair" in data else None
        )


@dataclass
class ConceptDistillationResult:
    """Result from concept distillation (Stage 7a)."""
    status: str  # "success", "api_error", "json_error", or "exception"
    concept_id: str
    concept_name: str
    generated_questions: Optional[List[Dict[str, Any]]] = None  # Raw question dicts from JSON
    response: Optional[str] = None  # Raw API response
    error_details: Optional[str] = None
    processing_time: Optional[float] = None
    json_validation: Optional[Dict[str, Any]] = None  # Validation metadata


@dataclass
class PairValidationResult:
    """Result from concept pair validation (Stage 7b)."""
    status: str  # "success", "api_error", "json_error", or "exception"
    pair_id: str
    concept_pair: tuple  # (concept1, concept2)
    is_clinically_relevant: Optional[bool] = None  # Insurance relevance
    is_instructionally_meaningful: Optional[bool] = None  # Educational value
    qa_data: Optional[Dict[str, Any]] = None  # Raw QA dictionary if pair is valid
    response: Optional[str] = None  # Raw API response
    error_details: Optional[str] = None
    processing_time: Optional[float] = None
    json_validation: Optional[Dict[str, Any]] = None  # Validation metadata


# ============================================================================
# Stage 8: MemOS/Neo4j Graph Models
# ============================================================================

@dataclass
class GraphNode:
    """Node in the knowledge graph."""
    id: str
    type: str  # "Concept" or "QA"
    text: str
    embedding: List[float]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "type": self.type,
            "text": self.text,
            "embedding": self.embedding,
            "metadata": self.metadata
        }

    @classmethod
    def create_concept_node(
        cls,
        concept: str,
        embedding: List[float]
    ) -> 'GraphNode':
        """Create a concept node."""
        import uuid
        return cls(
            id=str(uuid.uuid4()),
            type="Concept",
            text=concept,
            embedding=embedding,
            metadata={
                "node_type": "Concept",
                "created_at": datetime.now().isoformat()
            }
        )

    @classmethod
    def create_qa_node(
        cls,
        qa_pair: QAPair,
        embedding: List[float]
    ) -> 'GraphNode':
        """Create a QA node."""
        import uuid
        return cls(
            id=str(uuid.uuid4()),
            type="QA",
            text=qa_pair.question,
            embedding=embedding,
            metadata={
                "node_type": "QA",
                "reasoning_guidance": qa_pair.reasoning_guidance,
                "knowledge_facts": qa_pair.knowledge_facts,
                "final_answer": qa_pair.final_answer,
                "best_to_know": qa_pair.best_to_know,
                "created_at": datetime.now().isoformat()
            }
        )


@dataclass
class GraphEdge:
    """Edge in the knowledge graph."""
    source: str  # Node ID
    target: str  # Node ID
    relationship_type: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "source": self.source,
            "target": self.target,
            "type": self.relationship_type,
            "created_at": self.created_at
        }

    @classmethod
    def create_edge(
        cls,
        source_id: str,
        target_id: str,
        relationship_type: str = "RELATED_TO"
    ) -> 'GraphEdge':
        """Create an edge."""
        return cls(
            source=source_id,
            target=target_id,
            relationship_type=relationship_type,
            created_at=datetime.now().isoformat()
        )


@dataclass
class KnowledgeGraph:
    """Complete knowledge graph structure."""
    nodes: List[GraphNode]
    edges: List[GraphEdge]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges]
        }

    def get_concept_nodes(self) -> List[GraphNode]:
        """Get all concept nodes."""
        return [node for node in self.nodes if node.type == "Concept"]

    def get_qa_nodes(self) -> List[GraphNode]:
        """Get all QA nodes."""
        return [node for node in self.nodes if node.type == "QA"]

    def get_stats(self) -> Dict[str, int]:
        """Get graph statistics."""
        return {
            "total_nodes": len(self.nodes),
            "concept_nodes": len(self.get_concept_nodes()),
            "qa_nodes": len(self.get_qa_nodes()),
            "total_edges": len(self.edges)
        }
