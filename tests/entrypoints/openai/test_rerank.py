# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project

import pytest
import requests

from vllm.entrypoints.openai.protocol import RerankResponse

from ...utils import RemoteOpenAIServer

MODEL_NAME = "BAAI/bge-reranker-base"
DTYPE = "bfloat16"


@pytest.fixture(autouse=True)
def v1(run_with_both_engines):
    # Simple autouse wrapper to run both engines for each test
    # This can be promoted up to conftest.py to run for every
    # test in a package
    pass


@pytest.fixture(scope="module")
def server():
    args = ["--enforce-eager", "--max-model-len", "100", "--dtype", DTYPE]

    with RemoteOpenAIServer(MODEL_NAME, args) as remote_server:
        yield remote_server


@pytest.mark.parametrize("model_name", [MODEL_NAME])
def test_rerank_texts(server: RemoteOpenAIServer, model_name: str):
    query = "What is the capital of France?"
    documents = [
        "The capital of Brazil is Brasilia.", "The capital of France is Paris."
    ]

    rerank_response = requests.post(server.url_for("rerank"),
                                    json={
                                        "model": model_name,
                                        "query": query,
                                        "documents": documents,
                                    })
    rerank_response.raise_for_status()
    rerank = RerankResponse.model_validate(rerank_response.json())

    assert rerank.id is not None
    assert rerank.results is not None
    assert len(rerank.results) == 2
    assert rerank.results[0].relevance_score >= 0.9
    assert rerank.results[1].relevance_score <= 0.01


@pytest.mark.parametrize("model_name", [MODEL_NAME])
def test_top_n(server: RemoteOpenAIServer, model_name: str):
    query = "What is the capital of France?"
    documents = [
        "The capital of Brazil is Brasilia.",
        "The capital of France is Paris.", "Cross-encoder models are neat"
    ]

    rerank_response = requests.post(server.url_for("rerank"),
                                    json={
                                        "model": model_name,
                                        "query": query,
                                        "documents": documents,
                                        "top_n": 2
                                    })
    rerank_response.raise_for_status()
    rerank = RerankResponse.model_validate(rerank_response.json())

    assert rerank.id is not None
    assert rerank.results is not None
    assert len(rerank.results) == 2
    assert rerank.results[0].relevance_score >= 0.9
    assert rerank.results[1].relevance_score <= 0.01


@pytest.mark.parametrize("model_name", [MODEL_NAME])
def test_rerank_max_model_len(server: RemoteOpenAIServer, model_name: str):

    query = "What is the capital of France?" * 100
    documents = [
        "The capital of Brazil is Brasilia.", "The capital of France is Paris."
    ]

    rerank_response = requests.post(server.url_for("rerank"),
                                    json={
                                        "model": model_name,
                                        "query": query,
                                        "documents": documents
                                    })
    assert rerank_response.status_code == 400
    # Assert just a small fragments of the response
    assert "Please reduce the length of the input." in \
        rerank_response.text


def test_invocations(server: RemoteOpenAIServer):
    query = "What is the capital of France?"
    documents = [
        "The capital of Brazil is Brasilia.", "The capital of France is Paris."
    ]

    request_args = {
        "model": MODEL_NAME,
        "query": query,
        "documents": documents,
    }

    rerank_response = requests.post(server.url_for("rerank"),
                                    json=request_args)
    rerank_response.raise_for_status()

    invocation_response = requests.post(server.url_for("invocations"),
                                        json=request_args)
    invocation_response.raise_for_status()

    rerank_output = rerank_response.json()
    invocation_output = invocation_response.json()

    assert rerank_output.keys() == invocation_output.keys()
    assert rerank_output["results"] == invocation_output["results"]
