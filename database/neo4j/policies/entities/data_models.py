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
    """Node in the knowledge graph following MemOS TextualMemoryItem format."""
    id: str
    memory: str  # The main content (concept name or QA text)
    metadata: Dict[str, Any]  # Contains type, embedding, entities, tags, etc.

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "memory": self.memory,
            "metadata": self.metadata
        }

    @classmethod
    def create_concept_node(
        cls,
        concept_name: str,
        embedding: List[float]
    ) -> 'GraphNode':
        """Create a concept node."""
        import uuid
        return cls(
            id=str(uuid.uuid4()),
            memory=concept_name,  # Concept name as memory
            metadata={
                "type": "fact",
                "memory_type": "UserMemory",
                "status": "activated",
                "entities": [concept_name],
                "tags": [concept_name],
                "embedding": embedding,  # Embedding of the concept name
                "created_at": datetime.now().isoformat(),
                "usage": [],
                "background": ""
            }
        )

    @classmethod
    def create_qa_node(
        cls,
        qa_data: Dict[str, Any],
        embedding: List[float],
        qa_type: str,
        related_concept_ids: List[str]
    ) -> 'GraphNode':
        """Create a QA node from qa_collection item."""
        import uuid

        # Format memory content
        memory_content = f"""Question: {qa_data['question']}

Reasoning Guidance: {qa_data['reasoning_guidance']}

Knowledge Facts: {'; '.join(qa_data['knowledge_facts'])}

Answer: {qa_data['final_answer']}

Best to Know: {qa_data.get('best_to_know', '')}"""

        # Determine entities and tags based on concept type
        if isinstance(qa_data['concept'], str):
            entities = [qa_data['concept']]
            tags = [qa_data['concept']]
        elif isinstance(qa_data['concept'], list):
            entities = qa_data['concept']
            tags = qa_data['concept']
        else:
            entities = []
            tags = []

        return cls(
            id=str(uuid.uuid4()),
            memory=memory_content,
            metadata={
                "type": "fact",
                "memory_type": "UserMemory",
                "status": "activated",
                "entities": entities,
                "tags": tags,
                "embedding": embedding,  # Embedding of the question
                "created_at": datetime.now().isoformat(),
                "usage": [],
                "background": "",
                # Store relationship info for edge creation
                "qa_type": qa_type,
                "related_concept_ids": related_concept_ids
            }
        )


@dataclass
class GraphEdge:
    """Edge in the knowledge graph following MemOS format."""
    source: str  # Source node ID
    target: str  # Target node ID
    type: str  # Relationship type: "RELATE_TO" or "PARENT"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type
        }

    @classmethod
    def create_relate_to_edge(
        cls,
        source_id: str,
        target_id: str
    ) -> 'GraphEdge':
        """Create a RELATE_TO edge between concepts."""
        return cls(
            source=source_id,
            target=target_id,
            type="RELATE_TO"
        )

    @classmethod
    def create_parent_edge(
        cls,
        parent_id: str,
        child_id: str
    ) -> 'GraphEdge':
        """Create a PARENT edge from concept to QA."""
        return cls(
            source=parent_id,
            target=child_id,
            type="PARENT"
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
        """Get all concept nodes (nodes without qa_type in metadata)."""
        return [node for node in self.nodes if "qa_type" not in node.metadata]

    def get_qa_nodes(self) -> List[GraphNode]:
        """Get all QA nodes (nodes with qa_type in metadata)."""
        return [node for node in self.nodes if "qa_type" in node.metadata]

    def get_stats(self) -> Dict[str, int]:
        """Get graph statistics."""
        concept_nodes = self.get_concept_nodes()
        qa_nodes = self.get_qa_nodes()

        # Count QA types
        concept_qa_count = sum(1 for node in qa_nodes if node.metadata.get("qa_type") == "concept_qa")
        relation_qa_count = sum(1 for node in qa_nodes if node.metadata.get("qa_type") == "relation_qa")

        # Count edge types
        relate_to_edges = sum(1 for edge in self.edges if edge.type == "RELATE_TO")
        parent_edges = sum(1 for edge in self.edges if edge.type == "PARENT")

        return {
            "total_nodes": len(self.nodes),
            "concept_nodes": len(concept_nodes),
            "qa_nodes": len(qa_nodes),
            "concept_qa_nodes": concept_qa_count,
            "relation_qa_nodes": relation_qa_count,
            "total_edges": len(self.edges),
            "relate_to_edges": relate_to_edges,
            "parent_edges": parent_edges
        }
