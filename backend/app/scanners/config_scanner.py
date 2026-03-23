# Scanning patterns adapted from Systima Comply (Apache 2.0)
# https://github.com/systima-ai/comply
"""Configuration file scanning for AI usage signals.

Three pure functions that detect AI/ML usage from:
1. Environment variables (.env, .env.example)
2. Docker Compose images and environment blocks
3. Terraform resource blocks

Zero I/O — receives pre-fetched file content.
"""

from __future__ import annotations

import re

from app.schemas.scanner import ConfigSignal

# ---------------------------------------------------------------------------
# Environment variable patterns → AI framework hints
# ---------------------------------------------------------------------------

ENV_KEY_PATTERNS: list[tuple[str, str]] = [
    # OpenAI
    ("OPENAI_API_KEY", "openai"),
    ("OPENAI_ORG_ID", "openai"),
    # Anthropic
    ("ANTHROPIC_API_KEY", "anthropic"),
    # Hugging Face
    ("HF_TOKEN", "huggingface"),
    ("HUGGINGFACE_TOKEN", "huggingface"),
    ("HUGGING_FACE_HUB_TOKEN", "huggingface"),
    # Cohere
    ("COHERE_API_KEY", "cohere"),
    # Mistral
    ("MISTRAL_API_KEY", "mistralai"),
    # Groq
    ("GROQ_API_KEY", "groq"),
    # Together
    ("TOGETHER_API_KEY", "together"),
    # Replicate
    ("REPLICATE_API_TOKEN", "replicate"),
    # Pinecone (vector DB)
    ("PINECONE_API_KEY", "pinecone"),
    # Weaviate (vector DB)
    ("WEAVIATE_API_KEY", "weaviate"),
    ("WEAVIATE_URL", "weaviate"),
    # Qdrant (vector DB)
    ("QDRANT_API_KEY", "qdrant"),
    ("QDRANT_URL", "qdrant"),
]

# Prefix patterns for cloud AI services
ENV_PREFIX_PATTERNS: list[tuple[str, str]] = [
    ("AWS_BEDROCK_", "aws-bedrock"),
    ("AZURE_OPENAI_", "azure-openai"),
    ("VERTEX_AI_", "google-vertex-ai"),
]

# ---------------------------------------------------------------------------
# Docker image patterns → AI framework hints
# ---------------------------------------------------------------------------

DOCKER_IMAGE_PATTERNS: list[tuple[str, str]] = [
    ("tensorflow/serving", "tensorflow"),
    ("tensorflow/tensorflow", "tensorflow"),
    ("pytorch/pytorch", "pytorch"),
    ("ollama/ollama", "ollama"),
    ("ollama/", "ollama"),
    ("vllm/vllm", "vllm"),
    ("vllm/", "vllm"),
    ("nvcr.io/nvidia/tritonserver", "triton"),
    ("tritonserver", "triton"),
    ("huggingface/", "huggingface"),
    ("chromadb/chroma", "chromadb"),
    ("chromadb/", "chromadb"),
    ("localai/localai", "localai"),
    ("localai/", "localai"),
    ("ghcr.io/ggerganov/llama.cpp", "llama-cpp"),
    ("milvusdb/milvus", "milvus"),
    ("qdrant/qdrant", "qdrant"),
    ("semitechnologies/weaviate", "weaviate"),
]

# ---------------------------------------------------------------------------
# Terraform resource patterns → AI framework hints
# ---------------------------------------------------------------------------

TERRAFORM_RESOURCE_PATTERNS: list[tuple[str, str]] = [
    ("aws_sagemaker_", "aws-sagemaker"),
    ("aws_bedrock_", "aws-bedrock"),
    ("google_vertex_ai_", "google-vertex-ai"),
    ("google_ml_engine_", "google-ml-engine"),
    ("azurerm_cognitive_account", "azure-cognitive-services"),
    ("azurerm_machine_learning_", "azure-ml"),
    ("azurerm_openai_", "azure-openai"),
]

# Regex to extract env var names from .env-style files (allows leading whitespace
# for env vars inside docker-compose environment blocks)
_ENV_VAR_RE = re.compile(r"^\s*([A-Z_][A-Z0-9_]*)=", re.MULTILINE)

# Regex to extract Docker image names
_DOCKER_IMAGE_RE = re.compile(r"image:\s*['\"]?([^\s'\"#]+)", re.MULTILINE)

# Regex to extract Terraform resource types
_TERRAFORM_RESOURCE_RE = re.compile(
    r'resource\s+"([^"]+)"', re.MULTILINE
)


def scan_env_content(content: str) -> list[ConfigSignal]:
    """Scan .env/.env.example content for AI-related environment variables.

    Args:
        content: Raw content of an env file.

    Returns:
        List of ConfigSignal for each detected AI-related variable.
    """
    signals: list[ConfigSignal] = []
    var_names = _ENV_VAR_RE.findall(content)

    for var_name in var_names:
        # Check exact matches first, then prefix matches
        matched = False
        for pattern, framework in ENV_KEY_PATTERNS:
            if var_name == pattern:
                signals.append(ConfigSignal(
                    source="env",
                    framework_hint=framework,
                    detail=f"Environment variable {var_name} detected",
                    confidence=0.85,
                ))
                matched = True
                break

        if not matched:
            for prefix, framework in ENV_PREFIX_PATTERNS:
                if var_name.startswith(prefix):
                    signals.append(ConfigSignal(
                        source="env",
                        framework_hint=framework,
                        detail=f"Environment variable {var_name} detected",
                        confidence=0.80,
                    ))
                    break

    return signals


def scan_docker_compose(content: str) -> list[ConfigSignal]:
    """Scan docker-compose.yml content for AI-related Docker images.

    Args:
        content: Raw content of a docker-compose file.

    Returns:
        List of ConfigSignal for each detected AI-related image.
    """
    signals: list[ConfigSignal] = []
    images = _DOCKER_IMAGE_RE.findall(content)

    for image in images:
        image_lower = image.lower()
        for pattern, framework in DOCKER_IMAGE_PATTERNS:
            if pattern in image_lower:
                signals.append(ConfigSignal(
                    source="docker",
                    framework_hint=framework,
                    detail=f"Docker image {image} detected",
                    confidence=0.90,
                ))
                break

    # Also scan environment blocks for env var patterns
    env_signals = scan_env_content(content)
    for sig in env_signals:
        signals.append(ConfigSignal(
            source="docker",
            framework_hint=sig.framework_hint,
            detail=f"Docker env: {sig.detail}",
            confidence=0.80,
        ))

    return signals


def scan_terraform(content: str) -> list[ConfigSignal]:
    """Scan Terraform files for AI-related cloud resources.

    Args:
        content: Raw content of a .tf file.

    Returns:
        List of ConfigSignal for each detected AI-related resource.
    """
    signals: list[ConfigSignal] = []
    resources = _TERRAFORM_RESOURCE_RE.findall(content)

    for resource_type in resources:
        resource_lower = resource_type.lower()
        for pattern, framework in TERRAFORM_RESOURCE_PATTERNS:
            if resource_lower.startswith(pattern):
                signals.append(ConfigSignal(
                    source="terraform",
                    framework_hint=framework,
                    detail=f"Terraform resource {resource_type} detected",
                    confidence=0.90,
                ))
                break

    return signals
