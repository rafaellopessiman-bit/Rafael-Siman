"""Tests for src.knowledge.corpus_filter module."""
import pytest

from src.knowledge.corpus_filter import (
    ChunkQualityResult,
    DuplicateReport,
    content_fingerprint,
    deduplicate_chunks,
    detect_duplicates,
    evaluate_chunk_quality,
    filter_chunks,
)


class TestEvaluateChunkQuality:
    def test_short_chunk_rejected(self):
        result = evaluate_chunk_quality("too short")
        assert not result.accepted
        assert result.reason == "too_short"

    def test_empty_chunk_rejected(self):
        result = evaluate_chunk_quality("   ")
        assert not result.accepted

    def test_normal_chunk_accepted(self):
        text = "Python is a versatile programming language used for web development, data science, and automation tasks across many industries."
        result = evaluate_chunk_quality(text)
        assert result.accepted

    def test_low_alpha_ratio_rejected(self):
        text = "12345 67890 !@#$% ^&*() 12345 67890 !@#$% ^&*() 12345 67890 more stuff"
        result = evaluate_chunk_quality(text)
        assert not result.accepted
        assert result.reason == "low_alpha_ratio"

    def test_high_numeric_ratio_rejected(self):
        text = "1234567890 " * 20
        result = evaluate_chunk_quality(text)
        assert not result.accepted

    def test_low_vocabulary_rejected(self):
        text = "word " * 60  # long enough, but only 1 unique word
        result = evaluate_chunk_quality(text)
        assert not result.accepted
        assert result.reason == "low_vocabulary"

    def test_boilerplate_toc_rejected(self):
        text = "Table of Contents\n" + "Chapter 1 ........ 10\n" * 5
        result = evaluate_chunk_quality(text)
        assert not result.accepted
        assert result.reason == "boilerplate"

    def test_boilerplate_copyright_rejected(self):
        text = "Copyright 2025 John Doe. All Rights Reserved. This publication may not be reproduced in whole."
        result = evaluate_chunk_quality(text)
        assert not result.accepted
        assert result.reason == "boilerplate"

    def test_boilerplate_isbn_rejected(self):
        text = "ISBN: 978-0-13-468599-1 Published by O'Reilly Media. First Edition, revised and updated with corrections."
        result = evaluate_chunk_quality(text)
        assert not result.accepted
        assert result.reason == "boilerplate"

    def test_sumario_pt_rejected(self):
        text = "Sumário\nCapítulo 1 - Introdução ao Python\nCapítulo 2 - Variáveis e tipos de dados"
        result = evaluate_chunk_quality(text)
        assert not result.accepted


class TestFilterChunks:
    def test_filters_bad_chunks(self):
        chunks = [
            "short",
            "Python is a versatile programming language used for web development, data science, and automation tasks across many domains.",
            "  ",
            "Another valid chunk with enough content and unique vocabulary for real meaningful text retrieval and indexing.",
        ]
        accepted, dropped = filter_chunks(chunks)
        assert len(accepted) == 2
        assert dropped == 2

    def test_empty_list(self):
        accepted, dropped = filter_chunks([])
        assert accepted == []
        assert dropped == 0


class TestContentFingerprint:
    def test_same_content_same_hash(self):
        a = content_fingerprint("Hello World. This is a test document.")
        b = content_fingerprint("Hello World. This is a test document.")
        assert a == b

    def test_whitespace_variations_same_hash(self):
        a = content_fingerprint("Hello   World.\n\n  This   is a test.")
        b = content_fingerprint("Hello World. This is a test.")
        assert a == b

    def test_case_insensitive(self):
        a = content_fingerprint("Hello World")
        b = content_fingerprint("hello world")
        assert a == b

    def test_different_content_different_hash(self):
        a = content_fingerprint("Python programming")
        b = content_fingerprint("Java programming")
        assert a != b


class TestDetectDuplicates:
    def test_no_duplicates(self):
        docs = [
            {"file_path": "/a.txt", "content": "Unique content A with enough text."},
            {"file_path": "/b.txt", "content": "Unique content B with different text."},
        ]
        report = detect_duplicates(docs)
        assert len(report.unique_documents) == 2
        assert len(report.duplicates) == 0

    def test_exact_duplicates(self):
        docs = [
            {"file_path": "/a.txt", "content": "Same content here."},
            {"file_path": "/b.txt", "content": "Same content here."},
        ]
        report = detect_duplicates(docs)
        assert len(report.unique_documents) == 1
        assert len(report.duplicates) == 1
        assert report.duplicates[0]["_duplicate_of"] == "/a.txt"

    def test_whitespace_duplicates(self):
        docs = [
            {"file_path": "/a.txt", "content": "Hello   world"},
            {"file_path": "/b.txt", "content": "hello world"},
        ]
        report = detect_duplicates(docs)
        assert len(report.unique_documents) == 1
        assert len(report.duplicates) == 1

    def test_preserves_first_by_path_order(self):
        docs = [
            {"file_path": "/z.txt", "content": "duplicated"},
            {"file_path": "/a.txt", "content": "duplicated"},
        ]
        report = detect_duplicates(docs)
        assert report.unique_documents[0]["file_path"] == "/a.txt"

    def test_empty_input(self):
        report = detect_duplicates([])
        assert len(report.unique_documents) == 0
        assert len(report.duplicates) == 0


class TestDeduplicateChunks:
    def test_removes_exact_duplicates(self):
        chunks = ["chunk A", "chunk B", "chunk A", "chunk C", "chunk B"]
        unique, removed = deduplicate_chunks(chunks)
        assert unique == ["chunk A", "chunk B", "chunk C"]
        assert removed == 2

    def test_no_duplicates(self):
        chunks = ["a", "b", "c"]
        unique, removed = deduplicate_chunks(chunks)
        assert unique == ["a", "b", "c"]
        assert removed == 0

    def test_empty_input(self):
        unique, removed = deduplicate_chunks([])
        assert unique == []
        assert removed == 0

    def test_whitespace_normalized(self):
        chunks = ["  hello world  ", "hello world", "  hello world  "]
        unique, removed = deduplicate_chunks(chunks)
        # strip() makes all three equivalent; first kept, two removed
        assert removed == 2
