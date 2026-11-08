from shared.config_loader import load_config
from shared.llm.ollama_client import OllamaChatModel
from orchestration.orchestrator import Investigator


def test_v1_v2_investigator_uses_native_ollama_clients_from_provider_config():
    config = load_config("config/experiments/v1_basic.yaml")
    config["llm"].update({
        "provider": "ollama_native",
        "model": "qwen-test:latest",
        "base_url": "http://127.0.0.1:11434",
    })

    investigator = Investigator(object(), config, mode="live")

    assert len(investigator._models) == 5
    assert all(isinstance(model, OllamaChatModel) for model in investigator._models.values())
    assert all(model.model == "qwen-test:latest" for model in investigator._models.values())
