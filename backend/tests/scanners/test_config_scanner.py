"""Tests for config_scanner — env, Docker, Terraform AI signal detection."""

from __future__ import annotations

from app.scanners.config_scanner import (
    scan_docker_compose,
    scan_env_content,
    scan_terraform,
)


class TestScanEnvContent:
    """Tests for .env file scanning."""

    def test_empty_content_no_signals(self):
        assert scan_env_content("") == []

    def test_openai_key_detected(self):
        content = "OPENAI_API_KEY=sk-abc123\nDATABASE_URL=postgres://localhost"
        signals = scan_env_content(content)
        assert len(signals) == 1
        assert signals[0].framework_hint == "openai"
        assert signals[0].source == "env"

    def test_anthropic_key_detected(self):
        content = "ANTHROPIC_API_KEY=sk-ant-xxx"
        signals = scan_env_content(content)
        assert len(signals) == 1
        assert signals[0].framework_hint == "anthropic"

    def test_multiple_ai_keys(self):
        content = "OPENAI_API_KEY=sk-xxx\nANTHROPIC_API_KEY=sk-ant\nGROQ_API_KEY=gsk-xxx"
        signals = scan_env_content(content)
        hints = {s.framework_hint for s in signals}
        assert "openai" in hints
        assert "anthropic" in hints
        assert "groq" in hints

    def test_huggingface_token(self):
        content = "HF_TOKEN=hf_xxx"
        signals = scan_env_content(content)
        assert signals[0].framework_hint == "huggingface"

    def test_non_ai_env_vars_ignored(self):
        content = "DATABASE_URL=postgres://\nSECRET_KEY=abc\nPORT=8000"
        assert scan_env_content(content) == []

    def test_aws_bedrock_prefix(self):
        content = "AWS_BEDROCK_ENDPOINT=https://bedrock.us-east-1.amazonaws.com"
        signals = scan_env_content(content)
        assert len(signals) == 1
        assert signals[0].framework_hint == "aws-bedrock"

    def test_azure_openai_prefix(self):
        content = "AZURE_OPENAI_ENDPOINT=https://xxx.openai.azure.com"
        signals = scan_env_content(content)
        assert len(signals) == 1
        assert signals[0].framework_hint == "azure-openai"

    def test_vertex_ai_prefix(self):
        content = "VERTEX_AI_PROJECT=my-project"
        signals = scan_env_content(content)
        assert len(signals) == 1
        assert signals[0].framework_hint == "google-vertex-ai"

    def test_vector_db_keys(self):
        content = "PINECONE_API_KEY=xxx\nWEAVIATE_URL=http://localhost:8080"
        signals = scan_env_content(content)
        hints = {s.framework_hint for s in signals}
        assert "pinecone" in hints
        assert "weaviate" in hints


class TestScanDockerCompose:
    """Tests for docker-compose.yml scanning."""

    def test_empty_content_no_signals(self):
        assert scan_docker_compose("") == []

    def test_ollama_image_detected(self):
        content = """
services:
  llm:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
"""
        signals = scan_docker_compose(content)
        docker_signals = [s for s in signals if s.source == "docker" and "Docker image" in s.detail]
        assert len(docker_signals) >= 1
        assert docker_signals[0].framework_hint == "ollama"

    def test_tensorflow_serving_detected(self):
        content = "  image: tensorflow/serving:latest"
        signals = scan_docker_compose(content)
        docker_signals = [s for s in signals if "Docker image" in s.detail]
        assert docker_signals[0].framework_hint == "tensorflow"

    def test_triton_server_detected(self):
        content = "  image: nvcr.io/nvidia/tritonserver:23.08-py3"
        signals = scan_docker_compose(content)
        docker_signals = [s for s in signals if "Docker image" in s.detail]
        assert docker_signals[0].framework_hint == "triton"

    def test_non_ai_images_ignored(self):
        content = """
services:
  db:
    image: postgres:15
  redis:
    image: redis:7
"""
        signals = scan_docker_compose(content)
        docker_signals = [s for s in signals if "Docker image" in s.detail]
        assert len(docker_signals) == 0

    def test_env_vars_in_docker_detected(self):
        content = """
services:
  api:
    image: python:3.11
    environment:
      OPENAI_API_KEY=sk-xxx
"""
        signals = scan_docker_compose(content)
        env_signals = [s for s in signals if "Docker env" in s.detail]
        assert len(env_signals) >= 1

    def test_chromadb_detected(self):
        content = "  image: chromadb/chroma:latest"
        signals = scan_docker_compose(content)
        docker_signals = [s for s in signals if "Docker image" in s.detail]
        assert docker_signals[0].framework_hint == "chromadb"

    def test_vllm_detected(self):
        content = "  image: vllm/vllm-openai:latest"
        signals = scan_docker_compose(content)
        docker_signals = [s for s in signals if "Docker image" in s.detail]
        assert docker_signals[0].framework_hint == "vllm"


class TestScanTerraform:
    """Tests for Terraform file scanning."""

    def test_empty_content_no_signals(self):
        assert scan_terraform("") == []

    def test_sagemaker_detected(self):
        content = 'resource "aws_sagemaker_endpoint" "inference" {\n  name = "my-model"\n}'
        signals = scan_terraform(content)
        assert len(signals) == 1
        assert signals[0].framework_hint == "aws-sagemaker"
        assert signals[0].source == "terraform"

    def test_bedrock_detected(self):
        content = 'resource "aws_bedrock_model_invocation_logging_configuration" "config" {}'
        signals = scan_terraform(content)
        assert signals[0].framework_hint == "aws-bedrock"

    def test_vertex_ai_detected(self):
        content = 'resource "google_vertex_ai_endpoint" "endpoint" {\n  display_name = "ai"\n}'
        signals = scan_terraform(content)
        assert signals[0].framework_hint == "google-vertex-ai"

    def test_azure_ml_detected(self):
        content = 'resource "azurerm_machine_learning_workspace" "ml" {\n  name = "ml-ws"\n}'
        signals = scan_terraform(content)
        assert signals[0].framework_hint == "azure-ml"

    def test_azure_cognitive_detected(self):
        content = 'resource "azurerm_cognitive_account" "ai" {\n  name = "cog"\n}'
        signals = scan_terraform(content)
        assert signals[0].framework_hint == "azure-cognitive-services"

    def test_non_ai_resources_ignored(self):
        content = """
resource "aws_s3_bucket" "data" {
  bucket = "my-bucket"
}
resource "aws_lambda_function" "handler" {
  function_name = "my-func"
}
"""
        assert scan_terraform(content) == []

    def test_multiple_ai_resources(self):
        content = """
resource "aws_sagemaker_endpoint" "model" {}
resource "aws_bedrock_agent" "chat" {}
"""
        signals = scan_terraform(content)
        hints = {s.framework_hint for s in signals}
        assert "aws-sagemaker" in hints
        assert "aws-bedrock" in hints
