# SPDX-FileCopyrightText: 2022-present deepset GmbH <info@deepset.ai>
#
# SPDX-License-Identifier: Apache-2.0

from typing import Any, Dict

import pytest

from haystack import DeserializationError, Pipeline
from haystack.components.retrievers.in_memory.embedding_retriever import InMemoryEmbeddingRetriever
from haystack.dataclasses import Document
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.document_stores.types import FilterPolicy
from haystack.testing.factory import document_store_class


class TestMemoryEmbeddingRetriever:
    def test_init_default(self):
        retriever = InMemoryEmbeddingRetriever(InMemoryDocumentStore())
        assert retriever.filters is None
        assert retriever.top_k == 10
        assert retriever.scale_score is False

    def test_init_with_parameters(self):
        retriever = InMemoryEmbeddingRetriever(
            InMemoryDocumentStore(), filters={"name": "test.txt"}, top_k=5, scale_score=True
        )
        assert retriever.filters == {"name": "test.txt"}
        assert retriever.top_k == 5
        assert retriever.scale_score

    def test_init_with_invalid_top_k_parameter(self):
        with pytest.raises(ValueError):
            InMemoryEmbeddingRetriever(InMemoryDocumentStore(), top_k=-2)

    def test_to_dict(self):
        MyFakeStore = document_store_class("MyFakeStore", bases=(InMemoryDocumentStore,))
        document_store = MyFakeStore()
        document_store.to_dict = lambda: {"type": "test_module.MyFakeStore", "init_parameters": {}}
        component = InMemoryEmbeddingRetriever(document_store=document_store)

        data = component.to_dict()
        assert data == {
            "type": "haystack.components.retrievers.in_memory.embedding_retriever.InMemoryEmbeddingRetriever",
            "init_parameters": {
                "document_store": {"type": "test_module.MyFakeStore", "init_parameters": {}},
                "filters": None,
                "top_k": 10,
                "scale_score": False,
                "return_embedding": False,
                "filter_policy": "replace",
            },
        }

    def test_to_dict_with_custom_init_parameters(self):
        MyFakeStore = document_store_class("MyFakeStore", bases=(InMemoryDocumentStore,))
        document_store = MyFakeStore()
        document_store.to_dict = lambda: {"type": "test_module.MyFakeStore", "init_parameters": {}}
        component = InMemoryEmbeddingRetriever(
            document_store=document_store,
            filters={"name": "test.txt"},
            top_k=5,
            scale_score=True,
            return_embedding=True,
        )
        data = component.to_dict()
        assert data == {
            "type": "haystack.components.retrievers.in_memory.embedding_retriever.InMemoryEmbeddingRetriever",
            "init_parameters": {
                "document_store": {"type": "test_module.MyFakeStore", "init_parameters": {}},
                "filters": {"name": "test.txt"},
                "top_k": 5,
                "scale_score": True,
                "return_embedding": True,
                "filter_policy": "replace",
            },
        }

    def test_from_dict(self):
        data = {
            "type": "haystack.components.retrievers.in_memory.embedding_retriever.InMemoryEmbeddingRetriever",
            "init_parameters": {
                "document_store": {
                    "type": "haystack.document_stores.in_memory.document_store.InMemoryDocumentStore",
                    "init_parameters": {},
                },
                "filters": {"name": "test.txt"},
                "top_k": 5,
                "filter_policy": "merge",
            },
        }
        component = InMemoryEmbeddingRetriever.from_dict(data)
        assert isinstance(component.document_store, InMemoryDocumentStore)
        assert component.filters == {"name": "test.txt"}
        assert component.top_k == 5
        assert component.scale_score is False
        assert component.filter_policy == FilterPolicy.MERGE

    def test_from_dict_without_docstore(self):
        data = {
            "type": "haystack.components.retrievers.in_memory.embedding_retriever.InMemoryEmbeddingRetriever",
            "init_parameters": {},
        }
        with pytest.raises(DeserializationError, match="Missing 'document_store' in serialization data"):
            InMemoryEmbeddingRetriever.from_dict(data)

    def test_from_dict_without_docstore_type(self):
        data = {
            "type": "haystack.components.retrievers.in_memory.embedding_retriever.InMemoryEmbeddingRetriever",
            "init_parameters": {"document_store": {"init_parameters": {}}},
        }
        with pytest.raises(DeserializationError):
            InMemoryEmbeddingRetriever.from_dict(data)

    def test_from_dict_nonexisting_docstore(self):
        data = {
            "type": "haystack.components.retrievers.in_memory.embedding_retriever.InMemoryEmbeddingRetriever",
            "init_parameters": {"document_store": {"type": "Nonexisting.Docstore", "init_parameters": {}}},
        }
        with pytest.raises(DeserializationError):
            InMemoryEmbeddingRetriever.from_dict(data)

    def test_valid_run(self):
        top_k = 3
        ds = InMemoryDocumentStore(embedding_similarity_function="cosine")
        docs = [
            Document(content="my document", embedding=[0.1, 0.2, 0.3, 0.4]),
            Document(content="another document", embedding=[1.0, 1.0, 1.0, 1.0]),
            Document(content="third document", embedding=[0.5, 0.7, 0.5, 0.7]),
        ]
        ds.write_documents(docs)

        retriever = InMemoryEmbeddingRetriever(ds, top_k=top_k)
        result = retriever.run(query_embedding=[0.1, 0.1, 0.1, 0.1], return_embedding=True)

        assert "documents" in result
        assert len(result["documents"]) == top_k
        assert result["documents"][0].embedding == [1.0, 1.0, 1.0, 1.0]

    def test_invalid_run_wrong_store_type(self):
        SomeOtherDocumentStore = document_store_class("SomeOtherDocumentStore")
        with pytest.raises(ValueError, match="document_store must be an instance of InMemoryDocumentStore"):
            InMemoryEmbeddingRetriever(SomeOtherDocumentStore())

    @pytest.mark.integration
    def test_run_with_pipeline(self):
        ds = InMemoryDocumentStore(embedding_similarity_function="cosine")
        top_k = 2
        docs = [
            Document(content="my document", embedding=[0.1, 0.2, 0.3, 0.4]),
            Document(content="another document", embedding=[1.0, 1.0, 1.0, 1.0]),
            Document(content="third document", embedding=[0.5, 0.7, 0.5, 0.7]),
        ]
        ds.write_documents(docs)
        retriever = InMemoryEmbeddingRetriever(ds, top_k=top_k)

        pipeline = Pipeline()
        pipeline.add_component("retriever", retriever)
        result: Dict[str, Any] = pipeline.run(
            data={"retriever": {"query_embedding": [0.1, 0.1, 0.1, 0.1], "return_embedding": True}}
        )

        assert result
        assert "retriever" in result
        results_docs = result["retriever"]["documents"]
        assert results_docs
        assert len(results_docs) == top_k
        assert results_docs[0].embedding == [1.0, 1.0, 1.0, 1.0]
